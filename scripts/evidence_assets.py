"""Read portable raster evidence without importing files outside its bundle."""
from __future__ import annotations

import base64
from pathlib import Path

MAX_RASTER_BYTES = 25 * 1024 * 1024


def confined_path(src: str, base: Path) -> Path:
    path = Path(src)
    if path.is_absolute():
        raise ValueError("evidence must use a bundle-relative path")
    root = base.resolve()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("evidence path escapes the bundle")
    return resolved


def embed_raster(src: str, base: Path) -> str:
    """Return a bounded image URI, or empty for missing/unsafe/non-raster data."""
    try:
        path = confined_path(src, base)
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_RASTER_BYTES:
            return ""
        with path.open("rb") as handle:
            raw = handle.read(MAX_RASTER_BYTES + 1)
        if len(raw) > MAX_RASTER_BYTES:
            return ""
        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif raw.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif raw.startswith((b"GIF87a", b"GIF89a")):
            mime = "image/gif"
        elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            mime = "image/webp"
        else:
            return ""
        extensions = {"image/png": {".png"}, "image/jpeg": {".jpg", ".jpeg"},
                      "image/gif": {".gif"}, "image/webp": {".webp"}}
        if path.suffix.lower() not in extensions[mime]:
            return ""
        return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    except (OSError, ValueError):
        return ""
