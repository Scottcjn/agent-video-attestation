# SPDX-License-Identifier: Apache-2.0
"""
Regression tests: a malformed sender.public_key in an untrusted envelope must
make verification fail cleanly, never raise an unhandled exception out of the
verifier. No ffmpeg needed -- the envelope is built directly.
"""
import unittest

from avap.crypto import AgentKey, address_matches_pubkey
from avap.envelope import build_envelope, verify_envelope


class TestMalformedPubkey(unittest.TestCase):
    def test_address_matches_pubkey_bad_hex_returns_false(self):
        # non-hex and odd-length keys must not raise ValueError
        self.assertFalse(address_matches_pubkey("RTCdeadbeef", "zz"))
        self.assertFalse(address_matches_pubkey("RTCdeadbeef", "abc"))

    def test_verify_envelope_bad_pubkey_does_not_crash(self):
        alice = AgentKey.generate()
        env = build_envelope(alice, {"intent": "x"}, media_fingerprint="deadbeef")
        # Attacker replaces the public key with non-hex garbage.
        env["sender"]["public_key"] = "not-hex!!"
        # Must return a clean failing result, not raise.
        res = verify_envelope(env)
        self.assertFalse(res.ok)
        self.assertFalse(res["checks"]["address_binding"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
