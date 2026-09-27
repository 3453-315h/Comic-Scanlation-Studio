import pytest
from pathlib import Path

from src.plugins.loader import WasmPluginLoader, PluginMetadata
from src.plugins.interfaces import PluginHook, PluginContext

def test_wasm_plugin_explicit_unsupported_status(tmp_path):
    """Wasm plugin execution must explicitly report failure/unsupported status, not placeholder success."""
    loader = WasmPluginLoader(tmp_path)
    
    metadata = PluginMetadata(
        name="test_plugin",
        version="1.0.0",
        description="Test",
        author="Author",
        hooks=[PluginHook.PRE_TRANSLATE],
        path=str(tmp_path / "test.wasm")
    )
    loader.plugins[metadata.name] = metadata
    
    ctx = PluginContext(
        hook=PluginHook.PRE_TRANSLATE,
        data={"text": "test input"}
    )
    
    # Test _execute_wasm_plugin directly
    result = loader._execute_wasm_plugin(metadata, ctx)
    assert not result.success
    assert any("unsupported" in log.lower() for log in result.logs)
    
    # Test call_hook when WASMTIME_AVAILABLE is True (or mocked True)
    loader_was_avail = loader.is_available
    try:
        import src.plugins.loader as loader_mod
        loader_mod.WASMTIME_AVAILABLE = True
        
        call_res = loader.call_hook(PluginHook.PRE_TRANSLATE, ctx)
        assert not call_res.success
        assert any("unsupported" in log.lower() for log in call_res.logs)
    finally:
        import src.plugins.loader as loader_mod
        loader_mod.WASMTIME_AVAILABLE = loader_was_avail
