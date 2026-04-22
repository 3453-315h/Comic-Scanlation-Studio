"""
Plugin System - Comic Translation Studio

Sandboxed plugin execution via WebAssembly (Wasmtime).
Allows users to write custom text preprocessors, post-processors, and hooks.

Example use cases:
- Custom translation quirks (e.g., honorific handling)
- Text normalizers (e.g., punctuation fixes)
- OCR result validators
"""
