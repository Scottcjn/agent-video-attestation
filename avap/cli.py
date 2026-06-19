"""
AVAP command-line interface.

    avap keygen [--out key.json]
    avap fingerprint VIDEO
    avap send VIDEO --key key.json --payload '{"to":"agentB","ask":"render a sequel"}' \
        [--recipient RTC...] [--type agent.message] [--out out.mp4] \
        [--node https://rustchain.org] [--admin-key KEY]
    avap verify VIDEO [--node ...] [--onchain] [--require-anchor]
    avap inspect VIDEO            # dump the embedded envelope as JSON

Without --node, anchoring/verification uses the offline LocalAnchor so the whole
flow is runnable with no server.
"""
from __future__ import annotations

import argparse
import json
import sys

from .anchor import LocalAnchor, RustChainAnchor
from .crypto import AgentKey
from .embed import extract_envelope, media_fingerprint
from .pipeline import receive, send


def _anchor_from_args(args):
    if getattr(args, "node", None):
        return RustChainAnchor(node=args.node, admin_key=getattr(args, "admin_key", None))
    return LocalAnchor()


def _load_key(path: str) -> AgentKey:
    with open(path) as f:
        return AgentKey.from_private_hex(json.load(f)["private_key"])


def cmd_keygen(args):
    k = AgentKey.generate()
    blob = {"private_key": k.private_hex, "public_key": k.public_hex, "address": k.address}
    if args.out:
        with open(args.out, "w") as f:
            json.dump(blob, f, indent=2)
        print(f"wrote {args.out}  address={k.address}")
    else:
        print(json.dumps(blob, indent=2))


def cmd_fingerprint(args):
    print(media_fingerprint(args.video))


def cmd_send(args):
    key = _load_key(args.key)
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError:
        payload = args.payload  # treat as plain string
    env, out = send(
        args.video, key, payload,
        recipient=args.recipient, msg_type=args.type, video_id=args.video_id,
        anchor=_anchor_from_args(args), out_path=args.out,
        container=not args.no_container, sidecar=not args.no_sidecar,
    )
    print(json.dumps({
        "output": out,
        "commitment": env["anchor"]["commitment"],
        "tx": env["anchor"]["tx"],
        "sender": env["sender"]["address"],
    }, indent=2))


def cmd_verify(args):
    result, payload, env = receive(
        args.video, anchor=_anchor_from_args(args),
        require_anchor=args.require_anchor, verify_onchain=args.onchain,
    )
    if env is None:
        print("NO ENVELOPE FOUND", file=sys.stderr)
        sys.exit(2)
    out = {"ok": result.ok, "checks": result["checks"],
           "commitment": result["commitment"],
           "sender": env["sender"]["address"], "type": env["type"]}
    if result.ok:
        out["payload"] = payload
    print(json.dumps(out, indent=2))
    sys.exit(0 if result.ok else 1)


def cmd_inspect(args):
    env = extract_envelope(args.video)
    if env is None:
        print("NO ENVELOPE FOUND", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(env, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="avap", description="Agent Video Attestation Protocol")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("keygen", help="generate an agent identity")
    g.add_argument("--out")
    g.set_defaults(func=cmd_keygen)

    f = sub.add_parser("fingerprint", help="print a video's media fingerprint")
    f.add_argument("video")
    f.set_defaults(func=cmd_fingerprint)

    s = sub.add_parser("send", help="attach a signed, anchored envelope to a video")
    s.add_argument("video")
    s.add_argument("--key", required=True)
    s.add_argument("--payload", required=True)
    s.add_argument("--recipient", default="*")
    s.add_argument("--type", default="agent.message")
    s.add_argument("--video-id", default="")
    s.add_argument("--out")
    s.add_argument("--node")
    s.add_argument("--admin-key")
    s.add_argument("--no-container", action="store_true")
    s.add_argument("--no-sidecar", action="store_true")
    s.set_defaults(func=cmd_send)

    v = sub.add_parser("verify", help="verify a video's embedded envelope")
    v.add_argument("video")
    v.add_argument("--node")
    v.add_argument("--admin-key")
    v.add_argument("--onchain", action="store_true")
    v.add_argument("--require-anchor", action="store_true")
    v.set_defaults(func=cmd_verify)

    i = sub.add_parser("inspect", help="dump the embedded envelope")
    i.add_argument("video")
    i.set_defaults(func=cmd_inspect)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
