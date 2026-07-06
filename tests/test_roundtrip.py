# SPDX-License-Identifier: Apache-2.0
"""
AVAP end-to-end tests. Generates a tiny real MP4 with ffmpeg so no assets are
needed. Covers: happy-path roundtrip, signature forgery, payload tampering, and
media tampering (re-encode) detection.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

from avap import (
    AgentKey,
    extract_envelope,
    media_fingerprint,
    receive,
    send,
    verify_envelope,
)

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


def make_video(path, seconds=1, seed="testsrc"):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", f"{seed}=size=128x128:rate=10:duration={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
        check=True,
    )


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg required")
class TestRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.video = os.path.join(self.tmp, "in.mp4")
        make_video(self.video)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_happy_path(self):
        alice = AgentKey.generate()
        payload = {"to": "bob", "intent": "render_sequel", "budget_rtc": 5}
        env, out = send(self.video, alice, payload, recipient="bob", video_id="vid_001")
        result, got, parsed = receive(out, verify_onchain=True)
        self.assertTrue(result.ok, result.get("checks"))
        self.assertEqual(got, payload)
        self.assertEqual(parsed["sender"]["address"], alice.address)
        self.assertTrue(all(result["checks"].values()))

    def test_fingerprint_stable_across_embed(self):
        """Embedding the envelope must NOT change the media fingerprint."""
        alice = AgentKey.generate()
        before = media_fingerprint(self.video)
        _, out = send(self.video, alice, {"x": 1})
        after = media_fingerprint(out)
        self.assertEqual(before, after)

    def test_signature_forgery_detected(self):
        alice = AgentKey.generate()
        mallory = AgentKey.generate()
        env, out = send(self.video, alice, {"hello": "world"})
        tampered = extract_envelope(out)
        # Mallory swaps in her own key but cannot forge Alice's signature
        tampered["sender"]["public_key"] = mallory.public_hex
        tampered["sender"]["address"] = mallory.address
        res = verify_envelope(tampered)
        self.assertFalse(res.ok)
        self.assertFalse(res["checks"]["signature"])

    def test_payload_tamper_detected(self):
        alice = AgentKey.generate()
        env, out = send(self.video, alice, {"budget_rtc": 5})
        tampered = extract_envelope(out)
        tampered["payload"] = {"budget_rtc": 5000}  # raise the budget
        res = verify_envelope(tampered)
        self.assertFalse(res.ok)
        # commitment recompute and signature both break
        self.assertFalse(res["checks"]["signature"])

    def test_media_tamper_detected(self):
        alice = AgentKey.generate()
        env, out = send(self.video, alice, {"msg": "real"}, container=False)
        # Attacker re-encodes the video (different frames) but keeps the sidecar
        forged = os.path.join(self.tmp, "forged.mp4")
        make_video(forged, seconds=2)  # different content -> different fingerprint
        shutil.copy(out + ".avap.json", forged + ".avap.json")
        res, payload, _ = receive(forged)
        self.assertFalse(res.ok)
        self.assertFalse(res["checks"]["media_binding"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
