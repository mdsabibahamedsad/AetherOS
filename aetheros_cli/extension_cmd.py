"""CLI subcommand: ``aetheros extension`` — real extension operations.

Every command calls ExtensionService; output reflects actual results.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _svc():
    from aetheros_extensions.service import ExtensionService
    svc = ExtensionService()
    svc.initialize()
    return svc


def cmd_list(args: argparse.Namespace) -> int:
    svc = _svc()
    recs = svc.list(query=getattr(args, "query", "") or "",
                    ext_type=getattr(args, "type", "") or "")
    if not recs:
        print("No extensions registered.")
        return 0
    for r in recs:
        m = r.get("manifest", {})
        print("%-40s %-12s %-14s %-10s %s" % (
            r["id"], r.get("installed_version", "-") or "-",
            r.get("state", "?"), r.get("trust_level", "?"),
            m.get("description", "")[:60]))
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    info = _svc().info(args.ref)
    if info is None:
        print("Unknown extension: %s" % args.ref)
        return 1
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    svc = _svc()
    p = Path(args.source)
    if p.suffix == ".aetherext":
        res = svc.install(package=p, source="local_package")
    elif p.is_dir():
        res = svc.install(src_dir=p, source="local")
    else:
        print("Source must be an .aetherext file or directory.")
        return 1
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    res = _svc().uninstall(args.ref)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


def cmd_enable(args: argparse.Namespace) -> int:
    res = _svc().enable(args.ref)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


def cmd_disable(args: argparse.Namespace) -> int:
    res = _svc().disable(args.ref)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


def cmd_update(args: argparse.Namespace) -> int:
    svc = _svc()
    if args.ref == "all":
        results = {}
        for r in svc.list():
            p = Path(args.source) if getattr(args, "source", "") else None
            if p is None:
                continue
            kw = {"package": p} if p.suffix == ".aetherext" else {"src_dir": p}
            results[r["id"]] = svc.update(r["id"], **kw)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    p = Path(args.source)
    kw = {"package": p} if p.suffix == ".aetherext" else {"src_dir": p}
    res = svc.update(args.ref, **kw)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok") else 1


def cmd_verify(args: argparse.Namespace) -> int:
    print(json.dumps(_svc().verify(args.ref), indent=2, ensure_ascii=False))
    return 0


def cmd_permissions(args: argparse.Namespace) -> int:
    print(json.dumps(_svc().permissions(args.ref), indent=2, ensure_ascii=False))
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    print(json.dumps(_svc().revoke_all(args.ref), indent=2, ensure_ascii=False))
    return 0


def cmd_quarantine(args: argparse.Namespace) -> int:
    print(json.dumps(_svc().quarantine(args.ref, args.reason or "cli quarantine"),
                     indent=2, ensure_ascii=False))
    return 0


def cmd_doctor(_args: argparse.Namespace) -> int:
    print(json.dumps(_svc().doctor(), indent=2, ensure_ascii=False))
    return 0


def cmd_trust(args: argparse.Namespace) -> int:
    from aetheros_extensions.trust import PublisherRecord, PublisherState
    svc = _svc()
    rec = svc._trust.get(args.publisher)
    if rec is None:
        if not getattr(args, "key", ""):
            print("Unknown publisher. Provide --key <base64-ed25519-pub> to register it.")
            return 1
        rec = PublisherRecord(publisher_id=args.publisher,
                              display_name=args.publisher,
                              public_keys=[args.key],
                              trust=(PublisherState.ORGANIZATION_TRUSTED
                                     if getattr(args, "org", False)
                                     else PublisherState.USER_TRUSTED))
        svc._trust.upsert(rec)
        print("Registered publisher %s (trust=%s)." % (args.publisher, rec.trust))
        return 0
    trust = (PublisherState.ORGANIZATION_TRUSTED if getattr(args, "org", False)
             else PublisherState.USER_TRUSTED)
    svc._trust.set_trust(args.publisher, trust)
    print("Publisher %s trust=%s." % (args.publisher, trust))
    return 0


def cmd_block(args: argparse.Namespace) -> int:
    from aetheros_extensions.trust import PublisherState
    svc = _svc()
    if svc._trust.get(args.publisher) is None:
        print("Unknown publisher: %s" % args.publisher)
        return 1
    svc._trust.set_trust(args.publisher, PublisherState.REVOKED)
    print("Publisher %s REVOKED." % args.publisher)
    return 0


def cmd_package(args: argparse.Namespace) -> int:
    from aetheros_extensions.package import build_package
    try:
        dest = build_package(Path(args.source),
                             Path(args.dest) if getattr(args, "dest", "") else None)
    except ValueError as exc:
        print("Package failed: %s" % exc)
        return 1
    print("Wrote %s" % dest)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from aetheros_extensions.manifest import ExtensionManifest
    try:
        raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("Unreadable manifest: %s" % exc)
        return 1
    try:
        manifest = ExtensionManifest.from_dict(raw)
    except ValueError as exc:
        print("Invalid manifest: %s" % exc)
        return 1
    problems = manifest.validate()
    if problems:
        print("Invalid manifest:")
        for p in problems:
            print("  - %s" % p)
        return 1
    print("Manifest valid: %s %s" % (manifest.id, manifest.version))
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    from aetheros_extensions.package import verify_package
    from aetheros_extensions.trust import sign_package_digest
    rep = verify_package(Path(args.package))
    if not rep.ok:
        print("Package invalid: %s" % rep.reason)
        return 1
    try:
        key = Path(args.key).read_text(encoding="utf-8").strip()
    except OSError as exc:
        print("Key unreadable: %s" % exc)
        return 1
    env = sign_package_digest(rep.package_digest, key,
                              key_id=args.key_id or "k1")
    sig_dir = Path(args.package).parent / "signature-out.json"
    sig_dir.write_text(json.dumps(env, indent=2), encoding="utf-8")
    print("Signature envelope: %s" % sig_dir)
    print("Embed as signature/signature.json before distributing.")
    return 0


def build_parser(subparsers) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        "extension",
        help="Manage extensions (install/verify/permissions/quarantine)",
        description="Universal extension platform: real install, verification, "
        "permissions, updates, rollback and quarantine.",
    )
    parser.set_defaults(func=lambda _a: cmd_list(_a))
    subs = parser.add_subparsers(dest="extension_command", metavar="COMMAND")

    def _ref(p, help_text):
        p.add_argument("ref", help=help_text)

    p = subs.add_parser("list", help="List registered extensions")
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--type", default="")
    p.set_defaults(func=cmd_list)

    for name, fn, h in (("info", cmd_info, "Show extension detail"),
                        ("uninstall", cmd_uninstall, "Uninstall + verified cleanup"),
                        ("enable", cmd_enable, "Enable"),
                        ("disable", cmd_disable, "Disable"),
                        ("verify", cmd_verify, "Re-verify integrity"),
                        ("permissions", cmd_permissions, "Show grants + risk review"),
                        ("revoke", cmd_revoke, "Revoke all runtime grants"),
                        ("doctor", cmd_doctor, "Registry health/problems"),
                        ("block", cmd_block, "Revoke a publisher (untrusted)")):
        sp = subs.add_parser(name, help=h)
        if name != "doctor":
            _ref(sp, "Extension id" if name != "block" else "Publisher id")
        sp.set_defaults(func=fn)

    p = subs.add_parser("trust", help="Trust a publisher (optionally register key)")
    p.add_argument("publisher")
    p.add_argument("--key", default="", help="Base64 Ed25519 public key (register)")
    p.add_argument("--org", action="store_true", help="Organization trust")
    p.set_defaults(func=cmd_trust)

    p = subs.add_parser("install", help="Install from .aetherext or directory")
    p.add_argument("source")
    p.set_defaults(func=cmd_install)

    p = subs.add_parser("update", help="Update one extension (or 'all' with --source dir per id)")
    p.add_argument("ref")
    p.add_argument("--source", default="")
    p.set_defaults(func=cmd_update)

    p = subs.add_parser("quarantine", help="Quarantine an extension")
    _ref(p, "Extension id")
    p.add_argument("--reason", default="cli quarantine")
    p.set_defaults(func=cmd_quarantine)

    p = subs.add_parser("package", help="Build deterministic .aetherext from a directory")
    p.add_argument("source")
    p.add_argument("--dest", default="")
    p.set_defaults(func=cmd_package)

    p = subs.add_parser("validate", help="Validate a manifest.json (fail-closed)")
    p.add_argument("source")
    p.set_defaults(func=cmd_validate)

    p = subs.add_parser("sign", help="Sign a package digest (Ed25519 envelope)")
    p.add_argument("package")
    p.add_argument("key", help="File with base64 private key")
    p.add_argument("--key-id", default="k1")
    p.set_defaults(func=cmd_sign)
    return parser


def dispatch_extension_command(args: argparse.Namespace) -> int:
    command = getattr(args, "extension_command", None)
    handlers = {
        "list": cmd_list, "info": cmd_info, "install": cmd_install,
        "uninstall": cmd_uninstall, "enable": cmd_enable,
        "disable": cmd_disable, "update": cmd_update, "verify": cmd_verify,
        "permissions": cmd_permissions, "revoke": cmd_revoke,
        "quarantine": cmd_quarantine, "doctor": cmd_doctor,
        "package": cmd_package, "validate": cmd_validate, "sign": cmd_sign,
        "trust": cmd_trust, "block": cmd_block,
    }
    if not command:
        return cmd_list(args)
    handler = handlers.get(command)
    if handler is None:
        print("Unknown extension command: %s" % command)
        return 1
    return handler(args)
