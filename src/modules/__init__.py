"""
AI/ML processing modules for the scanlation pipeline stages.
Each module is swappable and encapsulates a specific model/backend.
"""

from .detector import TextDetector
from .ocr import MangaOCR
from .inpainter import LamaInpainter
from .translator import Translator
from .imprinter import TextImprinter, FontStyle

__all__ = [
    "TextDetector",
    "MangaOCR", 
    "LamaInpainter",
    "Translator",
    "TextImprinter",
    "FontStyle"
]
