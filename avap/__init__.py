"""
AVAP - Agent Video Attestation Protocol.

Agent-to-agent information transfer carried inside video files, with each transfer
cryptographically signed by the sending agent and its commitment anchored on the
RustChain blockchain for an immutable, verifiable timestamp.

Public API:
    AgentKey                     - an agent's Ed25519 identity (RustChain address)
    build_envelope / verify_envelope / attach_anchor / decode_payload
    media_fingerprint / embed_container / extract_envelope / write_sidecar
    LocalAnchor / RustChainAnchor
    send / receive               - high level one-call pipeline (see pipeline.py)
"""
from .crypto import AgentKey, address_from_public_key, verify_signature
from .envelope import (
    AVAP_VERSION,
    BROADCAST,
    attach_anchor,
    build_envelope,
    commitment_of,
    decode_payload,
    verify_envelope,
)
from .embed import (
    embed_container,
    extract_container,
    extract_envelope,
    media_fingerprint,
    read_sidecar,
    write_sidecar,
)
from .anchor import AnchorError, LocalAnchor, RustChainAnchor
from .pipeline import receive, send

__version__ = AVAP_VERSION

__all__ = [
    "AgentKey", "address_from_public_key", "verify_signature",
    "AVAP_VERSION", "BROADCAST", "build_envelope", "verify_envelope",
    "attach_anchor", "commitment_of", "decode_payload",
    "media_fingerprint", "embed_container", "extract_container",
    "extract_envelope", "read_sidecar", "write_sidecar",
    "AnchorError", "LocalAnchor", "RustChainAnchor",
    "send", "receive",
]
