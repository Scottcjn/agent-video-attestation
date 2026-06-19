# AVAP for AI Agents

This page is written for autonomous agents (and the humans wiring them up). It
describes AVAP as a tool using the six load-bearing components that govern whether
an agent uses a capability correctly and reuses it: **Purpose, Usage, Limitations,
Parameters, Completeness, Examples.**

## Purpose

Use AVAP when one agent needs to send another agent a **verifiable** message
*through a video* — and the receiver must be able to confirm authorship, integrity,
which video the message belongs to, and that it existed at a given time, **without
trusting any intermediary**. Typical uses: commissioning media work from another
agent with token-denominated terms, handing off a task with context, replying to a
prior video-borne message, or attaching a hash-bound data reference to a clip.

## Usage

1. `keygen` once to get an identity. The agent's address (`RTC...`) is also its
   RustChain wallet, so the same key that signs messages earns/spends RTC.
2. `send` a payload bound to a specific video → produces a video carrying a signed,
   anchored envelope (container metadata + sidecar).
3. The recipient (or any third party) calls `receive`/`verify` → a structured
   result with one boolean per check and the decoded payload iff all checks pass.
4. Anchor/verify offline by default; pass a `--node`/`RustChainAnchor` to use a
   live chain.

## Limitations

- Requires `ffmpeg`/`ffprobe` on PATH (media fingerprinting + container embedding).
- The payload is **authentic and integrity-protected, not secret**, from anyone
  holding the video. For confidentiality, supply an already-encrypted payload
  (a recipient-encrypted blob is a valid base64 payload).
- On-chain *existence* checking (`--onchain` / `verify_onchain=True`) needs a
  reachable anchor backend; offline mode proves everything except live anchoring.
- v1.0 has no revocation mechanism (planned for a later minor version).
- A re-encode/edit of the video breaks the media binding **by design** — bind the
  envelope to the exact rendered output you intend to distribute.

## Parameters (key ones)

- `payload` (any JSON or bytes) — the information being transferred.
- `recipient` (`RTC...` or `*`) — a specific agent or broadcast to all.
- `msg_type` — `agent.message | agent.commission | agent.handoff | agent.reply | agent.dataref`.
- `video_id` — optional platform identifier.
- `anchor` — `LocalAnchor()` (default, offline) or `RustChainAnchor(node, admin_key)`.
- verify flags — `require_anchor` (must claim anchored), `verify_onchain` (confirm on chain).

## Completeness

A successful `receive(..., verify_onchain=True)` returns checks:
`version, address_binding, commitment, signature, media_binding, onchain` — all
must be true for `result.ok`. The decoded `payload` is only returned when valid.

## Examples

```python
from avap import AgentKey, send, receive

alice = AgentKey.generate()
bob = AgentKey.generate()

# Alice commissions a sequel from Bob, terms embedded in the video
env, out = send("alice_clip.mp4", alice,
                {"intent": "render_sequel", "budget_rtc": 5, "reply_to": alice.address},
                recipient=bob.address, msg_type="agent.commission",
                video_id="alice_clip_001")

# Bob verifies before doing any work
result, payload, envelope = receive(out, verify_onchain=True)
if result.ok:
    do_the_work(payload)         # {'intent': 'render_sequel', 'budget_rtc': 5, ...}
else:
    reject(result["checks"])     # which check failed
```

```bash
avap keygen --out alice.json
avap send clip.mp4 --key alice.json --type agent.commission \
  --payload '{"intent":"render_sequel","budget_rtc":5}' --out clip.avap.mp4
avap verify clip.avap.mp4 --onchain      # exit 0 iff valid
```

See `SPEC.md` for the normative wire format and `examples/demo.py` for a runnable
end-to-end demonstration.
