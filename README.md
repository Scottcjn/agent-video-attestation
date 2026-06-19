# AVAP — Agent Video Attestation Protocol

**Agent-to-agent information transfer, carried inside video files, signed by the
sending agent and anchored on the RustChain blockchain.**

An AI agent can embed a signed message — an instruction, a handoff, a paid
commission, a reply — *inside a video it produces*. Any other agent can extract
that message and verify, with no prior contact with the sender:

- **who** sent it (Ed25519 signature; the sender's key *is* its blockchain wallet address)
- **that it wasn't altered** (signature over a canonical commitment)
- **that it belongs to this exact video** (a media fingerprint of the codec data, not the container)
- **that it provably existed at a point in time** (the commitment is anchored on-chain)

The same file is both a normal, playable video and a verifiable agent message bus.

> 📄 Protocol spec: [`SPEC.md`](SPEC.md) · Prior-art / defensive publication: [`PRIOR_ART.md`](PRIOR_ART.md)
> First published 2026-06-19 · Apache-2.0

---

## Why

Autonomous agents increasingly generate and exchange media. They need a way to
say *"I made this, here is what I'm asking you to do with it, and here are the
terms"* — verifiably, without a trusted intermediary, and in a way that survives
being passed around. AVAP makes the video itself carry that signed, timestamped,
economically-accountable channel. It builds directly on the
[RustChain](https://github.com/Scottcjn/Rustchain) agent economy: an agent's
signing key is its RTC wallet, so a message author is the same accountable party
that earns and spends tokens.

It pairs naturally with high-volume video generation (e.g. cloud video-gen APIs):
agents commission media from each other with token-denominated terms embedded in
the request video, and verify the result the same way.

## Install

```bash
pip install -e .          # needs Python 3.8+, PyNaCl; ffmpeg/ffprobe on PATH
pip install -e ".[node]"  # add 'requests' to anchor against a live RustChain node
```

## 60-second demo (fully offline)

```bash
python examples/demo.py
```

Alice embeds a signed `agent.commission` into a video and anchors its commitment;
Bob extracts it and all checks pass; then a tampered copy is rejected.

## CLI

```bash
# make an agent identity (its address is a RustChain wallet address)
avap keygen --out alice.json

# Alice attaches a signed, anchored message to a video
avap send clip.mp4 --key alice.json \
    --type agent.commission \
    --payload '{"intent":"render_sequel","budget_rtc":5}' \
    --recipient RTC<bob...> --out clip.avap.mp4

# anyone verifies it (offline). add --node + --onchain to confirm on a live node
avap verify clip.avap.mp4 --onchain

# dump the embedded envelope
avap inspect clip.avap.mp4
```

`send`/`verify` use an **offline local anchor** by default so everything runs with
no server. Point them at a RustChain node with `--node https://rustchain.org`
(and `--admin-key` if your node requires it).

## Library

```python
from avap import AgentKey, send, receive

alice = AgentKey.generate()                      # alice.address is an RTC wallet
env, out = send("clip.mp4", alice,
                {"intent": "render_sequel", "budget_rtc": 5},
                recipient="RTC...", msg_type="agent.commission")

result, payload, envelope = receive(out, verify_onchain=True)
assert result.ok            # version, address, commitment, signature, media, onchain
print(payload)              # the verified agent-to-agent message
```

To anchor on a live chain:

```python
from avap import RustChainAnchor
env, out = send("clip.mp4", alice, {...},
                anchor=RustChainAnchor("https://rustchain.org", admin_key="..."))
```

## How it works (one paragraph)

The sender builds an envelope (sender identity, recipient, payload, the video's
media fingerprint, time, nonce), serializes its **signed core** canonically, signs
it with Ed25519, and hashes it to a **commitment**. The commitment — and only the
commitment — is anchored on RustChain, so the payload stays private while its
existence and time become provable. The envelope is embedded in the MP4 metadata
and/or a sidecar `.avap.json`. A verifier recomputes the commitment, checks the
signature and the address binding, re-fingerprints the video to confirm the
message is bound to *this* content, and optionally confirms the on-chain anchor.
See [`SPEC.md`](SPEC.md) for the normative details.

## What's verified

| Check            | Catches                                            |
|------------------|----------------------------------------------------|
| `signature`      | forged sender / altered message                    |
| `address_binding`| public key that doesn't match the claimed address  |
| `commitment`     | mismatch between signed content and anchored hash  |
| `media_binding`  | the message moved onto a different/edited video    |
| `onchain`        | a commitment that was never actually anchored      |

## Status

v1.0 reference implementation. Tests cover roundtrip, signature forgery, payload
tampering, and media tampering:

```bash
python -m unittest discover -s tests -v
```

## Relationship to other work

AVAP is complementary to media-provenance standards like C2PA / Content
Credentials: where those center human-facing authorship manifests, AVAP centers
**autonomous agent-to-agent messaging** with **blockchain commitment anchoring**
and **token-account identity**. See [`PRIOR_ART.md`](PRIOR_ART.md) for the
specific combination disclosed here.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
