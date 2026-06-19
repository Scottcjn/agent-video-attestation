# SPDX-License-Identifier: Apache-2.0
"""
AVAP envelope: the signed, anchorable unit of agent-to-agent information transfer.

An envelope is a JSON object an agent attaches to a video. It binds:
  * WHO     - sender Ed25519 public key + RustChain address, optional recipient
  * WHAT    - the payload (arbitrary info the sender is transferring) plus the
              media fingerprint of the video the envelope is bound to
  * WHEN    - issued_at + a commitment hash that is anchored on RustChain

The "signed core" is every field except `sig` and `anchor`. The sender signs the
canonical bytes of the signed core; the commitment that gets anchored on-chain is
sha256 of those same bytes. So one canonicalization secures the signature, the
on-chain attestation, and cross-implementation interop.
"""
from __future__ import annotations

import base64
import time
from typing import Any, Dict, Optional

from .crypto import (
    AgentKey,
    address_matches_pubkey,
    canonical,
    sha256_hex,
    verify_signature,
)

AVAP_VERSION = "1.0"
BROADCAST = "*"  # recipient value meaning "any agent"


def _signed_core(env: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in env.items() if k not in ("sig", "anchor")}


def build_envelope(
    sender: AgentKey,
    payload: Any,
    media_fingerprint: str,
    *,
    video_id: str = "",
    recipient: str = BROADCAST,
    msg_type: str = "agent.message",
    issued_at: Optional[int] = None,
    nonce: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a signed (but not yet anchored) AVAP envelope.

    payload may be any JSON-serializable object, or raw bytes (stored base64).
    media_fingerprint binds the envelope to a specific video (see embed.media_fingerprint).
    """
    if isinstance(payload, (bytes, bytearray)):
        payload_value = base64.b64encode(bytes(payload)).decode("ascii")
        payload_encoding = "base64"
    else:
        payload_value = payload
        payload_encoding = "json"

    issued_at = int(time.time()) if issued_at is None else int(issued_at)
    nonce = issued_at * 1000 if nonce is None else int(nonce)

    env: Dict[str, Any] = {
        "avap": AVAP_VERSION,
        "type": msg_type,
        "video_id": video_id,
        "media_fingerprint": media_fingerprint,
        "sender": {"address": sender.address, "public_key": sender.public_hex},
        "recipient": recipient,
        "payload": payload_value,
        "payload_encoding": payload_encoding,
        "issued_at": issued_at,
        "nonce": nonce,
    }

    core_bytes = canonical(_signed_core(env))
    env["sig"] = sender.sign(core_bytes)
    env["anchor"] = {
        "chain": "rustchain",
        "commitment": sha256_hex(core_bytes),
        "status": "unanchored",
        "tx": "",
        "node": "",
        "anchored_at": 0,
    }
    return env


def commitment_of(env: Dict[str, Any]) -> str:
    """The commitment hash that is (or will be) anchored on-chain."""
    return sha256_hex(canonical(_signed_core(env)))


def decode_payload(env: Dict[str, Any]) -> Any:
    if env.get("payload_encoding") == "base64":
        return base64.b64decode(env["payload"])
    return env["payload"]


def attach_anchor(env: Dict[str, Any], receipt: Dict[str, Any]) -> Dict[str, Any]:
    """Record an on-chain anchoring receipt on the envelope (does not re-sign)."""
    env["anchor"].update(
        {
            "chain": receipt.get("chain", env["anchor"]["chain"]),
            "tx": receipt.get("tx", ""),
            "node": receipt.get("node", ""),
            "anchored_at": int(receipt.get("anchored_at", int(time.time()))),
            "status": "anchored",
        }
    )
    return env


class VerifyResult(dict):
    """Structured verification result; truthy iff every required check passed."""

    @property
    def ok(self) -> bool:
        return bool(self.get("ok"))

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.ok


def verify_envelope(
    env: Dict[str, Any],
    *,
    media_fingerprint: Optional[str] = None,
    require_anchor: bool = False,
) -> VerifyResult:
    """Verify an AVAP envelope.

    Checks, in order:
      1. structural version
      2. sender address is the hash of the embedded public key
      3. commitment recomputes from the signed core and matches anchor.commitment
      4. Ed25519 signature over the signed core
      5. (optional) the bound media fingerprint matches the actual video
      6. (optional) the envelope claims to be anchored on-chain

    On-chain *existence* of the commitment is confirmed separately by anchor.verify_anchor,
    which talks to a RustChain node; this function verifies everything offline-checkable.
    """
    checks: Dict[str, bool] = {}
    sender = env.get("sender", {})
    pub = sender.get("public_key", "")
    addr = sender.get("address", "")

    checks["version"] = env.get("avap") == AVAP_VERSION
    checks["address_binding"] = bool(pub) and address_matches_pubkey(addr, pub)

    recomputed = commitment_of(env)
    checks["commitment"] = recomputed == env.get("anchor", {}).get("commitment")

    core_bytes = canonical(_signed_core(env))
    checks["signature"] = bool(pub) and verify_signature(pub, core_bytes, env.get("sig", ""))

    if media_fingerprint is not None:
        checks["media_binding"] = media_fingerprint == env.get("media_fingerprint")

    if require_anchor:
        checks["anchored"] = env.get("anchor", {}).get("status") == "anchored" and bool(
            env.get("anchor", {}).get("tx")
        )

    result = VerifyResult(checks=checks, commitment=recomputed)
    result["ok"] = all(checks.values())
    return result
