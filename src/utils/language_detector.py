"""
Language Detection Utility - Comic Translation Studio

Auto-detects source language from text content.
Optimized for European languages (comics, BD, fumetti, etc.)
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Language patterns focused on European languages
LANGUAGE_PATTERNS = {
    # European languages (primary focus)
    "en": {
        "name": "English",
        "font_suggestion": "Comic Sans MS"
    },
    "fr": {
        "name": "French",
        "font_suggestion": "Comic Sans MS"
    },
    "de": {
        "name": "German",
        "font_suggestion": "Comic Sans MS"
    },
    "es": {
        "name": "Spanish",
        "font_suggestion": "Comic Sans MS"
    },
    "it": {
        "name": "Italian",
        "font_suggestion": "Comic Sans MS"
    },
    "pt": {
        "name": "Portuguese",
        "font_suggestion": "Comic Sans MS"
    },
    "nl": {
        "name": "Dutch",
        "font_suggestion": "Comic Sans MS"
    },
    "pl": {
        "name": "Polish",
        "font_suggestion": "Comic Sans MS"
    },
    "ru": {
        "name": "Russian",
        "font_suggestion": "Arial"
    },
    "uk": {
        "name": "Ukrainian",
        "font_suggestion": "Arial"
    },
    "cs": {
        "name": "Czech",
        "font_suggestion": "Comic Sans MS"
    },
    "ro": {
        "name": "Romanian",
        "font_suggestion": "Comic Sans MS"
    },
    "hu": {
        "name": "Hungarian",
        "font_suggestion": "Comic Sans MS"
    },
    "sv": {
        "name": "Swedish",
        "font_suggestion": "Comic Sans MS"
    },
    "da": {
        "name": "Danish",
        "font_suggestion": "Comic Sans MS"
    },
    "no": {
        "name": "Norwegian",
        "font_suggestion": "Comic Sans MS"
    },
    "fi": {
        "name": "Finnish",
        "font_suggestion": "Comic Sans MS"
    },
    "el": {
        "name": "Greek",
        "font_suggestion": "Arial"
    },
    "tr": {
        "name": "Turkish",
        "font_suggestion": "Arial"
    },
    # Asian languages (secondary)
    "ja": {
        "name": "Japanese",
        "font_suggestion": "Noto Sans JP"
    },
    "ko": {
        "name": "Korean",
        "font_suggestion": "Noto Sans KR"
    },
    "zh-cn": {
        "name": "Chinese (Simplified)",
        "font_suggestion": "Noto Sans SC"
    },
    "zh-tw": {
        "name": "Chinese (Traditional)",
        "font_suggestion": "Noto Sans TC"
    },
}

# All supported language codes for UI
SUPPORTED_LANGUAGES = [
    "en", "fr", "de", "es", "it", "pt", "nl", "pl", "ru", "uk",
    "cs", "ro", "hu", "sv", "da", "no", "fi", "el", "tr",
    "ja", "ko", "zh-cn", "zh-tw"
]


def detect_language_from_text(text: str) -> Tuple[str, str, float]:
    """Detect language from text content
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (language_code, font_suggestion, confidence)
    """
    if not text or len(text.strip()) < 3:
        return "en", "Comic Sans MS", 0.0  # Default to English
    
    # Use langdetect library
    try:
        from langdetect import detect, detect_langs
        detected = detect(text)
        
        # Normalize Chinese variants
        if detected == "zh-cn" or detected == "zh-tw":
            pass  # Keep as is
        elif detected.startswith("zh"):
            detected = "zh-cn"
        
        # Get confidence
        probs = detect_langs(text)
        confidence = probs[0].prob if probs else 0.5
        
        font = LANGUAGE_PATTERNS.get(detected, {}).get("font_suggestion", "Comic Sans MS")
        lang_name = LANGUAGE_PATTERNS.get(detected, {}).get("name", detected.upper())
        
        logger.info(f"Detected language: {lang_name} ({detected}) - confidence: {confidence:.2f}")
        return detected, font, confidence
        
    except ImportError:
        logger.warning("langdetect not installed, defaulting to English")
        return "en", "Comic Sans MS", 0.0
    except Exception as e:
        logger.warning(f"Language detection failed: {e}, defaulting to English")
        return "en", "Comic Sans MS", 0.0


def suggest_font_for_language(lang_code: str) -> str:
    """Get suggested font for a language
    
    Args:
        lang_code: ISO 639-1 language code
        
    Returns:
        Font name suggestion
    """
    return LANGUAGE_PATTERNS.get(lang_code, {}).get("font_suggestion", "Comic Sans MS")


def get_language_name(lang_code: str) -> str:
    """Get human-readable language name"""
    return LANGUAGE_PATTERNS.get(lang_code, {}).get("name", lang_code.upper())


# Common comic fonts for European languages
COMIC_FONTS = [
    "Comic Sans MS",
    "Wild Words",
    "Manga Temple",
    "CC Wild Words",
    "Badaboom",
    "Komika",
    "Bangers",
    "Permanent Marker",
    "Patrick Hand",
    "Arial",
    "Verdana"
]
