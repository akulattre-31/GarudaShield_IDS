"""One-time security setup. Run ONCE."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from crypto_utils import ensure_key, KEY_PATH


def main():
    print("=" * 55)
    print("Pipeline Security Setup")
    print("=" * 55)

    if os.path.exists(KEY_PATH):
        print(f"\n⚠️  Key already exists: {KEY_PATH}")
        ans = input("Regenerate? [y/N]: ")
        if ans.lower() != 'y':
            print("Keeping existing key.")
            return
        os.remove(KEY_PATH)

    key = ensure_key()
    print(f"\n✅ Key generated: {KEY_PATH}")
    print(f"   Size: {len(key)} bytes")
    print(f"   Permissions: 0600")

    print(f"\n📤 Share with M5 (and M4 for notifications):")
    print(f"   scp {KEY_PATH} <M5_user>@<M5_ip>:~/Drone/keys/")
    print(f"   M5 must run: chmod 600 ~/Drone/keys/pipeline.key")

    print(f"\n⚠️  Add to .gitignore: 'keys/'")


if __name__ == '__main__':
    main()