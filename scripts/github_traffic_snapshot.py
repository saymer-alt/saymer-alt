# SPDX-License-Identifier: MIT
"""Snapshot GitHub's rolling 14-day traffic for the eight public projects.

Requires an authenticated gh CLI token permitted to read Traffic metrics.
No credentials are stored or printed. Writes a local private JSON snapshot.
Usage: python3 scripts/github_traffic_snapshot.py --output-dir ~/github-traffic-private
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

OWNER = "saymer-alt"
REPOS = (
    "keenetic-auto-setup", "link-generators", "keenetic-knowledge-base",
    "amnezia-mihomo-gateway", "vps-gateway-bootstrap", "mihomo-auto-build",
    "keenetic-nvr", "entware-go",
)


def read_metric(repo: str, metric: str) -> dict:
    if repo not in REPOS or metric not in ("views", "clones"):
        raise ValueError("Unexpected repository or metric")
    path = f"repos/{OWNER}/{repo}/traffic/{metric}"
    response = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                              check=False)
    if response.returncode:
        # The CLI error may reveal endpoint names; never print credentials.
        raise RuntimeError(f"Traffic API failed for {repo}/{metric}; check token permissions")
    try:
        data = json.loads(response.stdout)
    except ValueError as exc:
        raise RuntimeError(f"Invalid traffic API response for {repo}/{metric}") from exc
    if (not isinstance(data, dict) or
            type(data.get("count")) is not int or
            type(data.get("uniques")) is not int or
            not isinstance(data.get(metric), list)):
        raise RuntimeError(f"Malformed traffic API response for {repo}/{metric}")
    for entry in data[metric]:
        if (not isinstance(entry, dict) or
                not isinstance(entry.get("timestamp"), str) or
                type(entry.get("count")) is not int or
                type(entry.get("uniques")) is not int):
            raise RuntimeError(f"Malformed traffic series for {repo}/{metric}")
    return {k: data[k] for k in ("count", "uniques", metric)}


def collect(today: str) -> dict:
    projects = {}
    for repo in REPOS:
        projects[repo] = {"views": read_metric(repo, "views"),
                          "clones": read_metric(repo, "clones")}
    return {
        "schema": 1,
        "owner": OWNER,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "day_utc": today,
        "window": "GitHub Traffic API rolling approximately 14 days",
        "repos": projects,
        "note": "Traffic unique counts are not additive across snapshots.",
    }


def save(snapshot: dict, destination: Path) -> Path:
    # A local directory outside any public repository is strongly recommended.
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    if destination.is_symlink():
        raise RuntimeError("Refusing symlinked output directory")
    filename = destination / f"traffic-{snapshot['day_utc']}.json"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(filename, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(snapshot, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return filename


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Private directory for snapshots; use a location outside public git")
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date().isoformat()
    snapshot = collect(today)
    filename = save(snapshot, args.output_dir.expanduser())
    print(f"Saved {len(REPOS)} public-repository traffic snapshots to {filename}")
    print("The API only exposes a rolling window; collect at least once every 14 days.")


if __name__ == "__main__":
    main()
