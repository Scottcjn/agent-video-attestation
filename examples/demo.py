#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
AVAP demo: Agent Alice transfers a task request to Agent Bob *through a video*,
signed and anchored, and Bob verifies it end to end. Runs fully offline.

    python examples/demo.py
"""
import json
import os
import subprocess
import tempfile

from avap import AgentKey, send, receive


def make_demo_video(path):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path],
        check=True,
    )


def main():
    tmp = tempfile.mkdtemp()
    video = os.path.join(tmp, "alice_clip.mp4")
    make_demo_video(video)

    alice = AgentKey.generate()
    bob = AgentKey.generate()
    print(f"Alice: {alice.address}")
    print(f"Bob:   {bob.address}\n")

    # --- Alice embeds a signed, anchored agent-to-agent message into her video ---
    payload = {
        "intent": "commission_response_video",
        "prompt": "Make a 10s sequel to this clip in the same style",
        "budget_rtc": 5,
        "reply_to": alice.address,
    }
    env, out = send(video, alice, payload, recipient=bob.address,
                    msg_type="agent.commission", video_id="alice_clip_001")
    print("Alice attached an AVAP envelope:")
    print(f"  output:     {out}")
    print(f"  commitment: {env['anchor']['commitment']}")
    print(f"  anchor tx:  {env['anchor']['tx']}\n")

    # --- Bob receives the video and verifies everything ---
    result, got, _ = receive(out, verify_onchain=True)
    print("Bob verifies the video:")
    print(json.dumps(result["checks"], indent=2))
    print(f"  verified payload: {got}\n")
    assert result.ok, "verification failed"

    # --- Tamper demo: change the payload, watch verification fail ---
    from avap import extract_envelope, verify_envelope
    tampered = extract_envelope(out)
    tampered["payload"]["budget_rtc"] = 5000
    bad = verify_envelope(tampered)
    print(f"After tampering budget 5 -> 5000, verifies? {bad.ok}  "
          f"(signature check: {bad['checks']['signature']})")

    print("\nAVAP demo OK")


if __name__ == "__main__":
    main()
