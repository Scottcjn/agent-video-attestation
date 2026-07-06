# SPDX-License-Identifier: Apache-2.0
"""
AVAP cryptographic primitives.

Deliberately identical in scheme to RustChain's wallet crypto so that an AVAP
sender identity *is* a RustChain identity:

    address = "RTC" + sha256(ed25519_public_key)[:40]

Canonical JSON (sorted keys, no whitespace, UTF-8) is the single source of truth
for everything that gets signed or hashed. If two implementations canonicalize
the same object the same way, their signatures and commitments interoperate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

ADDRESS_PREFIX = "RTC"


def canonical(obj: Any) -> bytes:
    """Deterministic byte serialization used for all signing and hashing."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def address_from_public_key(public_key_hex: str) -> str:
    """RustChain-compatible address derivation."""
    pubkey_hash = hashlib.sha256(bytes.fromhex(public_key_hex)).hexdigest()[:40]
    return f"{ADDRESS_PREFIX}{pubkey_hash}"


class AgentKey:
    """An agent's signing identity (Ed25519)."""

    def __init__(self, signing_key: SigningKey):
        self._sk = signing_key
        self._vk = signing_key.verify_key

    @classmethod
    def generate(cls) -> "AgentKey":
        return cls(SigningKey.generate())

    @classmethod
    def from_private_hex(cls, private_hex: str) -> "AgentKey":
        return cls(SigningKey(bytes.fromhex(private_hex)))

    @property
    def private_hex(self) -> str:
        return self._sk.encode().hex()

    @property
    def public_hex(self) -> str:
        return self._vk.encode().hex()

    @property
    def address(self) -> str:
        return address_from_public_key(self.public_hex)

    def sign(self, message: bytes) -> str:
        return self._sk.sign(message).signature.hex()


def verify_signature(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    try:
        VerifyKey(bytes.fromhex(public_key_hex)).verify(
            message, bytes.fromhex(signature_hex)
        )
        return True
    except (BadSignatureError, ValueError):
        return False


def address_matches_pubkey(address: str, public_key_hex: str) -> bool:
    return address == address_from_public_key(public_key_hex)
