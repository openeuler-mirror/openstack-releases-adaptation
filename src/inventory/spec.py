"""
spec.py - spec 文件版本信息采集

通过 Atomgit API 获取各仓库分支的 spec 文件中的 Version。
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from config import load_config, get_data_path

VERSION_RE = re.compile(r"^Version:\s*(.+)$", re.MULTILINE)
GLOBAL_MACRO_RE = re.compile(r"^%global\s+(\w+)\s+(.+)$", re.MULTILINE)


def resolve_macros(spec_text: str, raw_version: str) -> str:
    """递归解析 RPM 宏变量。"""
    if not raw_version or "%{" not in raw_version:
        return raw_version
    macros = {m.group(1): m.group(2).strip() for m in GLOBAL_MACRO_RE.finditer(spec_text)}

    result = raw_version
    for _ in range(10):
        changed = False
        for name, val in macros.items():
            for placeholder in (f"%{{{name}}}", f"%{name}"):
                if placeholder in result:
                    result = result.replace(placeholder, val)
                    changed = True
        if not changed:
            break
    return result


def extract_version(spec_text: str) -> str:
    """从 spec 文件内容提取 Version。"""
    m = VERSION_RE.search(spec_text)
    if not m:
        return ""
    return resolve_macros(spec_text, m.group(1).strip())


def fetch_branches(base_url: str, org: str, repo: str, timeout: int) -> list[str]:
    """获取仓库所有分支。"""
    url = f"{base_url}/repos/{org}/{repo}/branches"
    branches, page = [], 1
    while True:
        try:
            resp = requests.get(url, params={"page": page, "per_page": 100}, timeout=timeout)
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        data = resp.json()
        if not isinstance(data, list) or not data:
            break
        branches.extend(b["name"] for b in data if b.get("name"))
        if len(data) < 100:
            break
        page += 1
    return branches


def fetch_spec_version(base_url: str, org: str, repo: str, branch: str, timeout: int) -> str:
    """获取仓库指定分支的 spec Version。"""
    contents_url = f"{base_url}/repos/{org}/{repo}/contents"
    try:
        resp = requests.get(contents_url, params={"ref": branch}, timeout=timeout)
    except requests.RequestException:
        return ""

    if resp.status_code != 200:
        return ""
    items = resp.json()
    if not isinstance(items, list):
        return ""

    spec_names = [item["name"] for item in items if item["name"].endswith(".spec")]
    for spec_name in spec_names:
        try:
            resp = requests.get(contents_url, params={"ref": branch, "path": spec_name}, timeout=timeout)
        except requests.RequestException:
            continue
        if resp.status_code != 200:
            continue
        version = extract_version(resp.text)
        if version:
            return version
    return "No Spec"


def process_repo(org: str, repo_name: str, repo_url: str,
                 base_url: str, timeout: int) -> dict[str, Any]:
    """获取单个仓库的所有分支版本。"""
    result = {"name": repo_name, "url": repo_url, "Version": {}}
    branches = fetch_branches(base_url, org, repo_name, timeout)
    for branch in branches:
        result["Version"][branch] = fetch_spec_version(base_url, org, repo_name, branch, timeout)
    return result


def run(config: dict[str, Any] | None = None) -> int:
    """并发采集所有仓库的 spec 版本。"""
    if config is None:
        config = load_config()

    org = config["inventory"]["org"]
    base_url = config["inventory"]["base_url"]
    timeout = config["inventory"]["timeout"]
    workers = config["inventory"]["workers"]

    repos_path = get_data_path("repos.json")
    if not repos_path.exists():
        print("repos.json not found. Run 'inventory repo' first.")
        return 1

    repos = json.loads(repos_path.read_text(encoding="utf-8"))

    # 增量：加载已有版本
    versions_path = get_data_path("Version.json")
    merged = json.loads(versions_path.read_text(encoding="utf-8")) if versions_path.exists() else {}
    pending = [r for r in repos if r["name"] not in merged]
    print(f"Total: {len(repos)}, pending: {len(pending)}")

    if not pending:
        print("All repos already processed")
        return 0

    print(f"Processing {len(pending)} repos (workers={workers})...")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_repo, org, r["name"], r["url"], base_url, timeout): r
            for r in pending
        }
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == len(pending):
                print(f"  Progress: {done}/{len(pending)}")
            try:
                merged[future.result()["name"]] = future.result()
            except Exception as e:
                name = futures[future]["name"]
                print(f"  error processing {name}: {e}")
            time.sleep(0.1)

    versions_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True),
                            encoding="utf-8")
    print(f"\nVersion.json saved ({len(merged)} repos)")
    return 0
