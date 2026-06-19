# SPDX-License-Identifier: Apache-2.0
"""
High-level one-call AVAP pipeline.

    send():     fingerprint a video -> build & sign an envelope -> anchor its
                commitment on RustChain -> embed it in the video (container +/or
                sidecar). Returns the anchored envelope and the output path.

    receive():  extract the envelope from a video -> verify signature, address
                binding, commitment, and (re-fingerprinting the file) the media
                binding -> optionally confirm the commitment is anchored on-chain.
                Returns (VerifyResult, decoded_payload, envelope).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from .anchor import LocalAnchor
from .crypto import AgentKey
from .embed import (
    embed_container,
    extract_envelope,
    media_fingerprint,
    write_sidecar,
)
from .envelope import (
    BROADCAST,
    attach_anchor,
    build_envelope,
    decode_payload,
    verify_envelope,
)


def send(
    video_path: str,
    sender: AgentKey,
    payload: Any,
    *,
    recipient: str = BROADCAST,
    msg_type: str = "agent.message",
    video_id: str = "",
    anchor=None,
    out_path: Optional[str] = None,
    container: bool = True,
    sidecar: bool = True,
) -> Tuple[Dict[str, Any], str]:
    """Attach a signed, anchored AVAP envelope to a video.

    anchor defaults to LocalAnchor() (offline). Pass RustChainAnchor(...) to
    anchor on a live node. Returns (envelope, output_video_path).
    """
    anchor = anchor or LocalAnchor()
    fp = media_fingerprint(video_path)

    env = build_envelope(
        sender, payload, fp,
        video_id=video_id, recipient=recipient, msg_type=msg_type,
    )
    receipt = anchor.anchor(env["anchor"]["commitment"], video_id=video_id,
                            sender=sender.address)
    env = attach_anchor(env, receipt)

    target = video_path
    if container:
        target = out_path or (os.path.splitext(video_path)[0] + ".avap.mp4")
        embed_container(video_path, env, target)
    if sidecar:
        write_sidecar(target, env)
    return env, target


def receive(
    video_path: str,
    *,
    anchor=None,
    require_anchor: bool = False,
    verify_onchain: bool = False,
) -> Tuple[Any, Any, Optional[Dict[str, Any]]]:
    """Extract and verify an AVAP envelope from a video.

    Returns (VerifyResult, payload, envelope). payload/envelope are None if no
    envelope is present. If verify_onchain is True, the commitment is checked
    against the anchoring backend (anchor.verify).
    """
    env = extract_envelope(video_path)
    if env is None:
        return None, None, None

    fp = media_fingerprint(video_path)
    result = verify_envelope(env, media_fingerprint=fp, require_anchor=require_anchor)

    if verify_onchain:
        anchor = anchor or LocalAnchor()
        a = env.get("anchor", {})
        onchain = anchor.verify(a.get("commitment", ""), tx=a.get("tx", ""))
        result["checks"]["onchain"] = bool(onchain)
        result["ok"] = all(result["checks"].values())

    payload = decode_payload(env) if result.ok else None
    return result, payload, env
