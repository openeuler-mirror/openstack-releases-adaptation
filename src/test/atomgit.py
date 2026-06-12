import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ORG = "src-openeuler"
BASE_URL = f"https://api.atomgit.com/api/v5/orgs/{ORG}/repos"
REPO_CONTENTS_URL = "https://api.atomgit.com/api/v5/repos/{org}/{repo}/contents"
REPO_BRANCHES_URL = "https://api.atomgit.com/api/v5/repos/{org}/{repo}/branches"
RAW_URL = "https://raw.atomgit.com/{org}/{repo}/blobs/{sha}/{path}"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REPOS_JSON = os.path.join(DATA_DIR, "repos.json")

VERSION_RE = re.compile(r"^Version:\s*(.+)$", re.MULTILINE)


def fetch_all_repos(per_page: int = 100, max_pages: int = 200) -> list[dict]:
    """分页获取组织下所有仓库基本信息。"""
    page = 1
    all_repos = []

    while page <= max_pages:
        params = {"page": page, "per_page": per_page, "repo_type": "code"}
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected response: {data}")
        if not data:
            break
        all_repos.extend(data)
        print(f"Page {page}: got {len(data)} repos")
        page += 1

    return all_repos


def fetch_repo_branches(org: str, repo: str, per_page: int = 100) -> list[dict]:
    """获取仓库所有分支列表。"""
    branches = []
    page = 1
    while True:
        url = REPO_BRANCHES_URL.format(org=org, repo=repo)
        params = {"page": page, "per_page": per_page}
        try:
            resp = requests.get(url, params=params, timeout=15)
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        data = resp.json()
        if not isinstance(data, list) or not data:
            break
        branches.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return branches


def save_repos_json(repos: list[dict], path: str = REPOS_JSON) -> None:
    """保存仓库列表到 JSON 文件。

    每个仓库记录: { name, html_url, default_branch, branches: [branch1, branch2, ...] }
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    records = []
    for r in repos:
        records.append({
            "name": r.get("name", ""),
            "html_url": r.get("html_url", ""),
            "default_branch": r.get("default_branch", "master"),
            "branches": [],   # 后续 fetch_branches 填充
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Saved {len(records)} repos to {path}")


def load_repos_json(path: str = REPOS_JSON) -> list[dict]:
    """从 JSON 文件加载仓库列表。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Repos JSON not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_spec_files(org: str, repo: str, branch: str) -> list[dict]:
    """获取仓库指定分支第一层目录下的所有 spec 文件信息。"""
    url = REPO_CONTENTS_URL.format(org=org, repo=repo)
    try:
        resp = requests.get(url, params={"ref": branch}, timeout=15)
    except requests.RequestException:
        return []
    if resp.status_code != 200:
        return []

    items = resp.json()
    if not isinstance(items, list):
        return []

    return [
        {
            "path": item["path"],
            "name": item["name"],
            "download_url": item.get("download_url", ""),
        }
        for item in items
        if item["name"].endswith(".spec")
    ]


def extract_version(download_url: str) -> str:
    """从 spec 文件下载地址获取 Version 字段值。"""
    try:
        resp = requests.get(download_url, timeout=15)
        if resp.status_code != 200:
            return ""
    except requests.RequestException:
        return ""

    m = VERSION_RE.search(resp.text)
    return m.group(1).strip() if m else ""


def update_repos_with_versions(
    branch: str = "master",
    workers: int = 8,
) -> list[dict]:
    """遍历 repos.json 中所有仓库，获取指定分支的 spec Version 并更新 JSON。

    Args:
        branch: 要查询的分支名，默认 master。
        workers: 并发下载线程数。

    Returns:
        更新后的仓库列表。
    """
    repos = load_repos_json()
    print(f"Loaded {len(repos)} repos from JSON")

    # 统计未处理的仓库
    pending = [r for r in repos if branch not in r.get("versions", {})]
    print(f"Pending repos for branch '{branch}': {len(pending)}")

    if not pending:
        print("All repos already processed, skipping.")
        return repos

    results = []
    print(f"Fetching spec versions for {len(pending)} repos (workers={workers}) ...")

    def process_repo(repo: dict) -> dict:
        """获取单个仓库指定分支的 spec 版本信息。"""
        name = repo["name"]
        result = dict(repo)
        result.setdefault("versions", {})
        result.setdefault("specs", {})

        specs = fetch_spec_files(ORG, name, branch)
        if not specs:
            return result

        for spec in specs:
            version = extract_version(spec["download_url"])
            if version:
                result["versions"][branch] = version
                result["specs"][branch] = spec["path"]
                break  # 只取第一个 spec 的版本
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process_repo, r): r for r in pending}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0 or done == len(pending):
                print(f"  Progress: {done}/{len(pending)}")
            try:
                updated = future.result()
            except Exception:
                updated = futures[future]
            # 合并结果
            idx_map = {r["name"]: i for i, r in enumerate(repos)}
            if updated["name"] in idx_map:
                repos[idx_map[updated["name"]]] = updated
            results.append(updated)
            time.sleep(0.1)

    # 保存更新后的数据
    with open(REPOS_JSON, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Updated repos saved to {REPOS_JSON}")

    return repos


def fetch_branches_for_all_repos(workers: int = 8) -> list[dict]:
    """并发获取 repos.json 中所有仓库的分支列表并保存。

    需要先有 repos.json 文件。
    """
    repos = load_repos_json()
    print(f"Loaded {len(repos)} repos")

    pending = [r for r in repos if not r.get("branches")]
    print(f"Fetching branches for {len(pending)} repos (workers={workers}) ...")

    def process(repo: dict) -> dict:
        branches = fetch_repo_branches(ORG, repo["name"])
        result = dict(repo)
        result["branches"] = [b["name"] for b in branches]
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(process, r): r for r in pending}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0 or done == len(pending):
                print(f"  Progress: {done}/{len(pending)}")
            try:
                updated = future.result()
            except Exception:
                updated = futures[future]
            idx_map = {r["name"]: i for i, r in enumerate(repos)}
            if updated["name"] in idx_map:
                repos[idx_map[updated["name"]]] = updated
            time.sleep(0.1)

    with open(REPOS_JSON, "w", encoding="utf-8") as f:
        json.dump(repos, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Branches saved to {REPOS_JSON}")
    return repos


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect src-openeuler repos and spec versions")
    parser.add_argument("--repos", action="store_true", help="Fetch all repos and save to repos.json")
    parser.add_argument("--branches", action="store_true", help="Fetch branches for all repos in repos.json")
    parser.add_argument("--branch", default="master", help="Branch to query for spec versions (default: master)")
    parser.add_argument("--re-fetch", action="store_true", help="Re-fetch repos, ignoring existing data")
    args = parser.parse_args()

    if args.repos or not os.path.exists(REPOS_JSON) or args.re_fetch:
        print("=== Step 1: Fetching all repos ===")
        all_repos = fetch_all_repos()
        save_repos_json(all_repos)
        print(f"Total repos in {ORG}: {len(all_repos)}\n")

    if args.branches:
        print("=== Step 2: Fetching branches ===")
        fetch_branches_for_all_repos()
        print()

    print(f"=== Step 3: Fetching spec versions for branch '{args.branch}' ===")
    update_repos_with_versions(branch=args.branch)

    repos = load_repos_json()
    with_versions = sum(1 for r in repos if args.branch in r.get("versions", {}))
    print(f"\nDone: {with_versions}/{len(repos)} repos have version info for branch '{args.branch}'")
