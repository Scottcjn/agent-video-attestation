# SPDX-License-Identifier: Apache-2.0
"""
Regression tests: a malformed sender.public_key in an untrusted envelope must
make verification fail cleanly, never raise an unhandled exception out of the
verifier. No ffmpeg needed -- the envelope is built directly.
"""
import unittest

from avap.crypto import AgentKey, address_matches_pubkey, verify_signature
from avap.envelope import build_envelope, verify_envelope


class TestMalformedPubkey(unittest.TestCase):
    def test_address_matches_pubkey_bad_hex_returns_false(self):
        # non-hex and odd-length keys must not raise ValueError
        self.assertFalse(address_matches_pubkey("RTCdeadbeef", "zz"))
        self.assertFalse(address_matches_pubkey("RTCdeadbeef", "abc"))

    def test_address_matches_pubkey_non_string_returns_false(self):
        # bytes.fromhex() raises TypeError (not ValueError) on a non-str
        # input -- a JSON number, list, dict or None parsed straight out of
        # an untrusted envelope's sender.public_key field.
        for bad in (123, 123.4, ["a", "b"], {"x": 1}, None, True):
            self.assertFalse(address_matches_pubkey("RTCdeadbeef", bad))

    def test_verify_signature_non_string_returns_false(self):
        for bad in (123, ["a"], None):
            self.assertFalse(verify_signature(bad, b"msg", "aa"))

    def test_verify_envelope_bad_pubkey_does_not_crash(self):
        alice = AgentKey.generate()
        env = build_envelope(alice, {"intent": "x"}, media_fingerprint="deadbeef")
        # Attacker replaces the public key with non-hex garbage.
        env["sender"]["public_key"] = "not-hex!!"
        # Must return a clean failing result, not raise.
        res = verify_envelope(env)
        self.assertFalse(res.ok)
        self.assertFalse(res["checks"]["address_binding"])

    def test_verify_envelope_non_string_pubkey_does_not_crash(self):
        alice = AgentKey.generate()
        env = build_envelope(alice, {"intent": "x"}, media_fingerprint="deadbeef")
        # Attacker replaces the public key with a JSON number instead of a
        # hex string -- bytes.fromhex(123) raises TypeError, not ValueError.
        env["sender"]["public_key"] = 123
        res = verify_envelope(env)
        self.assertFalse(res.ok)
        self.assertFalse(res["checks"]["address_binding"])
        self.assertFalse(res["checks"]["signature"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
