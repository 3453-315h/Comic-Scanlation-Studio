"""
Plugin Interface Definitions - Comic Translation Studio

Defines the interfaces that plugins can implement and the hooks they can use.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PluginHook(Enum):
    """Available plugin hook points in the translation pipeline"""

    # Text Processing
    PRE_TRANSLATE = "pre_translate"      # Before translation API call
    POST_TRANSLATE = "post_translate"    # After translation API call
    PRE_OCR = "pre_ocr"                  # Before OCR on image region
    POST_OCR = "post_ocr"                # After OCR text extraction

    # Image Processing
    PRE_INPAINT = "pre_inpaint"          # Before text removal
    POST_INPAINT = "post_inpaint"        # After text removal
    PRE_IMPRINT = "pre_imprint"          # Before text rendering
    POST_IMPRINT = "post_imprint"        # After text rendering


@dataclass
class PluginContext:
    """Context passed to plugin hooks"""
    hook: PluginHook
    data: dict[str, Any]  # Hook-specific data

    # Common fields
    source_lang: str = "ja"
    target_lang: str = "en"
    page_index: int = 0
    bubble_index: int = 0


@dataclass
class PluginResult:
    """Result returned from plugin execution"""
    success: bool
    data: dict[str, Any]  # Modified data to pass back
    error: str | None = None
    logs: list[str] = None

    def __post_init__(self):
        if self.logs is None:
            self.logs = []


@dataclass
class PluginMetadata:
    """Metadata describing a loaded plugin"""
    name: str
    version: str
    description: str
    author: str
    hooks: list[PluginHook]  # Which hooks this plugin handles
    path: str  # Path to the .wasm file


class PluginInterface(ABC):
    """Abstract interface for plugins (for documentation purposes)"""

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """Execute the plugin with given context"""
        pass


# ─────────────────────────────────────────────────────────────
# Built-in Plugin Examples (Python-based, not Wasm)
# ─────────────────────────────────────────────────────────────

class HonorificPreprocessor:
    """
    Example built-in plugin: Preserve Japanese honorifics during translation.
    
    Replaces common honorifics with placeholders before translation,
    then restores them after.
    """

    HONORIFICS = {
        "さん": "-san",
        "くん": "-kun",
        "ちゃん": "-chan",
        "様": "-sama",
        "先生": "-sensei",
        "先輩": "-senpai",
        "後輩": "-kouhai"
    }

    def pre_translate(self, text: str) -> str:
        """Replace honorifics with placeholders"""
        result = text
        for jp, en in self.HONORIFICS.items():
            result = result.replace(jp, f"__HONORIFIC_{en}__")
        return result

    def post_translate(self, text: str) -> str:
        """Restore honorifics from placeholders"""
        result = text
        for jp, en in self.HONORIFICS.items():
            result = result.replace(f"__HONORIFIC_{en}__", en)
        return result
