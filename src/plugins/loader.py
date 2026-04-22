"""
Wasm Plugin Loader - Comic Translation Studio

Sandboxed plugin execution via WebAssembly (Wasmtime).
Provides secure, isolated execution of user-defined plugins.
"""

from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import logging
import json

from .interfaces import (
    PluginHook, PluginContext, PluginResult, PluginMetadata
)

logger = logging.getLogger(__name__)

# Try to import wasmtime, gracefully degrade if not available
try:
    import wasmtime
    WASMTIME_AVAILABLE = True
except ImportError:
    WASMTIME_AVAILABLE = False
    logger.warning("wasmtime not installed. Wasm plugins disabled. Install with: pip install wasmtime")


class WasmPluginLoader:
    """
    Loads and executes WebAssembly plugins in a sandboxed environment.
    
    Example usage:
        loader = WasmPluginLoader(Path("./plugins"))
        loader.discover_plugins()
        
        ctx = PluginContext(
            hook=PluginHook.PRE_TRANSLATE,
            data={"text": "こんにちは"}
        )
        result = loader.call_hook(PluginHook.PRE_TRANSLATE, ctx)
    """
    
    def __init__(self, plugins_dir: Path):
        """
        Initialize the plugin loader.
        
        Args:
            plugins_dir: Directory containing .wasm plugin files
        """
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, PluginMetadata] = {}
        self._hook_handlers: Dict[PluginHook, List[Callable]] = {h: [] for h in PluginHook}
        
        # Wasmtime components (initialized on first use)
        self._engine: Optional["wasmtime.Engine"] = None
        self._store: Optional["wasmtime.Store"] = None
        self._linker: Optional["wasmtime.Linker"] = None
        
        # Built-in Python plugins (always available)
        self._builtin_plugins: List[Any] = []
        
    @property
    def is_available(self) -> bool:
        """Check if Wasm runtime is available"""
        return WASMTIME_AVAILABLE
    
    def _init_runtime(self) -> bool:
        """Initialize the Wasmtime runtime (lazy initialization)"""
        if not WASMTIME_AVAILABLE:
            return False
            
        if self._engine is None:
            try:
                self._engine = wasmtime.Engine()
                self._store = wasmtime.Store(self._engine)
                self._linker = wasmtime.Linker(self._engine)
                
                # Add host functions that plugins can call
                self._setup_host_functions()
                
                logger.info("Wasmtime runtime initialized")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Wasmtime: {e}")
                return False
        return True
    
    def _setup_host_functions(self) -> None:
        """Set up host functions that Wasm plugins can import"""
        if self._linker is None:
            return
            
        # Example: log function for plugins
        # Plugins can call: (import "host" "log" (func (param i32 i32)))
        # This would be expanded in a full implementation
        pass
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """
        Scan plugins directory and load all valid plugins.
        
        Returns:
            List of successfully loaded plugin metadata
        """
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created plugins directory: {self.plugins_dir}")
            return []
        
        discovered = []
        
        # Look for .wasm files with accompanying metadata
        for wasm_file in self.plugins_dir.glob("*.wasm"):
            meta_file = wasm_file.with_suffix(".json")
            
            if meta_file.exists():
                try:
                    metadata = self._load_plugin_metadata(wasm_file, meta_file)
                    self.plugins[metadata.name] = metadata
                    discovered.append(metadata)
                    logger.info(f"Discovered plugin: {metadata.name} v{metadata.version}")
                except Exception as e:
                    logger.warning(f"Failed to load plugin {wasm_file.name}: {e}")
        
        return discovered
    
    def _load_plugin_metadata(self, wasm_path: Path, meta_path: Path) -> PluginMetadata:
        """Load plugin metadata from JSON file"""
        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return PluginMetadata(
            name=data.get("name", wasm_path.stem),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            author=data.get("author", "Unknown"),
            hooks=[PluginHook(h) for h in data.get("hooks", [])],
            path=str(wasm_path)
        )
    
    def load_plugin(self, path: Path) -> Optional[PluginMetadata]:
        """
        Load a single .wasm plugin file.
        
        Args:
            path: Path to the .wasm file
            
        Returns:
            Plugin metadata if successful, None otherwise
        """
        if not self._init_runtime():
            logger.warning("Wasmtime not available, cannot load Wasm plugin")
            return None
            
        if not path.exists():
            logger.error(f"Plugin file not found: {path}")
            return None
        
        try:
            # Load the Wasm module
            module = wasmtime.Module.from_file(self._engine, str(path))
            
            # Instantiate the module
            instance = self._linker.instantiate(self._store, module)
            
            # Get exported functions
            # Plugins should export: get_metadata, handle_hook
            # This is a simplified implementation
            
            meta_path = path.with_suffix(".json")
            if meta_path.exists():
                metadata = self._load_plugin_metadata(path, meta_path)
            else:
                metadata = PluginMetadata(
                    name=path.stem,
                    version="1.0.0",
                    description="Wasm plugin (no metadata)",
                    author="Unknown",
                    hooks=[],
                    path=str(path)
                )
            
            self.plugins[metadata.name] = metadata
            logger.info(f"Loaded Wasm plugin: {metadata.name}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load plugin {path}: {e}")
            return None
    
    def call_hook(self, hook: PluginHook, context: PluginContext) -> PluginResult:
        """
        Call all registered plugins for a specific hook.
        
        Args:
            hook: The hook point being executed
            context: Context data for the hook
            
        Returns:
            Combined result from all plugins
        """
        context.hook = hook
        result_data = context.data.copy()
        all_logs = []
        
        # Call built-in Python plugins first
        for plugin in self._builtin_plugins:
            handler_name = hook.value  # e.g., "pre_translate"
            if hasattr(plugin, handler_name):
                try:
                    handler = getattr(plugin, handler_name)
                    # Simple text-based hooks
                    if "text" in result_data:
                        result_data["text"] = handler(result_data["text"])
                except Exception as e:
                    all_logs.append(f"Built-in plugin error: {e}")
        
        # Call Wasm plugins (if available)
        if WASMTIME_AVAILABLE:
            for name, metadata in self.plugins.items():
                if hook in metadata.hooks:
                    try:
                        plugin_result = self._execute_wasm_plugin(metadata, context)
                        if plugin_result.success:
                            result_data.update(plugin_result.data)
                        all_logs.extend(plugin_result.logs)
                    except Exception as e:
                        all_logs.append(f"Plugin {name} error: {e}")
        
        return PluginResult(
            success=True,
            data=result_data,
            logs=all_logs
        )
    
    def _execute_wasm_plugin(self, metadata: PluginMetadata, context: PluginContext) -> PluginResult:
        """Execute a Wasm plugin with the given context"""
        # In a full implementation, this would:
        # 1. Serialize context to a format the Wasm plugin understands
        # 2. Call the plugin's exported handle_hook function
        # 3. Deserialize the result
        
        # For now, return a placeholder result
        return PluginResult(
            success=True,
            data=context.data,
            logs=[f"Wasm plugin {metadata.name} executed (placeholder)"]
        )
    
    def register_builtin(self, plugin: Any) -> None:
        """
        Register a Python-based built-in plugin.
        
        Args:
            plugin: Object with methods named after hooks (e.g., pre_translate)
        """
        self._builtin_plugins.append(plugin)
        logger.info(f"Registered built-in plugin: {type(plugin).__name__}")
    
    def list_plugins(self) -> List[PluginMetadata]:
        """List all loaded plugins"""
        return list(self.plugins.values())


# Convenience function for creating a global loader
_global_loader: Optional[WasmPluginLoader] = None

def get_plugin_loader(plugins_dir: Optional[Path] = None) -> WasmPluginLoader:
    """Get or create the global plugin loader"""
    global _global_loader
    
    if _global_loader is None:
        if plugins_dir is None:
            plugins_dir = Path(__file__).parent.parent.parent / "plugins"
        _global_loader = WasmPluginLoader(plugins_dir)
    
    return _global_loader
