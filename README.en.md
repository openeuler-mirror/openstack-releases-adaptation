# OpenStack × openEuler Automated Adaptation Tool

## Overview

This tool implements an **end-to-end automated adaptation pipeline** for porting OpenStack upstream releases to the openEuler distribution, covering version collection, diff analysis, automatic spec modification, build verification, and more.

## Architecture

```
OpenStack Releases (fetcher)
        ↓
Package & Dependency Analysis (fetcher + inventory)
        ↓
Diff & Decision (diff/)
        ↓
Auto-spec Update (spec/)
        ↓
Docker Build Test (builder/docker.py)
        ↓
EUR Build (builder/eur.py)
        ↓
CI Feedback & State (state/ + web/)
```

## Directory Structure

```
src/
├── cli.py                # Unified CLI entry point
├── config.py             # Global configuration loader
├── etc/
│   └── config.yaml      # Central configuration file
│
├── fetcher/             # Upstream data collection
│   ├── openstack.py     # OpenStack releases version scraping
│   └── constraints.py   # upper-constraints collection
│
├── inventory/           # openEuler status collection
│   ├── repo.py          # src-openeuler repository list
│   └── spec.py          # spec version information collection
│
├── diff/                # Diff analysis & decision engine
│   └── compare.py       # Version comparison, outputs upgrade_plan.json
│
├── spec/                # Automatic spec modification
│   └── modifier.py      # Version bump + Changelog append
│
├── builder/             # Build verification
│   ├── docker.py        # Docker local build
│   └── eur.py           # EUR (Copr) interaction
│
├── state/              # State management
│   └── store.py        # Package-level stage tracking
│
└── web/               # Status reporting
    └── report.py       # HTML/JSON report generation
```

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `requests>=2.28.0`, `pyyaml>=5.4.1`, `packaging`

## Quick Start

### 1. Configuration

Edit `src/etc/config.yaml` to set the target OpenStack release and openEuler branch:

```yaml
openeuler:
  lts: "24.03"
  branch: "openEuler-24.03-LTS-SP4"

openstack:
  current: "bobcat"   # Current adaptation release
```

### 2. Full Pipeline

```bash
cd src
python cli.py run --dry-run     # Preview full pipeline
python cli.py run               # Execute full pipeline
```

### 3. Step-by-Step

```bash
# Step 1: Fetch upstream data
python cli.py fetch

# Step 2: Collect openEuler status
python cli.py inventory

# Step 3: Version diff analysis
python cli.py diff

# Step 4: Auto-modify spec (preview)
python cli.py spec --dry-run

# Step 5: Build verification
python cli.py build --docker
```

### 4. Status Report

```bash
python cli.py web
```

## CLI Subcommands

| Command | Description |
|---------|-------------|
| `fetch` | Fetch OpenStack releases + upper-constraints |
| `inventory` | Fetch src-openeuler repo list and spec versions |
| `diff` | Compare versions, generate upgrade_plan.json |
| `spec` | Auto-modify spec files (supports `--dry-run`) |
| `build --docker` | Docker local build verification |
| `build --eur` | EUR remote build |
| `web` | Generate adaptation status report |
| `run` | Full pipeline (fetch → inventory → diff → spec) |

## Data Files

| File | Description |
|------|-------------|
| `etc/openstack_release.yaml` | OpenStack component versions per release |
| `data/repos.json` | src-openeuler repository list |
| `data/Version.json` | spec versions per repo branch |
| `data/constraints.json` | upper-constraints dependency constraints |
| `state/upgrade_plan.json` | Version upgrade decision list |
| `state/state.json` | Build/PR stage state tracking |

## Configuration Reference

Key configuration options (`src/etc/config.yaml`):

```yaml
openeuler:
  lts: "24.03"                          # openEuler LTS version
  branch: "openEuler-24.03-LTS-SP4"    # Target branch
  org: "src-openeuler"                  # Target organization

openstack:
  current: "bobcat"                     # Current adaptation release
  releases: [...]                       # Supported release list

inventory:
  base_url: "https://api.atomgit.com/api/v5"
  workers: 8                            # Concurrent thread count

eur:
  enabled: false                        # Enable EUR build
  owner: "openstack"

gitee:
  enabled: false                        # Enable Gitee PR
  bot: "openstack-bot"
  token_env: "GITEE_TOKEN"
```

## EUR Build States

| State | Meaning |
|-------|---------|
| `pending` | Waiting for build |
| `building` | Building in progress |
| `success` | Ready for PR |
| `failed` | Requires human intervention |
| `promoted` | Merged into src-openeuler |

## Contributing

1. Fork this repository
2. Create a feature branch (e.g. `feat/add-eur-support`)
3. Commit your code
4. Create a Pull Request

## Related Links

- [openEuler](https://www.openeuler.org/)
- [OpenStack Releases](https://releases.openstack.org/)
- [AtomGit](https://atomgit.com/)
