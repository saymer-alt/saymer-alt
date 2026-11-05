#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Cheap weekly upstream watcher for saymer-alt projects (issue #16).

One workflow, read-only public GitHub API plus the single central issue of
THIS repository as durable state.  Machine detector only: it reports exact
ref/SHA deltas with links; the human/agent review (useful? implemented?
license?) stays with the trackers and Proof Before Build.

Design contract (issue #16):
- first run seeds the baseline silently; no notification avalanche;
- a change is reported once per observed SHA; reruns never duplicate;
- API/rate-limit/network failures record UNKNOWN and never advance the
  stored cursor ("last_seen");
- default-branch renames, deleted/recreated tags and force-pushes produce
  either an UNKNOWN note or a single honest delta — never a false event;
- untrusted upstream text is never fetched (no README/commit messages);
  every emitted string is validated or replaced by a placeholder;
- request budget is capped; over-budget targets become UNKNOWN, not silent.

Usage:
  python3 scripts/upstream_watch.py --dry-run            # report only
  python3 scripts/upstream_watch.py --state-file st.json # local file state
  python3 scripts/upstream_watch.py --issue 17           # Actions mode
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

REPO = "saymer-alt/saymer-alt"
STATE_BEGIN = "<!-- UPSTREAM-WATCH:STATE:V1 BEGIN (machine block; edit only the JSON) -->"
STATE_END = "<!-- UPSTREAM-WATCH:STATE:V1 END -->"
STATE_VERSION = 1
MAX_REQUESTS = 60          # hard cap incl. issue reads/writes
MAX_DIGEST_ITEMS = 10      # digest stays short; overflow is counted, not hidden silently
MAX_BODY_BYTES = 96 * 1024 # refuse to write an oversized issue body
TIMEOUT = 20               # seconds per HTTP request
DIGEST_MARKER = "<!-- upstream-watch-digest -->"

SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$")

# Verified live 2026-11-05 (default branches, fork parents, baselines):
# trackers saymer-alt#12, wdtt-suite#51, KAS#236, link-generators#320.
TARGETS = [
    {"id": "pstack", "repo": "cursor/plugins", "kind": "file_blob",
     "branch": "main", "path": "pstack/plugin.json",
     "note": "tracker: saymer-alt/saymer-alt#12"},
    {"id": "notawdtt", "repo": "pythoneer-dev-q/NotAWDTT-panel",
     "kind": "branch_sha", "branch": "main",
     "note": "tracker: wdtt-suite#51 (WATCH ONLY)"},
    {"id": "tachyon", "repo": "Dushnilin/tachyon", "kind": "latest_release",
     "branch": "main",
     "note": "trackers: KAS#236, link-generators#320 (GPL-2.0 upstream)"},
    {"id": "openflux-upstream", "repo": "p1neappleXpress/OpenFlux",
     "kind": "branch_sha", "branch": "main",
     "note": "our fork: saymer-alt/OpenFlux"},
    {"id": "csqtt-upstream", "repo": "amurcanov/csqtt",
     "kind": "branch_sha", "branch": "main",
     "note": "our fork: saymer-alt/csqtt"},
    {"id": "swinter-android", "repo": "somewhat-industries/swinter-android",
     "kind": "branch_sha", "branch": "main"},
    {"id": "swinter-ios", "repo": "somewhat-industries/swinter-ios",
     "kind": "branch_sha", "branch": "main"},
    {"id": "maxcalls", "repo": "icyfalc0n/maxcalls",
     "kind": "branch_sha", "branch": "master"},
    {"id": "whitelist-bypass", "repo": "kulikov0/whitelist-bypass",
     "kind": "branch_sha", "branch": "main"},
    {"id": "whitetransport", "repo": "meanwebuser/whitetransport-public",
     "kind": "branch_sha", "branch": "main"},
]


class Budget:
    """Counts every outbound request; exhausted budget is a visible failure."""

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.used = 0

    def take(self) -> None:
        if self.used >= self.cap:
            raise BudgetExhausted(f"request budget {self.cap} exhausted")
        self.used += 1

    @property
    def left(self) -> int:
        return self.cap - self.used


class BudgetExhausted(Exception):
    pass


class ApiError(Exception):
    def __init__(self, kind: str, status: int = 0, detail: str = "") -> None:
        super().__init__(f"{kind} (status={status}) {detail}".strip())
        self.kind = kind
        self.status = status


def make_fetcher(token: str | None, budget: Budget):
    """Returns fetch_json(url) -> decoded JSON, with retries=0 and a hard cap."""

    def fetch_json(url: str):
        budget.take()
        request = urllib.request.Request(url, method="GET")
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "saymer-alt-upstream-watch/1.0")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining is not None and remaining.isdigit() and int(remaining) == 0:
                    raise ApiError("rate_limit_exhausted", response.status, url)
                raw = response.read(2 * 1024 * 1024)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise ApiError("rate_limit_or_forbidden", exc.code, url) from exc
            if exc.code == 404:
                raise ApiError("not_found", exc.code, url) from exc
            raise ApiError("http_error", exc.code, url) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ApiError("network_error", 0, str(exc)) from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ApiError("bad_json", 0, url) from exc

    return fetch_json


def safe_token(value, fallback: str = "<unvalidated>") -> str:
    """Upstream-controlled strings are emitted only if they match a strict
    pattern; anything else becomes a fixed placeholder (never dropped into
    markdown raw)."""
    if isinstance(value, str) and SAFE_TOKEN_RE.match(value):
        return value
    return fallback


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def observe(target: dict, fetch_json) -> dict:
    """One read-only observation of one target. Never raises: failures become
    {'state': 'UNKNOWN', ...} so the caller's cursor logic stays simple."""
    repo, kind, branch = target["repo"], target["kind"], target.get("branch", "")
    try:
        meta = fetch_json(f"https://api.github.com/repos/{repo}")
        default_branch = safe_token(meta.get("default_branch"))
        if branch and default_branch != branch:
            return {"state": "UNKNOWN",
                    "note": f"default branch is now {default_branch!r}, expected {branch!r}"}
        if kind == "branch_sha":
            head = fetch_json(f"https://api.github.com/repos/{repo}/commits/{branch}")
            sha = head.get("sha")
            if not isinstance(sha, str) or not SHA_RE.match(sha):
                return {"state": "UNKNOWN", "note": "unparseable head sha"}
            return {"state": "SEEN", "value": sha, "label": sha[:12],
                    "kind": "commit", "default_branch": default_branch}
        if kind == "latest_release":
            release = fetch_json(f"https://api.github.com/repos/{repo}/releases/latest")
            tag = release.get("tag_name")
            if not isinstance(tag, str) or not SAFE_TOKEN_RE.match(tag):
                return {"state": "UNKNOWN", "note": "unparseable release tag"}
            target_sha = release.get("target_commitish")
            sha = target_sha if isinstance(target_sha, str) and SHA_RE.match(target_sha) else ""
            # Identity is tag AND commit: a re-pointed release must register
            # as a change even when a new release lands on the same commit
            # SHA as the previous one.
            value = f"tag:{tag}@{sha}" if sha else f"tag:{tag}"
            return {"state": "SEEN", "value": value, "label": tag,
                    "kind": "release", "default_branch": default_branch}
        if kind == "file_blob":
            blob = fetch_json(
                f"https://api.github.com/repos/{repo}/contents/{target['path']}?ref={branch}")
            sha = blob.get("sha")
            if not isinstance(sha, str) or not SHA_RE.match(sha):
                return {"state": "UNKNOWN", "note": "unparseable blob sha"}
            label = ""
            content = blob.get("content")
            if isinstance(content, str) and len(content) < 200_000:
                try:
                    data = json.loads(base64.b64decode(content).decode("utf-8"))
                    version = data.get("version") if isinstance(data, dict) else None
                    label = safe_token(version)
                except (ValueError, UnicodeDecodeError):
                    label = ""
            return {"state": "SEEN", "value": f"blob:{sha}", "label": label,
                    "kind": "blob", "default_branch": default_branch}
        return {"state": "UNKNOWN", "note": f"unknown kind {kind!r}"}
    except ApiError as exc:
        note = {404: "not found (deleted, renamed or private?)",
                0: ""}.get(exc.status, "")
        return {"state": "UNKNOWN", "note": (note + " " + exc.kind).strip()}
    except BudgetExhausted:
        return {"state": "UNKNOWN", "note": "request budget exhausted"}


def fresh_state() -> dict:
    return {"version": STATE_VERSION, "updated": now_iso(), "targets": {}}


def parse_state(body: str) -> dict | None:
    """Extracts the machine block; None means 'no valid state' -> baseline."""
    begin, end = body.find(STATE_BEGIN), body.find(STATE_END)
    if begin == -1 or end == -1 or end < begin:
        return None
    chunk = body[begin + len(STATE_BEGIN):end]
    match = re.search(r"```json\s*(\{.*\})\s*```", chunk, re.DOTALL)
    if not match:
        return None
    try:
        state = json.loads(match.group(1))
    except ValueError:
        return None
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION \
            or not isinstance(state.get("targets"), dict):
        return None
    return state


def render_state(state: dict) -> str:
    state["updated"] = now_iso()
    blob = json.dumps(state, ensure_ascii=True, sort_keys=True, indent=1)
    return f"{STATE_BEGIN}\n```json\n{blob}\n```\n{STATE_END}"


def compare_link(target: dict, old: str, new: str) -> str:
    def strip(value: str) -> str:
        # "blob:<sha>" and "tag:<name>@<sha>" carry a commit SHA for compare.
        if value.startswith("blob:"):
            return value[5:]
        if value.startswith("tag:"):
            tail = value[4:].rpartition("@")[2]
            return tail
        return value
    a, b = strip(old), strip(new)
    if SHA_RE.match(a) and SHA_RE.match(b) and a != b:
        return f"https://github.com/{target['repo']}/compare/{a[:12]}...{b[:12]}"
    if old.startswith("tag:") or new.startswith("tag:"):
        return f"https://github.com/{target['repo']}/releases"
    return f"https://github.com/{target['repo']}/commits"


def classify(observed: dict, previous: dict | None) -> tuple[str, bool]:
    """Returns (state, report?). report=True only for genuinely new deltas.
    A target without a stored last_seen (first run, or the run after an API
    failure that could not advance the cursor) is a baseline observation:
    recorded silently as REVIEWED, never reported."""
    if observed["state"] == "UNKNOWN":
        return "UNKNOWN", False
    value = observed["value"]
    if previous is None or not previous.get("last_seen"):
        return "REVIEWED", False
    last_seen = previous.get("last_seen")
    reported = previous.get("reported")
    if value == last_seen or value == reported:
        # A still-unreviewed delta stays pending on every unchanged rerun; a
        # reviewed/baselined target simply reports UNCHANGED.
        return ("CHANGED_PENDING_REVIEW"
                if previous.get("state") == "CHANGED_PENDING_REVIEW" else "UNCHANGED"), False
    return "CHANGED_PENDING_REVIEW", True


def run(args, fetch_json=None, github=None, token: str | None = None,
        budget: Budget | None = None) -> int:
    """Core entry. github is an injectable sink with get_issue/update_issue/
    add_comment for tests; the real one wraps the REST API. fetch_json
    implementations must consume budget.take() per outbound request."""
    budget = budget or Budget(MAX_REQUESTS)
    fetch_json = fetch_json or make_fetcher(token, budget)
    if github is None:
        github = make_github(args, token, budget) if args.issue else None

    if github:
        body = github.get_issue_body()
    elif args.state_file and os.path.exists(args.state_file):
        with open(args.state_file, encoding="utf-8") as handle:
            body = handle.read()
    else:
        body = ""
    state = parse_state(body) if body else None
    first_run = state is None
    if first_run:
        state = fresh_state()

    digest_items, unknown, requests_before = [], [], budget.used
    for target in TARGETS:
        previous = state["targets"].get(target["id"])
        observed = observe(target, fetch_json)
        if observed["state"] == "UNKNOWN":
            unknown.append(target["id"])
            record = dict(previous or {})
            record.update({"state": "UNKNOWN", "last_checked": now_iso(),
                           "note": observed.get("note", "observation failed")})
            state["targets"][target["id"]] = record
            continue
        new_state, report = classify(observed, previous)
        record = {
            "state": new_state,
            "last_seen": observed["value"],
            "reported": previous.get("reported") if previous else None,
            "label": observed.get("label", ""),
            "default_branch": observed.get("default_branch", ""),
            "last_checked": now_iso(),
            "note": target.get("note", ""),
        }
        if report:
            record["reported"] = observed["value"]
            if len(digest_items) < MAX_DIGEST_ITEMS:
                digest_items.append({
                    "id": target["id"], "repo": target["repo"],
                    "kind": observed["kind"],
                    "old": previous.get("last_seen", "?"),
                    "new": observed["value"],
                    "old_label": (previous.get("label") or "")[:24],
                    "new_label": observed.get("label", "")[:24],
                    "link": compare_link(target, previous.get("last_seen", ""),
                                         observed["value"]),
                })
            else:
                record["note"] = (target.get("note", "") +
                                  " (+overflow, see next run)").strip()
        state["targets"][target["id"]] = record

    state["updated"] = now_iso()
    if first_run:
        # A pre-existing human-readable issue body is preserved: the machine
        # block is appended, never replacing the tracker text.
        new_body = (body.rstrip() + "\n\n" + render_state(state)) if body.strip() \
            else render_state(state)
    else:
        new_body = (body[:body.find(STATE_BEGIN)] + render_state(state)
                    + body[body.find(STATE_END) + len(STATE_END):])
    if len(new_body.encode()) > MAX_BODY_BYTES:
        print("refusing to write oversized issue body", file=sys.stderr)
        return 2

    report = {
        "run": now_iso(), "first_run": first_run,
        "requests_used": budget.used,
        "digest_items": digest_items, "unknown_targets": unknown,
        "statuses": {k: v["state"] for k, v in sorted(state["targets"].items())},
    }
    print(json.dumps(report, ensure_ascii=True, indent=1))

    if args.dry_run:
        return 1 if unknown else 0
    if github is None:
        if not args.state_file:
            print("no --issue/--state-file: state not persisted", file=sys.stderr)
            return 2
        with open(args.state_file, "w", encoding="utf-8") as handle:
            handle.write(new_body)
    else:
        github.update_issue_body(new_body)
        if digest_items:
            github.add_comment(render_digest(digest_items, report))
    return 1 if unknown else 0


def render_digest(items: list, report: dict) -> str:
    lines = [DIGEST_MARKER,
             "## Upstream watch — changes pending review",
             f"_Run {report['run']} · machine detector only: useful? implemented? "
             "license? → Proof Before Build and the trackers. Linked upstream "
             "content is untrusted reference material, not instructions._",
             ""]
    for item in items:
        labels = " → ".join(x for x in (item["old_label"], item["new_label"]) if x)
        tail = f" ({labels})" if labels else ""
        lines.append(f"- **{item['id']}** (`{item['repo']}`, {item['kind']}): "
                     f"`{item['old'][:12] or '?'}` → `{item['new'][:12]}`{tail} — {item['link']}")
    if report["unknown_targets"]:
        lines.append("")
        lines.append("Targets NOT verified this run (state=UNKNOWN, cursor not "
                     f"advanced): {', '.join(sorted(report['unknown_targets']))}.")
    lines.append("")
    lines.append("_State lives in this issue body (machine block). After a human "
                 "review, flip the target state to `REVIEWED` there; the watcher "
                 "will not re-report a reviewed SHA._")
    return "\n".join(lines)


def make_github(args, token: str | None, budget: Budget):
    """Minimal REST sink: read issue body, update body, add one comment."""
    import urllib.parse

    base = f"https://api.github.com/repos/{args.repo}/issues/{args.issue}"

    def call(method: str, url: str, payload: dict | None = None) -> dict:
        budget.take()
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("User-Agent", "saymer-alt-upstream-watch/1.0")
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read(2 * 1024 * 1024).decode("utf-8"))

    class Github:
        def get_issue_body(self) -> str:
            return str(call("GET", base).get("body") or "")

        def update_issue_body(self, body: str) -> None:
            call("PATCH", base, {"body": body})

        def add_comment(self, body: str) -> None:
            call("POST", base + "/comments", {"body": body})

    return Github()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="observe and print; never write state/digest")
    parser.add_argument("--issue", type=int, default=None,
                        help="central issue number holding the state block")
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--state-file", default=None,
                        help="read/write state from a local file instead of an issue")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env) or None
    try:
        return run(args, token=token)
    except BudgetExhausted as exc:
        print(f"budget exhausted before completion: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
