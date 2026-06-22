"""
repo.py - src-openeuler 仓库列表采集

通过 Atomgit API 获取 src-openeuler 组织下的所有仓库。
"""

import json
from typing import Any

import requests

from config import load_config, get_data_path


def fetch_repos(config: dict[str, Any] | None = None) -> list[dict]:
    """
    分页获取 src-openeuler 组织下所有仓库。

    Returns:
        仓库信息列表 [{"name": ..., "url": ...}]
    """
    if config is None:
        config = load_config()

    org = config["inventory"]["org"]
    base_url = config["inventory"]["base_url"]
    timeout = config["inventory"]["timeout"]
    per_page = config["inventory"]["per_page"]
    max_pages = config["inventory"]["max_pages"]

    api_url = f"{base_url}/orgs/{org}/repos"
    page = 1
    all_repos = []

    while page <= max_pages:
        params = {"page": page, "per_page": per_page, "repo_type": "code"}
        try:
            resp = requests.get(api_url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"Error fetching repos page {page}: {e}")
            break

        if not isinstance(data, list) or not data:
            break
        all_repos.extend(data)
        print(f"Page {page}: got {len(data)} repos")
        page += 1

    return all_repos


def save_repos(repos: list[dict], org: str) -> Path:
    """将仓库列表保存为 repos.json，返回文件路径。"""
    output = []
    for r in repos:
        name = r.get("name", "")
        output.append({"name": name, "url": f"git@atomgit.com:{org}/{name}.git"})
    output.sort(key=lambda x: x["name"])

    path = get_data_path("repos.json")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def run(config: dict[str, Any] | None = None) -> int:
    """采集并保存仓库列表。"""
    if config is None:
        config = load_config()

    org = config["inventory"]["org"]
    repos = fetch_repos(config)
    path = save_repos(repos, org)
    print(f"\nTotal repos: {len(repos)}, saved to: {path}")
    return 0
