# Portfolio maintenance tools

These helpers manage only the explicitly listed public projects of `saymer-alt`.
They use the authenticated [GitHub CLI](https://cli.github.com/) (`gh`).
**Neither script stores or prints tokens.**

## 1. Audit and update repository descriptions / Topics

```sh
python3 scripts/portfolio_metadata.py          # dry run, no changes
python3 scripts/portfolio_metadata.py --apply  # requires repo Administration: write
```

The updater is limited to **four confirmed discrepancies**:

- `link-generators`: remove the absolute "keys/configs never leave browser" claim; subscription preview can use a Cloudflare Worker
- `keenetic-knowledge-base`: set the homepage to the searchable GitHub Pages site
- `keenetic-nvr`: add relevant Topics; retain existing topics
- `entware-go`: replace generic inherited fork description and add Topics; retain existing topics

Before `--apply`, review proposed values in `scripts/portfolio_metadata.py`.
After mutation, the script re-reads and verifies every repository.
It does not change Pins, branches, permissions, releases, or repository visibility.

The linked GitHub integration used to add this tool cannot change repository
About/Topics settings; an owner/admin must run the updater through an
authorized CLI or have an authorized agent run it.

## 2. Capture a daily snapshot of GitHub Traffic

GitHub Traffic API provides approximately **14 days** of view and clone data.
To preserve a longer history, run the script **at least once every 14 days**
(daily is recommended). GitHub traffic `uniques` across dates or snapshots
must **not** be summed as if they represent different people.

```sh
# Needs a GitHub token authorized to read Traffic for all eight repositories.
gh auth status
python3 scripts/github_traffic_snapshot.py --output-dir ~/github-traffic-private
```

A new, private-mode (`0600`) JSON file named `traffic-YYYY-MM-DD.json`
is written **outside any public repository**. Existing snapshots are never
overwritten. Snapshot files include only aggregated repository-level daily
views/clones and GitHub's overall counts/uniques, **not** visitor identities,
referrers, or private projects.

To automate on a trusted Linux VPS that has `gh` authorized with the required
GitHub Traffic permissions, schedule the script in that user's **own cron** at
04:20 daily (the actual file paths and interpreter may vary):

```cron
20 4 * * * /usr/bin/python3 /path/to/saymer-alt/scripts/github_traffic_snapshot.py --output-dir /path/to/private/traffic
```

The cron host must retain its own authorized `gh` CLI credentials securely;
do not put tokens in scripts, cron lines, Actions logs, public Issues or README.
If the API returns permission errors, use a fine-grained token with read-only
repository Administration permission for the eight repositories (or suitable
classic-token permissions), following GitHub's current requirements.

**No recurring job is installed by this repository.** The owner must enable
cron/Task Scheduler on a chosen private host. Publishing traffic JSON into a
public profile repository is intentionally unsupported.

## Testing

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```
