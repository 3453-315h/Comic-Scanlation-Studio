"""
AI/ML processing modules for the scanlation pipeline stages.
Each module is swappable and encapsulates a specific model/backend.
"""

from .detector import TextDetector
from .imprinter import FontStyle, TextImprinter
from .inpainter import LamaInpainter
from .ocr import MangaOCR
from .translator import Translator

__all__ = [
    "TextDetector",
    "MangaOCR",
    "LamaInpainter",
    "Translator",
    "TextImprinter",
    "FontStyle"
]
