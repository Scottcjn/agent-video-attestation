# AVAP/1.0 — Agent Video Attestation Protocol

Status: Draft standard, v1.0
First published: 2026-06-19
Author: Scott (Elyan Labs)

AVAP lets an AI agent embed a **signed, blockchain-anchored message** to other
agents inside a video file. Any agent can later extract the message and verify,
with no prior contact with the sender: who sent it, that it has not been altered,
that it is bound to this specific video, and that it provably existed at a given
time (via an on-chain commitment).

This document specifies the wire format and verification rules. Two
implementations that follow §2 (canonicalization) interoperate.

---

## 1. Terminology

- **Agent** — an autonomous party with an Ed25519 keypair.
- **Address** — `RTC` + first 40 hex chars of `sha256(public_key_bytes)`. An
  agent's address is also its RustChain wallet address.
- **Envelope** — the JSON object defined in §3, embedded in/alongside a video.
- **Commitment** — `sha256` of the canonical signed core (§4); the value anchored
  on-chain.
- **Media fingerprint** — content hash of the video's codec packets (§5).

## 2. Canonicalization (normative)

All signing and hashing operate on **canonical bytes**:

```
canonical(obj) = utf8( json(obj, sort_keys=true, separators=(",", ":")) )
```

No insignificant whitespace, keys sorted lexicographically, UTF-8, non-ASCII
preserved. Numbers MUST be represented without loss; integers are RECOMMENDED for
timestamps, nonces, and token amounts where exactness matters.

## 3. Envelope schema

```jsonc
{
  "avap": "1.0",                         // protocol version
  "type": "agent.message",               // message type, §7
  "video_id": "alice_clip_001",          // optional platform id
  "media_fingerprint": "<hex sha256>",   // §5, binds envelope to the video
  "sender": {
    "address": "RTC<40 hex>",            // = hash of public_key
    "public_key": "<64 hex>"             // Ed25519 public key
  },
  "recipient": "RTC<40 hex>" | "*",      // "*" = broadcast to any agent
  "payload": { ... } | "<base64>",       // the transferred information
  "payload_encoding": "json" | "base64",
  "issued_at": 1781877179,               // unix seconds
  "nonce": 1781877179000,                // replay guard, unique per sender
  "sig": "<128 hex>",                    // Ed25519 over canonical signed core
  "anchor": {
    "chain": "rustchain",
    "commitment": "<hex sha256>",        // = sha256(canonical signed core)
    "status": "anchored",                // "unanchored" | "anchored"
    "tx": "<chain tx/anchor id>",
    "node": "https://rustchain.org",
    "anchored_at": 1781877185
  }
}
```

### Signed core

The **signed core** is the envelope with the `sig` and `anchor` members removed.
It is the only input to the signature and the commitment. Because `anchor` is
excluded, the on-chain receipt can be added after signing without invalidating
the signature; because `commitment` is `sha256(canonical(signed core))`, the
sender is nonetheless cryptographically bound to exactly what gets anchored.

## 4. Producing an envelope (sender)

1. Compute `media_fingerprint` of the source video (§5).
2. Assemble the signed-core fields (§3 minus `sig`, `anchor`).
3. `core = canonical(signed_core)`.
4. `sig = ed25519_sign(sender_private_key, core)` (hex).
5. `commitment = sha256(core)` (hex).
6. Anchor `commitment` on-chain (§6); attach the receipt as `anchor`.
7. Embed the envelope in the video (§5.2) and/or write a sidecar.

## 5. Media binding

### 5.1 Fingerprint (normative)

The media fingerprint is computed over **codec packet data**, excluding container
metadata, so that adding/removing the envelope does not change it:

```
for each stream: h_s = sha256(packet bytes of that stream)   // e.g. ffmpeg -f streamhash -hash sha256
fingerprint = sha256( "\n".join( sorted("<index>,<type>,sha256=<h_s>") ) )
```

A conforming verifier MUST recompute this the same way. Implementations MAY
define additional fingerprint methods under new `avap` minor versions; verifiers
MUST treat an unknown method as a failed media binding.

### 5.2 Embedding profiles

- **Container profile:** store `base64(canonical(envelope))` as a metadata tag
  named `avap` in the media container (MP4/MOV: write with metadata-tag support).
- **Sidecar profile:** store `canonical(envelope)` as `<video>.avap.json`, and/or
  serve it at a platform endpoint such as `GET /api/video/<id>/avap`.

A file MAY carry both. On extraction, the container profile takes precedence; the
sidecar is the fallback.

## 6. Anchoring (blockchain attestation)

Anchoring publishes only the `commitment` (never the payload), preserving payload
privacy while making existence and time provable.

Reference RustChain interface:

```
POST {node}/avap/anchor
     { "commitment": "<hex>", "video_id": "...", "sender": "RTC..." }
  -> { "tx": "<id>", "anchored_at": <unix> }

GET  {node}/avap/anchor/{commitment}
  -> { "anchored": true, "tx": "<id>", "anchored_at": <unix> }
```

This MAY be served natively by a RustChain node or backed by an Ergo register
anchor (commitment in box register `R4`). Implementations MAY batch many
commitments under one Merkle root and anchor the root; in that case the receipt
SHOULD carry the Merkle path. Offline/dev deployments MAY use a deterministic
local receipt (`tx = "local:" + commitment[:32]`) for testing only.

## 7. Message types

`type` is an extensible string. Defined v1.0 types:

| type               | meaning                                                        |
|--------------------|----------------------------------------------------------------|
| `agent.message`    | generic signed note from one agent to another / to all         |
| `agent.commission` | request for media work; payload SHOULD carry token-denominated terms |
| `agent.handoff`    | transfer of a task/context to another agent                    |
| `agent.reply`      | response to a prior envelope; payload SHOULD reference its commitment |
| `agent.dataref`    | a pointer/manifest to off-video data, integrity-bound by hash  |

Unknown types MUST still be signature/anchor-verifiable; semantics are ignored.

## 8. Verification (verifier) — normative

Given a video, a conforming verifier MUST:

1. Extract the envelope (container, then sidecar).
2. **version** — `avap == "1.0"`.
3. **address_binding** — `sender.address == "RTC"+sha256(public_key)[:40]`.
4. **commitment** — `sha256(canonical(signed_core)) == anchor.commitment`.
5. **signature** — Ed25519 verify `sig` over `canonical(signed_core)` with
   `sender.public_key`.
6. **media_binding** — recompute §5.1 over the video; equals `media_fingerprint`.
7. **anchored** (if required) — `anchor.status == "anchored"` and `tx` non-empty.
8. **onchain** (if requested) — `GET {node}/avap/anchor/{commitment}` confirms.

The envelope is **valid** iff all required checks pass. A verifier SHOULD also
enforce a per-sender `nonce`/`issued_at` policy to reject replays.

## 9. Threat model (informative)

| Attack                              | Defended by                                  |
|-------------------------------------|----------------------------------------------|
| Impersonating a sender              | Ed25519 sig + address-binding (3,5)          |
| Editing the message payload         | sig + commitment over signed core (4,5)      |
| Swapping the video under a message  | media fingerprint binding (5.1, §8.6)        |
| Back-dating a message               | on-chain commitment timestamp (6, §8.8)      |
| Replaying an old message            | nonce/issued_at policy (§8)                   |
| Leaking the transferred info on-chain | only the commitment is anchored (6)        |

Out of scope for v1.0: confidentiality of the payload from a holder of the video
(use an encrypted payload for that — a recipient-encrypted blob is a valid
`payload_encoding`), and revocation (planned for a future minor version).

## 10. Versioning

`avap` is `MAJOR.MINOR`. Verifiers MUST reject a different MAJOR. New MINOR
versions may add message types, fingerprint methods, and anchor receipt forms
without breaking MAJOR-compatible verification of existing envelopes.
