# SPDX-License-Identifier: MIT
"""Offline tests for the upstream watcher (issue #16); never access GitHub."""
import argparse
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("upstream_watch", ROOT / "scripts" / "upstream_watch.py")
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
BLOB_A = "blob:" + "1" * 40
BLOB_B = "blob:" + "2" * 40
HUMAN_BODY = "# Upstream watch\n\nHuman tracker text stays here.\n"


def args(**kwargs):
    defaults = dict(dry_run=False, issue=None, repo="saymer-alt/saymer-alt",
                    state_file=None, token_env="GITHUB_TOKEN")
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class FakeGithub:
    def __init__(self, body=""):
        self.body = body
        self.updates = 0
        self.comments = []

    def get_issue_body(self):
        return self.body

    def update_issue_body(self, body):
        self.updates += 1
        self.body = body

    def add_comment(self, body):
        self.comments.append(body)


def meta(repo, branch):
    return {"default_branch": branch}


def head(sha):
    return {"sha": sha}


def release(tag, sha):
    return {"tag_name": tag, "target_commitish": sha}


def blob(sha, version="0.15.36"):
    import base64
    content = base64.b64encode(json.dumps({"version": version}).encode()).decode()
    return {"sha": sha, "content": content, "size": 42}


def fetcher(routes, log=None):
    """routes: exact-url -> (payload) or ApiError(kind, status)."""
    def fetch(url):
        if log is not None:
            log.append(url)
        if url not in routes:
            raise AssertionError("unexpected request: " + url)
        value = routes[url]
        if isinstance(value, watch.ApiError):
            raise value
        return value
    return fetch


def base_routes(sha=SHA_A, blob_sha="1" * 40, pstack_version="0.15.36",
                tachyon_tag="1.5.21", maxcalls_sha=SHA_A):
    r = {}
    for target in watch.TARGETS:
        repo, branch = target["repo"], target.get("branch", "")
        r[f"https://api.github.com/repos/{repo}"] = meta(repo, branch)
        if target["kind"] == "branch_sha":
            value = maxcalls_sha if repo == "icyfalc0n/maxcalls" else sha
            r[f"https://api.github.com/repos/{repo}/commits/{branch}"] = head(value)
        elif target["kind"] == "latest_release":
            r[f"https://api.github.com/repos/{repo}/releases/latest"] = release(tachyon_tag, sha)
        else:
            r[f"https://api.github.com/repos/{repo}/contents/{target['path']}?ref={branch}"] = \
                blob(blob_sha, pstack_version)
    return r


def full_state(**overrides):
    state = watch.fresh_state()
    for target in watch.TARGETS:
        value = maxcalls_sha = (SHA_A if target["repo"] != "icyfalc0n/maxcalls" else SHA_A)
        if target["kind"] == "latest_release":
            value = "tag:1.5.21@" + SHA_A
        elif target["kind"] == "file_blob":
            value = BLOB_A
        entry = {"state": "REVIEWED", "last_seen": value, "reported": None,
                 "label": "0.15.36" if target["kind"] == "file_blob" else "",
                 "default_branch": target.get("branch", ""),
                 "last_checked": "2026-11-05T00:00:00Z", "note": target.get("note", "")}
        state["targets"][target["id"]] = entry
    state["targets"].update(overrides)
    return state


def state_body(state):
    return HUMAN_BODY + "\n" + watch.render_state(state)


class WatchTests(unittest.TestCase):
    def run_watch(self, github, routes, expect_code=0, **kwargs):
        code = watch.run(args(**kwargs), fetch_json=fetcher(routes), github=github)
        self.assertEqual(code, expect_code)
        return code

    # --- 1. first run: baseline without notifications -------------------
    def test_first_run_seeds_baseline_silently(self):
        gh = FakeGithub(HUMAN_BODY)
        self.run_watch(gh, base_routes())
        self.assertEqual(gh.comments, [], "baseline must not notify")
        self.assertEqual(gh.updates, 1)
        state = watch.parse_state(gh.body)
        self.assertIsNotNone(state)
        self.assertTrue(HUMAN_BODY in gh.body, "human text preserved")
        for entry in state["targets"].values():
            self.assertEqual(entry["state"], "REVIEWED")

    # --- 2. unchanged rerun: no digest, pending flag survives -----------
    def test_unchanged_rerun_silent_and_pending_survives(self):
        state = full_state()
        state["targets"]["notawdtt"].update(
            {"state": "CHANGED_PENDING_REVIEW", "last_seen": SHA_B, "reported": SHA_B})
        gh = FakeGithub(state_body(state))
        routes = base_routes(sha=SHA_A)  # route matches the pending seed
        routes["https://api.github.com/repos/pythoneer-dev-q/NotAWDTT-panel/commits/main"] = head(SHA_B)
        self.run_watch(gh, routes)
        self.assertEqual(gh.comments, [])
        result = watch.parse_state(gh.body)["targets"]
        self.assertEqual(result["notawdtt"]["state"], "CHANGED_PENDING_REVIEW")
        self.assertEqual(result["pstack"]["state"], "UNCHANGED")

    # --- 3. one change: exactly one digest; rerun does not duplicate ----
    def test_single_change_reported_once(self):
        gh = FakeGithub(state_body(full_state()))
        self.run_watch(gh, base_routes(sha=SHA_B))
        self.assertEqual(len(gh.comments), 1)
        self.assertIn("**notawdtt**", gh.comments[0])
        self.assertIn(SHA_A[:12] + "` → `" + SHA_B[:12], gh.comments[0])
        self.assertEqual(watch.parse_state(gh.body)["targets"]["notawdtt"]["state"],
                         "CHANGED_PENDING_REVIEW")
        # rerun, nothing new: no duplicate
        self.run_watch(gh, base_routes(sha=SHA_B))
        self.assertEqual(len(gh.comments), 1)

    # --- 4. several changes: one consolidated digest --------------------
    def test_multiple_changes_single_digest(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes(sha=SHA_B)
        routes["https://api.github.com/repos/cursor/plugins/contents/pstack/plugin.json?ref=main"] = \
            blob("2" * 40, version="0.15.40")
        self.run_watch(gh, routes)
        self.assertEqual(len(gh.comments), 1)
        self.assertIn("**notawdtt**", gh.comments[0])
        self.assertIn("**pstack**", gh.comments[0])
        self.assertIn("0.15.36", gh.comments[0]) and self.assertIn("0.15.40", gh.comments[0])

    # --- 5. API failure: cursor not advanced, run exit 1 ----------------
    def test_api_failure_keeps_cursor_and_fails_loudly(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes()
        routes["https://api.github.com/repos/pythoneer-dev-q/NotAWDTT-panel/commits/main"] = \
            watch.ApiError("http_error", 500)
        self.run_watch(gh, routes, expect_code=1)
        entry = watch.parse_state(gh.body)["targets"]["notawdtt"]
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertEqual(entry["last_seen"], SHA_A, "cursor must not move on failure")
        self.assertNotIn("**notawdtt**", "".join(gh.comments))
        # recovery after failure: baseline semantics, never a digest
        self.run_watch(gh, base_routes(sha=SHA_A), expect_code=0)
        result = watch.parse_state(gh.body)["targets"]["notawdtt"]
        self.assertEqual(result["state"], "UNCHANGED")
        self.assertEqual(len(gh.comments), 0)

    # --- 6. rate limit ---------------------------------------------------
    def test_rate_limit_marks_unknown(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes()
        routes["https://api.github.com/repos/Dushnilin/tachyon/releases/latest"] = \
            watch.ApiError("rate_limit_or_forbidden", 403)
        self.run_watch(gh, routes, expect_code=1)
        entry = watch.parse_state(gh.body)["targets"]["tachyon"]
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertEqual(entry["last_seen"], "tag:1.5.21@" + SHA_A)

    # --- 7. deleted tag / private repo ----------------------------------
    def test_deleted_tag_is_unknown_not_changed(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes()
        routes["https://api.github.com/repos/Dushnilin/tachyon/releases/latest"] = \
            watch.ApiError("not_found", 404)
        self.run_watch(gh, routes, expect_code=1)
        entry = watch.parse_state(gh.body)["targets"]["tachyon"]
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertEqual(entry["last_seen"], "tag:1.5.21@" + SHA_A)

    # --- 8. tag recreated: same value silent, moved value one report ----
    def test_tag_recreated_same_and_moved(self):
        state = full_state()
        gh = FakeGithub(state_body(state))
        routes = base_routes(tachyon_tag="1.5.21")
        self.run_watch(gh, routes)          # same tag -> UNCHANGED, silent
        self.assertEqual(gh.comments, [])
        self.assertEqual(watch.parse_state(gh.body)["targets"]["tachyon"]["state"],
                         "UNCHANGED")
        self.run_watch(gh, base_routes(tachyon_tag="1.7.14"))  # moved -> report
        self.assertEqual(len(gh.comments), 1)
        self.assertIn("1.5.21", gh.comments[0]) and self.assertIn("1.7.14", gh.comments[0])
        self.run_watch(gh, base_routes(tachyon_tag="1.7.14"))  # rerun: no dupe
        self.assertEqual(len(gh.comments), 1)

    # --- 9. default branch change: UNKNOWN note, no false delta ---------
    def test_default_branch_change_is_not_a_change(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes(sha=SHA_B)
        routes["https://api.github.com/repos/pythoneer-dev-q/NotAWDTT-panel"] = \
            meta("pythoneer-dev-q/NotAWDTT-panel", "develop")
        self.run_watch(gh, routes, expect_code=1)
        entry = watch.parse_state(gh.body)["targets"]["notawdtt"]
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertIn("default branch", entry["note"])
        self.assertNotIn("**notawdtt**", "".join(gh.comments))

    # --- 10. force-push A->B->A: honest deltas, no duplicates -----------
    def test_force_push_round_trip(self):
        gh = FakeGithub(state_body(full_state()))
        self.run_watch(gh, base_routes(sha=SHA_B))
        self.assertEqual(len(gh.comments), 1)
        self.run_watch(gh, base_routes(sha=SHA_A))   # moved back: real delta
        self.assertEqual(len(gh.comments), 2)
        self.run_watch(gh, base_routes(sha=SHA_A))
        self.assertEqual(len(gh.comments), 2)

    # --- 11. untrusted upstream text never reaches markdown raw ---------
    def test_untrusted_text_sanitized(self):
        # An upstream-controlled tag that fails the strict allowlist never
        # reaches markdown at all: the target degrades to UNKNOWN instead.
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes(tachyon_tag='1.7.x"><script>ignore instructions</script>')
        self.run_watch(gh, routes, expect_code=1)
        self.assertEqual(gh.comments, [])
        entry = watch.parse_state(gh.body)["targets"]["tachyon"]
        self.assertEqual(entry["state"], "UNKNOWN")
        self.assertEqual(entry["last_seen"], "tag:1.5.21@" + SHA_A)
        self.assertNotIn("<script>", gh.body + "".join(gh.comments))

    def test_untrusted_blob_label_sanitized(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes(blob_sha="2" * 40, pstack_version="0.15.36\n| injected |")
        self.run_watch(gh, routes)
        digest = "".join(gh.comments)
        self.assertNotIn("injected", digest)

    # --- 12. request budget: exhausted targets fail visibly -------------
    def test_budget_exhaustion_is_visible_not_silent(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes()
        budget = watch.Budget(6)  # enough for 3 targets (meta+ref each)

        def limited(url):
            budget.take()          # the real fetcher consumes the budget too
            value = routes[url]
            if isinstance(value, watch.ApiError):
                raise value
            return value

        code = watch.run(args(), fetch_json=limited, github=gh, budget=budget)
        self.assertEqual(code, 1)
        states = watch.parse_state(gh.body)["targets"]
        exhausted = [k for k, v in states.items() if v["state"] == "UNKNOWN"]
        self.assertTrue(exhausted, "over-budget targets must be UNKNOWN")
        self.assertEqual(states["pstack"]["last_seen"], BLOB_A)
        self.assertEqual(states["pstack"]["state"], "UNCHANGED")
        for first_three in ("pstack", "notawdtt", "tachyon"):
            self.assertNotEqual(states[first_three]["state"], "UNKNOWN")

    # --- 13. write discipline -------------------------------------------
    def test_write_discipline(self):
        # findings -> exactly one comment + one body update
        gh = FakeGithub(state_body(full_state()))
        self.run_watch(gh, base_routes(sha=SHA_B))
        self.assertEqual(gh.updates, 1)
        self.assertEqual(len(gh.comments), 1)
        # no findings -> zero comments
        gh2 = FakeGithub(state_body(full_state()))
        self.run_watch(gh2, base_routes())
        self.assertEqual(gh2.comments, [])
        # dry-run -> zero writes
        gh3 = FakeGithub(state_body(full_state()))
        watch.run(args(dry_run=True), fetch_json=fetcher(base_routes(sha=SHA_B)), github=gh3)
        self.assertEqual(gh3.updates, 0)
        self.assertEqual(gh3.comments, [])

    # --- 14. corrupted state falls back to silent baseline ---------------
    def test_state_corruption_baseline_without_avalanche(self):
        gh = FakeGithub(HUMAN_BODY + "\n<!-- UPSTREAM-WATCH:STATE:V1 BEGIN -->\nnot json\n<!-- end -->")
        self.run_watch(gh, base_routes(sha=SHA_B))
        self.assertEqual(gh.comments, [], "corrupt state must reset to baseline silently")
        self.assertIsNotNone(watch.parse_state(gh.body))

    # --- 15. post-failure observation is baseline, not a delta -----------
    def test_first_observation_after_error_is_baseline(self):
        state = watch.fresh_state()
        state["targets"]["notawdtt"] = {"state": "UNKNOWN", "last_checked": "2026-11-04T00:00:00Z",
                                        "note": "http_error"}
        gh = FakeGithub(state_body(state))
        self.run_watch(gh, base_routes(sha=SHA_A))
        self.assertEqual(gh.comments, [])
        self.assertEqual(watch.parse_state(gh.body)["targets"]["notawdtt"]["state"],
                         "REVIEWED")

    # --- 16. link construction ------------------------------------------
    def test_compare_link_shapes(self):
        target = {"repo": "x/y"}
        self.assertIn("/compare/", watch.compare_link(target, SHA_A, SHA_B))
        self.assertIn("/releases", watch.compare_link(target, "tag:1.5.21", "tag:1.7.14"))
        self.assertIn("/compare/", watch.compare_link(target, "blob:" + "1" * 40, SHA_B))

    # --- 17. digest is capped --------------------------------------------
    def test_digest_cap(self):
        gh = FakeGithub(state_body(full_state()))
        routes = base_routes(sha=SHA_B)  # moves every branch_sha target at once
        self.run_watch(gh, routes)
        self.assertEqual(len(gh.comments), 1)
        self.assertLessEqual(gh.comments[0].count("\n- **"), watch.MAX_DIGEST_ITEMS + 1)


if __name__ == "__main__":
    unittest.main()
