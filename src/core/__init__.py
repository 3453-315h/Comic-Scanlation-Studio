"""
Core business logic and data models for the scanlation pipeline.
"""

# Avoid importing heavy modules here to prevent startup slowing/crashes
# Imports should be done explicitly in the using modules
# e.g. from src.core.pipeline import ScanlationPipeline

from .config import Config

__all__ = [
    "Config"
]