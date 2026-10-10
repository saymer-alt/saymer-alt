# SPDX-License-Identifier: MIT
"""Audit and optionally fix *only* explicitly approved GitHub portfolio metadata.

Requires: gh CLI authenticated as owner/admin. Safe default: DRY RUN.
Usage: python3 scripts/portfolio_metadata.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import subprocess

OWNER = "saymer-alt"
# Only confirmed discrepancies from the 2026-10-10 metadata audit.
CHANGES = {
    "keenetic-auto-setup": {
        "description": (
            "Mihomo (Clash Meta) on Keenetic + Entware: one-command "
            "installer, VPN routing, watchdog, diagnostics and safe updates"
        ),
    },
    "link-generators": {
        "description": (
            "Local-first Mihomo config & WARP MASQUE link generator; "
            "subscription preview may use a Cloudflare Worker"
        ),
    },
    "keenetic-knowledge-base": {
        "homepage": "https://saymer-alt.github.io/keenetic-knowledge-base/",
    },
    "keenetic-nvr": {
        "topics_add": [
            "keenetic", "entware", "ffmpeg", "rtsp", "nvr",
            "ip-camera", "video-surveillance", "watchdog", "shell",
        ],
    },
    "entware-go": {
        "description": (
            "Entware IPK package builds for Keenetic: "
            "Mihomo, WARPSCOUT and other Go-based tools"
        ),
        "topics_add": [
            "entware", "keenetic", "ipk", "mihomo", "warpscout",
            "go", "github-actions", "cross-compilation",
        ],
    },
}


def gh_api(method: str, endpoint: str, body=None):
    args = ["gh", "api", "--method", method,
            "-H", "Accept: application/vnd.github+json", endpoint]
    if body is not None:
        args += ["--input", "-"]
    p = subprocess.run(args, input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True, check=False)
    if p.returncode:
        raise RuntimeError(f"GitHub request failed ({method} {endpoint}): {p.stderr.strip()}")
    return json.loads(p.stdout) if p.stdout.strip() else {}


def plan(name: str, actual: dict, wanted: dict):
    patch = {}
    for field in ("description", "homepage"):
        if field in wanted and actual.get(field) != wanted[field]:
            patch[field] = wanted[field]
    present = set(actual.get("topics") or [])
    topics = sorted(present | set(wanted.get("topics_add", [])))
    if topics != sorted(present):
        return patch, topics
    return patch, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Perform changes (default: dry run)")
    args = parser.parse_args()
    for name, wanted in CHANGES.items():
        path = f"repos/{OWNER}/{name}"
        current = gh_api("GET", path)
        if current.get("full_name") != f"{OWNER}/{name}" or current.get("private"):
            raise RuntimeError(f"Unexpected repository identity or visibility: {name}")
        patch, topics = plan(name, current, wanted)
        print(f"{name}: {('PATCH ' + str(patch)) if patch else 'description/homepage OK'}"
              f"; {('ADD TOPICS ' + str(topics)) if topics is not None else 'topics OK'}")
        if not args.apply:
            continue
        if patch:
            gh_api("PATCH", path, patch)
        if topics is not None:
            gh_api("PUT", f"{path}/topics", {"names": topics})
        fresh = gh_api("GET", path)
        updated_patch, updated_topics = plan(name, fresh, wanted)
        if updated_patch or updated_topics is not None:
            raise RuntimeError(f"Verification failed after update: {name}")
        print(f"  verified {name}")
    print("Dry-run only; no changes made." if not args.apply else "Applied and verified.")


if __name__ == "__main__":
    main()
