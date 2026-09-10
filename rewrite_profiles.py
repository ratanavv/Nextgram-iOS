#!/usr/bin/env python3
import plistlib
import subprocess
import sys
from pathlib import Path

src, dst, bundle_id, team_id, plist_tmp, signing_pem = map(Path, sys.argv[1:])

profiles = {
    "Telegram.mobileprovision": "Telegram.mobileprovision",
    "Share.mobileprovision": "Share.mobileprovision",
    "NotificationContent.mobileprovision": "NotificationContent.mobileprovision",
    "NotificationService.mobileprovision": "NotificationService.mobileprovision",
    "Intents.mobileprovision": "Intents.mobileprovision",
    "Widget.mobileprovision": "Widget.mobileprovision",
    "BroadcastUpload.mobileprovision": "BroadcastUpload.mobileprovision",
}

old_bundle = "ph.telegra.Telegraph"
dst.mkdir(parents=True, exist_ok=True)

def extract(path):
    p = subprocess.run(
        ["openssl", "smime", "-inform", "DER", "-verify", "-noverify",
         "-in", str(path), "-out", str(plist_tmp)],
        check=True
    )
    with plist_tmp.open("rb") as f:
        return plistlib.load(f)

def replace(v):
    if isinstance(v, str):
        return v.replace(old_bundle, bundle_id)
    if isinstance(v, list):
        return [replace(x) for x in v]
    if isinstance(v, dict):
        return {k: replace(x) for k, x in v.items()}
    return v

for name, out_name in profiles.items():
    source = src / name
    if not source.exists():
        raise SystemExit(f"Missing source fake profile: {source}")

    profile = extract(source)
    profile = replace(profile)
    profile.pop("DER-Encoded-Profile", None)

    ent = profile.get("Entitlements", {})
    expected = f"{team_id}.{bundle_id}"

    # Validate the fields that matter to Bazel/TrollStore.
    app_id = ent.get("application-identifier")
    if app_id != expected and not app_id.startswith(expected + "."):
        raise SystemExit(
            f"{name}: unexpected application-identifier after rewrite: {app_id!r}"
        )

    team = ent.get("com.apple.developer.team-identifier")
    if team != team_id:
        raise SystemExit(f"{name}: unexpected team identifier: {team!r}")

    with plist_tmp.open("wb") as f:
        plistlib.dump(profile, f, fmt=plistlib.FMT_BINARY)

    out = dst / out_name
    subprocess.run(
        [
            "openssl", "smime", "-sign", "-binary", "-nodetach",
            "-outform", "DER",
            "-in", str(plist_tmp),
            "-signer", str(signing_pem),
            "-inkey", str(signing_pem),
            "-out", str(out),
        ],
        check=True,
    )

    print(f"generated {out}")

plist_tmp.unlink(missing_ok=True)
