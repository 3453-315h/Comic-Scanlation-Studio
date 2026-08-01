"""
Translation Module - Comic Translation Studio

Supports multiple translation backends:
- DeepL API (best quality, requires API key)
- Google Translate (free, via googletrans)
- OpenAI GPT (contextual, requires API key)
- NLLB Offline (high quality, no internet required)
- OPUS-MT Offline (fast, lightweight)
"""

import requests
from typing import Optional
import logging
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


# NLLB language code mapping
NLLB_LANG_CODES = {
    "ja": "jpn_Jpan",
    "en": "eng_Latn", 
    "zh": "zho_Hans",
    "zh-cn": "zho_Hans",
    "zh-tw": "zho_Hant",
    "ko": "kor_Hang",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",
    "pl": "pol_Latn",
    "cs": "ces_Latn",
    "it": "ita_Latn",
    "nl": "nld_Latn",
    "sv": "swe_Latn",
    "da": "dan_Latn",
    "no": "nor_Latn",
    "fi": "fin_Latn",
    "el": "ell_Grek",
    "tr": "tur_Latn",
    "hu": "hun_Latn",
    "ro": "ron_Latn",
    "uk": "ukr_Cyrl",
    "id": "ind_Latn",
    "th": "tha_Thai",
    "vi": "vie_Latn",
}


class Translator:
    """Translation using external APIs or offline models
    
    Available backends:
        - "deepl": DeepL API (requires DEEPL_API_KEY)
        - "google": Google Translate (free, may be rate-limited)
        - "openai": OpenAI GPT (requires OPENAI_API_KEY, contextual)
        - "nllb": Meta NLLB-200 (offline, high quality, ~2GB download)
        - "opus": Helsinki-NLP OPUS-MT (offline, fast, ~300MB)
        - "offline": Alias for "nllb"
    """
    
    def __init__(self, api: str = "deepl", source_lang: str = "ja", target_lang: str = "en"):
        self.api = api
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = None
        
        # Lazy-loaded offline models
        self._nllb_model = None
        self._nllb_tokenizer = None
        self._opus_model = None
        self._opus_tokenizer = None
        
        # Cached API clients to reuse connections
        self._google_client = None
        self._requests_session = None
        self._openai_client = None

        if api == "deepl":
            from dotenv import load_dotenv
            import os
            load_dotenv()
            self.api_key = os.getenv("DEEPL_API_KEY")
        elif api == "openai":
            from dotenv import load_dotenv
            import os
            load_dotenv()
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        
        # Simple disk cache
        self.cache_file = Path("bck/translation_cache.json")
        self.cache = self._load_cache()
        
        logger.info(f"Translator initialized with backend: {api}")
        
    def _load_cache(self) -> dict:
        """Load translation cache from disk"""
        if self.cache_file.exists():
            try:
                import json
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load cache: {e}")
        return {}
        
    def _save_cache(self):
        """Save translation cache to disk"""
        try:
            self.cache_file.parent.mkdir(exist_ok=True)
            import json
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    def download_model(self):
        """Force download/load of offline models"""
        try:
            if self.api in ("nllb", "offline"):
                if self._nllb_model is None:
                    logger.info("Downloading/Loading NLLB model...")
                    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                    model_name = "facebook/nllb-200-distilled-600M"
                    self._nllb_tokenizer = AutoTokenizer.from_pretrained(model_name)
                    self._nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
                    logger.info("NLLB model loaded.")
            elif self.api == "opus":
                if self._opus_model is None:
                    logger.info("Downloading/Loading OPUS model...")
                    from transformers import MarianMTModel, MarianTokenizer
                    model_name = f"Helsinki-NLP/opus-mt-{self.source_lang}-{self.target_lang}"
                    self._opus_tokenizer = MarianTokenizer.from_pretrained(model_name)
                    self._opus_model = MarianMTModel.from_pretrained(model_name)
                    logger.info("OPUS model loaded.")
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            raise

    def translate(self, text: str, context: Optional[str] = None, api_override: Optional[str] = None) -> str:
        """Translate text from source to target language
        
        Args:
            text: Text to translate
            context: Optional context for AI models
            api_override: Force use of specific backend (e.g. "google")
        """
        
        if not text.strip():
            return ""
            
        # Determine effective API
        effective_api = api_override if api_override else self.api
            
        # Check cache
        # Key includes api, source, target to avoid collisions
        cache_key = f"{effective_api}|{self.source_lang}|{self.target_lang}|{text}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = text
        if effective_api == "google":
            result = self._google_translate(text)
        elif effective_api == "deepl":
            if not self.api_key:
                logger.warning("DeepL API key missing. Falling back to Google Translate.")
                result = self._google_translate(text)
            else:
                result = self._deepl_translate(text)
        elif effective_api == "openai":
            if not self.api_key:
                logger.warning("OpenAI API key missing. Falling back to Google Translate.")
                result = self._google_translate(text)
            else:
                result = self._openai_translate(text, context)
        elif effective_api in ("nllb", "offline"):
            result = self._nllb_translate(text)
        elif effective_api == "opus":
            result = self._opus_translate(text)
        else:
            logger.warning(f"Unknown translation API: {effective_api}")
            return text
            
        # Save to cache if successful and different
        # Fallback: if result is the same or None, we return text?
        # If result starts with specific error brackets (legacy behavior), we should return text.
        # But we are changing the implementation below to NOT return brackets.
        
        if result and result != text:
             self.cache[cache_key] = result
             self._save_cache()
             return result
             
        return text
    
    def _google_translate(self, text: str) -> str:
        """Use googletrans library"""
        try:
            if self._google_client is None:
                from googletrans import Translator as GTranslator
                self._google_client = GTranslator()

            # Use auto-detection to handle cases where the text isn't in the default project source language
            result = self._google_client.translate(text, src='auto', dest=self.target_lang)
            
            # Handle async result (newer googletrans versions)
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    # We are already in a loop (e.g. valid for some GUI frameworks or nested async)
                    # This is tricky in sync context. simpler to just use run_until_complete if not running
                    # But if loop is running, we might need a future. 
                    # For this specific app, we are likely not in an async loop in the worker thread.
                    # But let's be safe:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                         result = pool.submit(asyncio.run, result).result()
                else:
                    result = loop.run_until_complete(result)
            
            return result.text
        except Exception as e:
            logger.error(f"Google Translate error: {e}")
            return text  # Return original



    
    def _deepl_translate(self, text: str) -> str:
        """Use DeepL API"""
        if not self.api_key:
            return text
        
        try:
            if self._requests_session is None:
                self._requests_session = requests.Session()

            url = "https://api-free.deepl.com/v2/translate"
            params = {
                "auth_key": self.api_key,
                "text": text,
                "source_lang": self.source_lang.upper(),
                "target_lang": self.target_lang.upper()
            }
            response = self._requests_session.post(url, data=params)
            return response.json()["translations"][0]["text"]
        except Exception as e:
            logger.error(f"DeepL error: {e}")
            return text
    
    def _openai_translate(self, text: str, context: Optional[str] = None) -> str:
        """Use OpenAI GPT for contextual translation"""
        if not self.api_key:
            return text
        
        try:
            if self._openai_client is None:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.api_key)
            
            prompt = f"""Translate this comic text from {self.source_lang} to {self.target_lang}.
            Maintain the tone and style appropriate for comics.
            Context: {context or 'No context provided'}
            
            Text: "{text}"
            
            Translation:"""
            
            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return text
    
    def _nllb_translate(self, text: str) -> str:
        """High-quality offline translation using Meta's NLLB-200
        
        First run will download ~2.3GB model. Subsequent runs use cache.
        Provides quality close to DeepL/Google for most language pairs.
        """
        try:
            # Lazy load model (if not already loaded by download_model)
            if self._nllb_model is None:
                self.download_model()
            
            # Get NLLB language codes
            src_code = NLLB_LANG_CODES.get(self.source_lang, "jpn_Jpan")
            tgt_code = NLLB_LANG_CODES.get(self.target_lang, "eng_Latn")
            
            # Tokenize
            self._nllb_tokenizer.src_lang = src_code
            inputs = self._nllb_tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
            
            # Generate translation
            translated_tokens = self._nllb_model.generate(
                **inputs,
                forced_bos_token_id=self._nllb_tokenizer.convert_tokens_to_ids(tgt_code),
                max_length=512,
                num_beams=4,
                early_stopping=True
            )
            
            result = self._nllb_tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            return result
            
        except ImportError:
            logger.error("transformers not installed. Install with: pip install transformers sentencepiece")
            return text
        except Exception as e:
            logger.error(f"NLLB translation error: {e}")
            return text
    
    def _opus_translate(self, text: str) -> str:
        """Fast offline translation using Helsinki-NLP OPUS-MT
        
        Smaller models (~300MB), faster inference, slightly lower quality than NLLB.
        Best for quick translations when resources are limited.
        """
        try:
            # Lazy load model
            if self._opus_model is None:
                 self.download_model()
            
            # Tokenize and translate
            inputs = self._opus_tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
            translated_tokens = self._opus_model.generate(**inputs, max_length=512)
            result = self._opus_tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            
            return result
            
        except ImportError:
            logger.error("transformers not installed. Install with: pip install transformers sentencepiece")
            return text
        except Exception as e:
            logger.error(f"OPUS-MT translation error: {e}")
            # Try NLLB as fallback
            logger.info("Falling back to NLLB...")
            return self._nllb_translate(text)