"""
RustChain anchoring for AVAP commitments.

Anchoring publishes an envelope's commitment hash to RustChain so the envelope's
existence is provable and immutably timestamped. The commitment (not the payload)
goes on-chain, so the actual transferred information stays private to the parties
holding the video while still being verifiable.

Reference interface (see SPEC.md §6):
    POST {node}/avap/anchor   {"commitment": "<hex>", "video_id": "...", "sender": "RTC..."}
        -> {"tx": "...", "anchored_at": <unix>}
    GET  {node}/avap/anchor/{commitment}
        -> {"anchored": true, "tx": "...", "anchored_at": <unix>}

On RustChain this can be served directly, or backed by the existing Ergo register
anchor (commitment in box register R4) documented in the RustChain node. For
offline development and tests, LocalAnchor produces a deterministic, content-
addressed receipt so the full pipeline runs without a node.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

try:  # requests is optional; LocalAnchor needs nothing
    import requests
except Exception:  # pragma: no cover
    requests = None

DEFAULT_NODE = "https://rustchain.org"


class AnchorError(RuntimeError):
    pass


class LocalAnchor:
    """Offline anchor: deterministic receipt, no network. For dev/tests/demos."""

    chain = "rustchain-local"

    def anchor(self, commitment: str, **meta: Any) -> Dict[str, Any]:
        return {
            "chain": self.chain,
            "tx": f"local:{commitment[:32]}",
            "node": "local",
            "anchored_at": int(meta.get("anchored_at", time.time())),
        }

    def verify(self, commitment: str, tx: str = "", **_: Any) -> bool:
        return tx == f"local:{commitment[:32]}"


class RustChainAnchor:
    """Anchors commitments on a live RustChain node over HTTP."""

    chain = "rustchain"

    def __init__(self, node: str = DEFAULT_NODE, admin_key: Optional[str] = None,
                 timeout: float = 15.0, verify_tls: bool = True):
        if requests is None:  # pragma: no cover
            raise AnchorError("the 'requests' package is required for RustChainAnchor")
        self.node = node.rstrip("/")
        self.admin_key = admin_key
        self.timeout = timeout
        self.verify_tls = verify_tls

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.admin_key:
            h["X-Admin-Key"] = self.admin_key
        return h

    def anchor(self, commitment: str, **meta: Any) -> Dict[str, Any]:
        body = {"commitment": commitment}
        body.update({k: v for k, v in meta.items() if k in ("video_id", "sender")})
        try:
            r = requests.post(
                f"{self.node}/avap/anchor", json=body,
                headers=self._headers(), timeout=self.timeout, verify=self.verify_tls,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # pragma: no cover - network dependent
            raise AnchorError(f"anchor request failed: {e}") from e
        return {
            "chain": self.chain,
            "tx": data.get("tx", ""),
            "node": self.node,
            "anchored_at": int(data.get("anchored_at", time.time())),
        }

    def verify(self, commitment: str, tx: str = "", **_: Any) -> bool:
        try:
            r = requests.get(
                f"{self.node}/avap/anchor/{commitment}",
                timeout=self.timeout, verify=self.verify_tls,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # pragma: no cover - network dependent
            raise AnchorError(f"anchor verify failed: {e}") from e
        return bool(data.get("anchored"))
