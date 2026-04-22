# Scanlation Tool Plugin Development Guide

This document explains how to create plugins for the Comic Translation Studio.

## Overview

Plugins can hook into various stages of the translation pipeline:

| Hook | Description |
|------|-------------|
| `pre_translate` | Process text before sending to translation API |
| `post_translate` | Process translated text before display |
| `pre_ocr` | Modify image region before OCR |
| `post_ocr` | Process extracted OCR text |
| `pre_inpaint` | Modify image before text removal |
| `post_inpaint` | Process image after text removal |
| `pre_imprint` | Process text before rendering |
| `post_imprint` | Process image after text rendering |

## Plugin Types

### 1. Python Built-in Plugins (Recommended for starters)

Create a Python class with methods matching hook names:

```python
class MyPlugin:
    def pre_translate(self, text: str) -> str:
        # Add honorific preservation
        return text.replace("さん", "__SAN__")
    
    def post_translate(self, text: str) -> str:
        return text.replace("__SAN__", "-san")
```

Register it:

```python
from src.plugins.loader import get_plugin_loader

loader = get_plugin_loader()
loader.register_builtin(MyPlugin())
```

### 2. Wasm Plugins (Advanced - Sandboxed)

For maximum security and language flexibility, compile your plugin to WebAssembly.

**Requirements:**
- A `.wasm` file (compiled from Rust, C, etc.)
- A `.json` metadata file with the same name

**Example metadata (my_plugin.json):**

```json
{
    "name": "My Custom Plugin",
    "version": "1.0.0",
    "description": "Handles special translation quirks",
    "author": "Your Name",
    "hooks": ["pre_translate", "post_translate"]
}
```

Place both files in the `plugins/` directory.

## Example: Rust Wasm Plugin

```rust
// lib.rs
#[no_mangle]
pub extern "C" fn pre_translate(text_ptr: *const u8, text_len: usize) -> *const u8 {
    // Process text and return pointer to result
    // (Memory management details omitted for brevity)
}
```

Compile with:
```bash
cargo build --target wasm32-unknown-unknown --release
```

## Security

Wasm plugins run in a sandboxed environment with:
- No filesystem access
- No network access
- Limited memory (configurable)
- CPU time limits

This ensures plugins cannot harm your system.
