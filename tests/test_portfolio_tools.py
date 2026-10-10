# SPDX-License-Identifier: MIT
"""Offline tests; never access GitHub from CI."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


metadata = module("metadata", "portfolio_metadata.py")
traffic = module("traffic", "github_traffic_snapshot.py")


class PortfolioTests(unittest.TestCase):
    def test_topics_add_without_deleting_existing(self):
        current = {"topics": ["existing-topic"], "description": "old"}
        patch, topics = metadata.plan("keenetic-nvr", current, {
            "description": "new", "topics_add": ["nvr", "existing-topic"]})
        self.assertEqual(patch, {"description": "new"})
        self.assertEqual(topics, ["existing-topic", "nvr"])
        self.assertIsNone(metadata.plan("x", {"topics": topics}, {
            "topics_add": ["nvr"]})[1])

    def test_default_config_targets_only_allowlisted_repos(self):
        self.assertEqual(set(metadata.CHANGES), {
            "link-generators", "keenetic-knowledge-base", "keenetic-nvr",
            "entware-go",
        })

    def test_traffic_rejects_unexpected_repo_metric(self):
        with self.assertRaises(ValueError):
            traffic.read_metric("private-server", "views")
        with self.assertRaises(ValueError):
            traffic.read_metric("keenetic-nvr", "secrets")

    def test_traffic_collect_has_fixed_repos(self):
        sample = lambda repo, metric: {"count": 3, "uniques": 2, metric: []}
        with patch.object(traffic, "read_metric", side_effect=sample) as reader:
            data = traffic.collect("2026-10-10")
        self.assertEqual(set(data["repos"]), set(traffic.REPOS))
        self.assertEqual(reader.call_count, 16)
        self.assertEqual(data["schema"], 1)

    def test_traffic_api_fail_closed(self):
        fake = subprocess.CompletedProcess([], 1, stdout="", stderr="error")
        with patch.object(subprocess, "run", return_value=fake):
            with self.assertRaises(RuntimeError):
                traffic.read_metric("keenetic-nvr", "views")

    def test_traffic_private_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / "private"
            saved = traffic.save({"day_utc": "2026-10-10", "repos": {}}, folder)
            self.assertTrue(saved.is_file())
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(saved.read_text())["day_utc"], "2026-10-10")
            with self.assertRaises(FileExistsError):
                traffic.save({"day_utc": "2026-10-10", "repos": {}}, folder)


if __name__ == "__main__":
    unittest.main()
