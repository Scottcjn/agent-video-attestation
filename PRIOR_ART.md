# AVAP — Defensive Publication / Prior-Art Notice

**Title:** Agent Video Attestation Protocol (AVAP) — signed, blockchain-anchored
agent-to-agent information transfer embedded in video files.

**Author:** Scott (Elyan Labs)
**First public disclosure:** 2026-06-19 (this commit and repository)
**Canonical location:** https://github.com/Scottcjn/agent-video-attestation
**License:** Apache-2.0 (includes an express patent grant)

---

## Purpose of this document

This is a **defensive publication**. It is published to place the methods
described here into the public domain of prior art as of the date above, so that
the techniques remain free for anyone to implement and so that they cannot later
be claimed as the exclusive invention of another party. The authoritative date is
established by the public Git commit history of this repository and any
third-party timestamps thereof (GitHub commit timestamps, blockchain anchors of
this repository's content, and archival snapshots).

The reference implementation in this repository (`avap/`) is a complete, working
embodiment of every claim below; it is not a sketch.

## Field

Provenance, authenticity, and machine-to-machine messaging for AI-agent-generated
video media, combining: digital signatures, content binding, blockchain
commitment anchoring, and economic (token-account) identity.

## Background and relationship to existing art

Existing media-provenance work (e.g. C2PA / Content Credentials) signs media
assertions and binds them to a manifest. Existing blockchain timestamping anchors
arbitrary hashes. AVAP is disclosed as the **specific combination** of the
elements enumerated below, oriented toward **autonomous agent-to-agent transfer**
rather than human-facing authorship claims. Where AVAP overlaps prior work it is
noted; the novelty claimed is the combination and the agent-economic semantics,
not signatures or timestamping in isolation.

## Enumerated disclosure (the claimed combination)

1. **A video file used as a transport for a signed agent-to-agent message.** An
   AI agent embeds a structured payload (an instruction, handoff, data reference,
   commission, or reply) addressed to another agent or broadcast to all agents,
   *inside* a video the agent produced or distributes.

2. **A cryptographic identity that is simultaneously a blockchain account.** The
   sender is identified by an Ed25519 public key whose hash is the agent's
   on-chain wallet address (here: `RTC` + sha256(pubkey)[:40]). The same key both
   signs the message and identifies the economically-accountable agent. This binds
   message authorship to a spendable/earning blockchain identity.

3. **A media fingerprint computed from codec packet data, not container bytes,**
   so that attaching or detaching the attestation does not alter the binding, but
   re-encoding or editing the actual audio/video does — making the attestation
   tamper-evident with respect to the *content*, independent of the *container*.

4. **A commitment hash of the signed message, anchored on a blockchain,** giving
   the message an immutable, independently-verifiable timestamp of existence while
   keeping the payload itself off-chain (privacy-preserving: only the commitment
   is published).

5. **Dual embedding profiles** — (a) in-container metadata (e.g. MP4/MOV tag) and
   (b) detached sidecar manifest — sharing one canonical, deterministically
   serialized envelope so a signature/commitment produced by one implementation
   verifies in another.

6. **A deterministic verification procedure** that an arbitrary third agent can
   run with no prior contact with the sender: recover the public key, confirm the
   address binding, recompute the commitment from the signed core, verify the
   signature, re-fingerprint the media to confirm the content binding, and confirm
   the commitment's on-chain anchoring.

7. **Agent-economic message semantics layered on the above:** typed messages
   (e.g. `agent.commission`, `agent.handoff`, `agent.reply`, `agent.dataref`)
   carrying token-denominated terms (e.g. a budget in the chain's native token),
   enabling autonomous agents to commission, pay for, and verify media work from
   one another using the embedded, signed, anchored envelope as the contract.

8. **Use of the same media item to carry both human-presentable content and the
   machine-only agent channel**, such that the video is simultaneously a normal
   playable clip and a verifiable agent message bus.

## Embodiment

A complete reference implementation accompanies this disclosure:
- `avap/crypto.py` — Ed25519 identity + RustChain address derivation + canonical serialization
- `avap/envelope.py` — signed envelope construction, commitment, verification
- `avap/embed.py` — codec-packet media fingerprint; container + sidecar embedding
- `avap/anchor.py` — blockchain commitment anchoring (RustChain; offline mode)
- `avap/pipeline.py`, `avap/cli.py` — end-to-end send/verify
- `tests/`, `examples/` — passing roundtrip, forgery, payload-tamper, media-tamper tests

## Statement

The author publishes the foregoing freely. Anyone may implement, use, and build
upon it under the Apache-2.0 license accompanying this repository. This notice is
intended to be discoverable prior art against any later, conflicting claim of
exclusive invention over the disclosed combination.
