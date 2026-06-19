"""
Embedding AVAP envelopes into video files.

Two transport profiles are defined; both are implemented here:

  * SIDECAR   - write `<video>.avap.json` beside the file. Always works, and is
                what a platform serves at e.g. GET /api/video/<id>/avap.
  * CONTAINER - store the envelope inside the MP4/MOV metadata as a base64 string
                under the `avap` tag (ffmpeg `-movflags use_metadata_tags`).

Both profiles bind to the video through a *media fingerprint* computed from the
codec packet data (ffmpeg `streamhash`), NOT the container bytes. Consequence:
attaching/removing the envelope does not change the fingerprint, but re-encoding
or editing the actual audio/video does -> tamper-evident attestation in the video.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from typing import Any, Dict, Optional

from .crypto import canonical

CONTAINER_TAG = "avap"


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def media_fingerprint(path: str) -> str:
    """Metadata-independent fingerprint of a video's codec packet data.

    Hashes every stream's packets with sha256 (container/metadata excluded), then
    folds the per-stream hashes into one canonical digest. Re-encoding or editing
    frames changes this; adding the AVAP metadata tag does not.
    """
    proc = _run(
        [
            "ffmpeg", "-v", "error", "-i", path,
            "-map", "0", "-c", "copy",
            "-f", "streamhash", "-hash", "sha256", "-",
        ]
    )
    if proc.returncode == 0 and proc.stdout.strip():
        # lines look like:  0,v,sha256=<hex>
        per_stream = sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())
        return hashlib.sha256("\n".join(per_stream).encode()).hexdigest()
    # Fallback: hash raw file bytes (document: embed must precede signing in this mode)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_path(video_path: str) -> str:
    return video_path + ".avap.json"


def write_sidecar(video_path: str, env: Dict[str, Any]) -> str:
    out = sidecar_path(video_path)
    with open(out, "wb") as f:
        f.write(canonical(env))
    return out


def read_sidecar(video_path: str) -> Optional[Dict[str, Any]]:
    p = sidecar_path(video_path)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def embed_container(video_path: str, env: Dict[str, Any], out_path: str) -> str:
    """Write a new video file with the envelope stored in container metadata."""
    import base64

    blob = base64.b64encode(canonical(env)).decode("ascii")
    proc = _run(
        [
            "ffmpeg", "-v", "error", "-y", "-i", video_path,
            "-map", "0", "-c", "copy",
            "-movflags", "use_metadata_tags",
            "-metadata", f"{CONTAINER_TAG}={blob}",
            out_path,
        ]
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg embed failed: {proc.stderr.strip()}")
    return out_path


def extract_container(video_path: str) -> Optional[Dict[str, Any]]:
    """Read an AVAP envelope from container metadata, if present."""
    import base64

    proc = _run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format_tags",
            "-of", "json", video_path,
        ]
    )
    if proc.returncode != 0:
        return None
    try:
        tags = json.loads(proc.stdout).get("format", {}).get("tags", {})
    except json.JSONDecodeError:
        return None
    # ffprobe may lowercase/normalize tag keys
    blob = tags.get(CONTAINER_TAG) or tags.get(CONTAINER_TAG.upper())
    if not blob:
        return None
    try:
        return json.loads(base64.b64decode(blob).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


def extract_envelope(video_path: str) -> Optional[Dict[str, Any]]:
    """Return the envelope from container metadata, falling back to the sidecar."""
    return extract_container(video_path) or read_sidecar(video_path)
