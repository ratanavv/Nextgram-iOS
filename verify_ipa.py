#!/usr/bin/env python3
import plistlib
import sys
import tempfile
import zipfile
from pathlib import Path

def verify_app(app, expected_main):
    def plist(path):
        with open(path, "rb") as f:
            return plistlib.load(f)

    main = plist(app / "Info.plist")
    if main.get("CFBundleIdentifier") != expected_main:
        raise SystemExit(
            f"Main bundle ID mismatch: {main.get('CFBundleIdentifier')!r}"
        )

    names = [
        "Share",
        "NotificationContent",
        "NotificationService",
        "Intents",
        "Widget",
        "BroadcastUpload",
    ]

    plugins = app / "PlugIns"
    if not plugins.is_dir():
        raise SystemExit("PlugIns directory missing")

    for name in names:
        p = plugins / f"{name}.appex"
        if not p.is_dir():
            raise SystemExit(f"Missing extension: {p}")

        info = plist(p / "Info.plist")
        actual = info.get("CFBundleIdentifier")
        wanted = f"{expected_main}.{name}"
        if actual != wanted:
            raise SystemExit(f"{name}: expected {wanted}, got {actual}")

        if (p / "embedded.mobileprovision").exists():
            raise SystemExit(f"{name}: embedded.mobileprovision still present")

    if (app / "embedded.mobileprovision").exists():
        raise SystemExit("Main app still contains embedded.mobileprovision")

    print("IPA verification OK")
    print(f"Main: {expected_main}")
    for n in names:
        print(f"Extension: {expected_main}.{n}")

def main():
    target = Path(sys.argv[1])
    expected_main = sys.argv[2]

    if target.is_file() and target.suffix == ".ipa":
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(target) as z:
                z.extractall(td)
            payload = Path(td, "Payload")
            apps = list(payload.glob("*.app"))
            if len(apps) != 1:
                raise SystemExit(f"Expected one app, found {len(apps)}")
            verify_app(apps[0], expected_main)
    else:
        verify_app(target, expected_main)

if __name__ == "__main__":
    main()
