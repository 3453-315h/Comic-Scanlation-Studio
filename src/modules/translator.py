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
from typing import Optional, Dict
import logging
from pathlib import Path
import asyncio
import os
import json
import tempfile
import threading

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    """Base error for translation operations."""
    pass


class TranslationBackendError(TranslationError):
    """Raised when a translation backend fails (network, API, inference)."""
    pass


class MissingCredentialsError(TranslationError):
    """Raised when required API credentials are missing."""
    pass


class UnsupportedBackendError(TranslationError):
    """Raised when an unsupported translation backend is selected."""
    pass


class CacheLockError(TranslationError):
    """Raised when acquiring or releasing inter-process cache lock fails."""
    pass


class CacheCorruptError(TranslationError):
    """Raised when the on-disk cache file is corrupt or malformed."""
    def __init__(self, message: str, quarantine_path: Optional[Path] = None):
        super().__init__(message)
        self.quarantine_path = quarantine_path


class TranslationCache:
    """Thread-safe and process-safe persistent translation cache with atomic writes."""
    
    def __init__(self, cache_file: Optional[Path] = None):
        from ..core.config import Config
        if cache_file is not None:
            self.cache_file = Path(cache_file).resolve()
        else:
            default_path = getattr(Config, 'TRANSLATION_CACHE_FILE', Config.PORTABLE_DIR / "cache" / "translation_cache.json")
            self.cache_file = Path(default_path).resolve()
        
        self.lock_file = self.cache_file.with_suffix('.lock')
        self._thread_lock = threading.RLock()
        self._in_memory: Dict[str, str] = {}
        self.persistence_disabled = False
        self.quarantine_path: Optional[Path] = None
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._reload_from_disk()

    @property
    def is_durable(self) -> bool:
        """Returns True if cache persistence is active, False if disabled."""
        return not self.persistence_disabled

    @property
    def is_persistent(self) -> bool:
        """Returns True if cache persistence is active, False if disabled."""
        return not self.persistence_disabled

    def _quarantine_corrupt_file(self, cause: Exception) -> Path:
        """Quarantine corrupt cache file to preserve bytes for diagnosis without silent data loss."""
        import shutil
        import time
        ts = int(time.time() * 1000)
        quarantine = self.cache_file.with_name(f"{self.cache_file.stem}_corrupt_{ts}{self.cache_file.suffix}")
        try:
            shutil.copy2(str(self.cache_file), str(quarantine))
            self.cache_file.unlink(missing_ok=True)
        except Exception as q_err:
            logger.error(f"Failed to quarantine corrupt cache file: {q_err}")
        self.persistence_disabled = True
        self.quarantine_path = quarantine
        return quarantine

    def _acquire_file_lock(self) -> int:
        """Acquire an exclusive cross-process lock portably on Windows and POSIX."""
        import sys
        try:
            lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR)
        except Exception as e:
            raise CacheLockError(f"Could not open lock file {self.lock_file}: {e}") from e

        if sys.platform == "win32":
            try:
                import msvcrt
                os.lseek(lock_fd, 0, os.SEEK_SET)
                msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
            except Exception as e:
                try:
                    os.close(lock_fd)
                except Exception:
                    pass
                raise CacheLockError(f"Windows file locking failed for {self.lock_file}: {e}") from e
        else:
            try:
                import fcntl
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
            except Exception as e:
                try:
                    os.close(lock_fd)
                except Exception:
                    pass
                raise CacheLockError(f"POSIX file locking failed for {self.lock_file}: {e}") from e

        return lock_fd

    def _release_file_lock(self, lock_fd: int):
        """Release the cross-process lock portably on Windows and POSIX."""
        import sys
        unlock_err = None
        try:
            if sys.platform == "win32":
                try:
                    import msvcrt
                    os.lseek(lock_fd, 0, os.SEEK_SET)
                    msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
                except Exception as e:
                    unlock_err = CacheLockError(f"Windows file unlocking failed for {self.lock_file}: {e}")
            else:
                try:
                    import fcntl
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except Exception as e:
                    unlock_err = CacheLockError(f"POSIX file unlocking failed for {self.lock_file}: {e}")
        finally:
            try:
                os.close(lock_fd)
            except Exception as close_err:
                if unlock_err is None:
                    unlock_err = CacheLockError(f"Closing lock file descriptor failed for {self.lock_file}: {close_err}")

        if unlock_err is not None:
            raise unlock_err

    def _reload_from_disk(self) -> Dict[str, str]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    content = f.read()
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("Cache root is not a JSON object")
                self._in_memory.update(data)
                return self._in_memory
            except Exception as e:
                quarantine = self._quarantine_corrupt_file(e)
                err_msg = (
                    f"Corrupt translation cache detected at {self.cache_file} ({e}). "
                    f"Corrupt bytes quarantined to {quarantine}. Persistence is disabled."
                )
                logger.error(err_msg)
                raise CacheCorruptError(err_msg, quarantine_path=quarantine) from e
        return self._in_memory

    def get(self, key: str) -> Optional[str]:
        with self._thread_lock:
            if key in self._in_memory:
                return self._in_memory[key]
            if not self.persistence_disabled:
                try:
                    self._reload_from_disk()
                except CacheCorruptError:
                    return None
            return self._in_memory.get(key)

    def set(self, key: str, value: str):
        with self._thread_lock:
            if self.persistence_disabled:
                self._in_memory[key] = value
                raise CacheCorruptError(
                    f"Cache persistence is disabled due to quarantined corrupt cache ({self.quarantine_path}). "
                    "Entry retained in-memory for session only.",
                    quarantine_path=self.quarantine_path
                )

            try:
                lock_fd = self._acquire_file_lock()
            except CacheLockError as e:
                logger.error(f"Failed to acquire file lock for cache persistence: {e}")
                self._in_memory[key] = value
                raise

            write_exc = None
            try:
                current_disk = {}
                if self.cache_file.exists():
                    try:
                        with open(self.cache_file, "r", encoding="utf-8") as f:
                            content = f.read()
                        loaded = json.loads(content)
                        if isinstance(loaded, dict):
                            current_disk = loaded
                        else:
                            raise ValueError("Cache root is not a JSON object")
                    except Exception as parse_err:
                        quarantine = self._quarantine_corrupt_file(parse_err)
                        self._in_memory[key] = value
                        raise CacheCorruptError(
                            f"Corrupt translation cache detected on disk during set() ({parse_err}). "
                            f"Preserved at {quarantine}. Persistence disabled.",
                            quarantine_path=quarantine
                        ) from parse_err

                current_disk.update(self._in_memory)
                current_disk[key] = value
                self._in_memory = current_disk

                cache_dir = self.cache_file.parent
                cache_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile("w", dir=cache_dir, delete=False, encoding="utf-8") as tf:
                    json.dump(self._in_memory, tf, ensure_ascii=False, indent=2)
                    tf.flush()
                    os.fsync(tf.fileno())
                    temp_name = tf.name

                os.replace(temp_name, self.cache_file)
            except Exception as e:
                write_exc = e
                raise
            finally:
                try:
                    self._release_file_lock(lock_fd)
                except Exception as rel_err:
                    if write_exc is not None:
                        logger.error(f"Failed to release lock after write exception: {rel_err}")
                        write_exc.lock_release_error = rel_err
                        write_exc.__context__ = rel_err
                    else:
                        raise rel_err

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __getitem__(self, key: str) -> str:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __setitem__(self, key: str, value: str):
        self.set(key, value)


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
    
    def __init__(self, api: str = "deepl", source_lang: str = "ja", target_lang: str = "en", cache_file: Optional[Path] = None, backend: Optional[str] = None):
        self.api = backend if backend is not None else api
        self.backend = self.api
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = None
        
        # Lazy-loaded offline models
        self._nllb_model = None
        self._nllb_tokenizer = None
        self._opus_model = None
        self._opus_tokenizer = None
        self._session = requests.Session()
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
        
        # Persistent thread/process safe disk cache
        try:
            self.cache = TranslationCache(cache_file)
        except CacheCorruptError as e:
            logger.error(f"Translation cache initialization encountered corrupt cache: {e}. Translation will proceed uncached.")
            self.cache = TranslationCache.__new__(TranslationCache)
            from ..core.config import Config
            p = Path(cache_file) if cache_file is not None else Path(getattr(Config, 'TRANSLATION_CACHE_FILE', Config.PORTABLE_DIR / "cache" / "translation_cache.json"))
            self.cache.cache_file = p.resolve()
            self.cache.lock_file = self.cache.cache_file.with_suffix('.lock')
            self.cache._thread_lock = threading.RLock()
            self.cache._in_memory = {}
            self.cache.persistence_disabled = True
            self.cache.quarantine_path = getattr(e, 'quarantine_path', None)
        self.cache_file = self.cache.cache_file
        
        logger.info(f"Translator initialized with backend: {api}")
        
    def _load_cache(self) -> dict:
        """Compatibility helper"""
        return self.cache._reload_from_disk()
        
    def _save_cache(self):
        """Compatibility helper"""
        pass
        
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

    def _get_cache_key(self, text: str, source_lang: Optional[str] = None, target_lang: Optional[str] = None, api: Optional[str] = None) -> str:
        s_lang = source_lang or self.source_lang
        t_lang = target_lang or self.target_lang
        eff_api = api or self.api
        return f"{eff_api}|{s_lang}|{t_lang}|{text}"

    def translate(self, text: str, context: Optional[str] = None, api_override: Optional[str] = None) -> str:
        """Translate text from source to target language
        
        Args:
            text: Text to translate
            context: Optional context for AI models
            api_override: Force use of specific backend (e.g. "google")
        """
        if not text or not text.strip():
            return ""
            
        # Determine effective API
        effective_api = api_override if api_override else self.api
            
        # Check cache
        cache_key = self._get_cache_key(text, self.source_lang, self.target_lang, effective_api)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        if effective_api == "google":
            result = self._google_translate(text)
        elif effective_api == "deepl":
            if not self.api_key:
                raise MissingCredentialsError("DeepL API key is missing. Please configure DEEPL_API_KEY in your settings.")
            result = self._deepl_translate(text)
        elif effective_api == "openai":
            if not self.api_key:
                raise MissingCredentialsError("OpenAI API key is missing. Please configure OPENAI_API_KEY in your settings.")
            result = self._openai_translate(text, context)
        elif effective_api in ("nllb", "offline"):
            result = self._nllb_translate(text)
        elif effective_api == "opus":
            result = self._opus_translate(text)
        else:
            raise UnsupportedBackendError(f"Unsupported translation backend: '{effective_api}'")
            
        # Save to cache even if translation is identical to original input
        if result is not None:
            try:
                self.cache.set(cache_key, result)
            except CacheCorruptError as e:
                logger.warning(f"Translation cache persistence unavailable ({e}). Translation succeeded uncached.")
            return result
             
        raise TranslationBackendError(f"Translation backend '{effective_api}' returned None.")
    
    def _google_translate(self, text: str) -> str:
        """Use googletrans library"""
        try:
            from googletrans import Translator as GTranslator
            translator = GTranslator()
            result = translator.translate(text, src='auto', dest=self.target_lang)
            
            # Handle async result (newer googletrans versions)
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(asyncio.run, result).result()
                else:
                    result = loop.run_until_complete(result)
            
            if not result or not hasattr(result, 'text') or result.text is None:
                raise TranslationBackendError("Google Translate returned empty response.")
            return str(result.text)
        except Exception as e:
            logger.error(f"Google Translate error: {e}")
            raise TranslationBackendError(f"Google Translate error: {e}") from e
    
    def _deepl_translate(self, text: str) -> str:
        """Use DeepL API"""
        if not self.api_key:
            raise MissingCredentialsError("DeepL API key is missing.")
        
        try:
            url = "https://api-free.deepl.com/v2/translate"
            params = {
                "auth_key": self.api_key,
                "text": text,
                "source_lang": self.source_lang.upper(),
                "target_lang": self.target_lang.upper()
            }
            response = self._session.post(url, data=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            translations = data.get("translations", [])
            if not translations:
                raise TranslationBackendError("DeepL returned no translations.")
            return translations[0]["text"]
        except Exception as e:
            logger.error(f"DeepL error: {e}")
            raise TranslationBackendError(f"DeepL error: {e}") from e
    
    def _openai_translate(self, text: str, context: Optional[str] = None) -> str:
        """Use OpenAI GPT for contextual translation"""
        if not self.api_key:
            raise MissingCredentialsError("OpenAI API key is missing.")
        
        try:
            from openai import OpenAI
            if self._openai_client is None:
                self._openai_client = OpenAI(api_key=self.api_key)
            
            prompt = f"""Translate this comic text from {self.source_lang} to {self.target_lang}.
Maintain the tone and style appropriate for comics.
Context: {context or 'No context provided'}

Text: "{text}"

Translation:"""
            
            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                timeout=30
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise TranslationBackendError(f"OpenAI error: {e}") from e
    
    def _nllb_translate(self, text: str) -> str:
        """High-quality offline translation using Meta's NLLB-200"""
        try:
            if self._nllb_model is None:
                self.download_model()
            
            src_code = NLLB_LANG_CODES.get(self.source_lang, "jpn_Jpan")
            tgt_code = NLLB_LANG_CODES.get(self.target_lang, "eng_Latn")
            
            self._nllb_tokenizer.src_lang = src_code
            inputs = self._nllb_tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
            
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
            raise TranslationBackendError("transformers not installed. Install with: pip install transformers sentencepiece")
        except Exception as e:
            logger.error(f"NLLB translation error: {e}")
            raise TranslationBackendError(f"NLLB translation error: {e}") from e
    
    def _opus_translate(self, text: str) -> str:
        """Fast offline translation using Helsinki-NLP OPUS-MT"""
        try:
            if self._opus_model is None:
                self.download_model()
            
            inputs = self._opus_tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
            translated_tokens = self._opus_model.generate(**inputs, max_length=512)
            result = self._opus_tokenizer.decode(translated_tokens[0], skip_special_tokens=True)
            return result
            
        except ImportError:
            raise TranslationBackendError("transformers not installed. Install with: pip install transformers sentencepiece")
        except Exception as e:
            logger.error(f"OPUS-MT translation error: {e}")
            logger.info("Falling back to NLLB...")
            return self._nllb_translate(text)