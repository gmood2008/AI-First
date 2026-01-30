"""
StdLib loader - Automatic registration of standard library capabilities.

This module provides functions to load and register all 20 standard library capabilities.
"""

from pathlib import Path
from typing import Dict, Any

from ..registry import CapabilityRegistry
from .fs_handlers import (
    ReadFileHandler,
    HashFileHandler,
    WriteFileHandler,
    ListDirHandler,
    MakeDirHandler,
    DeleteHandler,
    ExistsHandler,
    MoveHandler,
    CopyHandler,
)
from .sys_handlers import (
    GetOSHandler,
    GetEnvVarHandler,
    GetTimeHandler,
    ExecRunHandler,
    ZipHandler,
)
from .net_handlers import (
    HTTPGetHandler,
    HTTPPostHandler,
    HTTPPutHandler,
)
from .data_handlers import (
    JSONParseHandler,
    JSONStringifyHandler,
    JSONGetHandler,
    RegexMatchHandler,
    TemplateRenderHandler,
)
from .pdf_handlers import PdfExtractTableHandler
from .pandas_handlers import PandasCalculateHandler
from .fs_bytes_handlers import WriteBytesHandler

try:
    from .web_browser_handlers import WebBrowserNavigateHandler, WebBrowserSnapshotHandler
except Exception:
    WebBrowserNavigateHandler = None
    WebBrowserSnapshotHandler = None

try:
    from .presentation_handlers import PPTXRenderHandler
    from .presentation_theme_handlers import PresentationThemeApplyHandler
    from .markdown_handlers import MarkdownToSlidesHandler
except Exception:
    PPTXRenderHandler = None
    PresentationThemeApplyHandler = None
    MarkdownToSlidesHandler = None


# Mapping of capability IDs to handler classes
STDLIB_HANDLERS = {
    # Filesystem (8)
    "io.fs.read_file": ReadFileHandler,
    "io.fs.hash_file": HashFileHandler,
    "io.fs.write_file": WriteFileHandler,
    "io.fs.list_dir": ListDirHandler,
    "io.fs.make_dir": MakeDirHandler,
    "io.fs.delete": DeleteHandler,
    "io.fs.exists": ExistsHandler,
    "io.fs.move": MoveHandler,
    "io.fs.copy": CopyHandler,
    
    # System (5)
    "sys.info.get_os": GetOSHandler,
    "sys.info.get_env_var": GetEnvVarHandler,
    "sys.info.get_time": GetTimeHandler,
    "sys.exec.run": ExecRunHandler,
    "sys.archive.zip": ZipHandler,
    
    # Network (3)
    "net.http.get": HTTPGetHandler,
    "net.http.post": HTTPPostHandler,
    "net.http.put": HTTPPutHandler,
    
    # Data (4)
    "data.json.parse": JSONParseHandler,
    "data.json.stringify": JSONStringifyHandler,
    "data.json.get": JSONGetHandler,
    "text.regex.match": RegexMatchHandler,
    "text.template.render": TemplateRenderHandler,

    # PDF (1) - financial report workflow
    "io.pdf.extract_table": PdfExtractTableHandler,
    # Math / Pandas (1) - financial report workflow
    "math.pandas.calculate": PandasCalculateHandler,

    **({
        "web.browser.navigate": WebBrowserNavigateHandler,
        "web.browser.snapshot": WebBrowserSnapshotHandler,
    } if WebBrowserNavigateHandler is not None and WebBrowserSnapshotHandler is not None else {}),

    **({
        "io.presentation.pptx.render": PPTXRenderHandler,
        "io.presentation.theme.apply": PresentationThemeApplyHandler,
        "io.presentation.markdown.to_slides": MarkdownToSlidesHandler,
    } if PPTXRenderHandler is not None and PresentationThemeApplyHandler is not None and MarkdownToSlidesHandler is not None else {}),
    "io.fs.write_bytes": WriteBytesHandler,
}


def load_stdlib(
    registry: CapabilityRegistry,
    specs_dir: Path,
) -> int:
    """
    Load all standard library capabilities into registry.
    
    This function:
    1. Reads YAML specs from the specs directory
    2. Creates handler instances
    3. Registers them in the registry
    
    Args:
        registry: CapabilityRegistry to register into
        specs_dir: Directory containing YAML specifications
    
    Returns:
        Number of capabilities loaded
    
    Raises:
        FileNotFoundError: If specs_dir doesn't exist
        ValueError: If spec/handler mismatch
    """
    if not specs_dir.exists():
        raise FileNotFoundError(f"Specs directory not found: {specs_dir}")
    
    loaded_count = 0
    errors = []
    
    print(f"📚 Loading StdLib from {specs_dir}")
    print("=" * 70)
    
    for capability_id, handler_class in STDLIB_HANDLERS.items():
        try:
            # Find YAML spec file
            # Convert io.fs.read_file -> io_fs_read_file.yaml
            spec_filename = capability_id.replace(".", "_") + ".yaml"
            spec_path = specs_dir / spec_filename
            
            # Try to load spec (local first, then GitHub)
            spec_dict = None
            
            if spec_path.exists():
                # Load from local file
                import yaml
                with open(spec_path, "r") as f:
                    spec_dict = yaml.safe_load(f)
            else:
                # Try loading from GitHub if local file not found
                try:
                    from runtime.remote_loader import load_capability_from_github
                    print(f"📡 Loading {capability_id} from GitHub...")
                    spec_dict = load_capability_from_github(capability_id)
                    if spec_dict:
                        print(f"✅ Loaded {capability_id} from GitHub")
                    else:
                        errors.append(f"❌ Spec not found locally or on GitHub: {spec_filename}")
                        continue
                except ImportError:
                    errors.append(f"❌ Spec not found: {spec_filename} (remote loading not available)")
                    continue
                except Exception as e:
                    errors.append(f"❌ Failed to load {capability_id} from GitHub: {e}")
                    continue
            
            # Verify capability ID matches
            if spec_dict["meta"]["id"] != capability_id:
                errors.append(
                    f"❌ ID mismatch: {spec_filename} declares "
                    f"{spec_dict['meta']['id']}, expected {capability_id}"
                )
                continue
            
            # Create handler instance
            handler = handler_class(spec_dict)
            
            # Register
            registry.register(capability_id, handler, spec_dict)
            loaded_count += 1
        
        except Exception as e:
            errors.append(f"❌ Failed to load {capability_id}: {e}")
    
    print("=" * 70)
    print(f"✅ Loaded {loaded_count}/{len(STDLIB_HANDLERS)} capabilities")
    
    if errors:
        print(f"\n⚠️  {len(errors)} errors:")
        for error in errors:
            print(f"  {error}")
    
    return loaded_count


def get_stdlib_info() -> Dict[str, Any]:
    """
    Get information about standard library.
    
    Returns:
        Dictionary with stdlib metadata
    """
    namespaces = {}
    for capability_id in STDLIB_HANDLERS.keys():
        parts = capability_id.split(".")
        namespace = ".".join(parts[:-1])
        
        if namespace not in namespaces:
            namespaces[namespace] = []
        namespaces[namespace].append(capability_id)
    
    return {
        "total_capabilities": len(STDLIB_HANDLERS),
        "namespaces": namespaces,
        "namespace_count": len(namespaces),
    }


def list_stdlib_capabilities() -> list:
    """
    List all standard library capability IDs.
    
    Returns:
        Sorted list of capability IDs
    """
    return sorted(STDLIB_HANDLERS.keys())
