"""
atomgit.py - 收集 src-openeuler 组织下所有仓库的分支和 spec 版本信息

Usage:
    python -m src.version.atomgit --repos          → repos.json
    python -m src.version.atomgit --versions       → Version.json
    python -m src.version.atomgit --all           → repos.json + Version.json

API 端点：
    https://api.atomgit.com/api/v5/orgs/{org}/repos
    https://api.atomgit.com/api/v5/repos/{org}/{repo}/contents
    https://api.atomgit.com/api/v5/repos/{org}/{repo}/branches
"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from .config import load_config, get_repos_path, get_versions_path

# 匹配 spec 文件中的 Version 和全局宏定义
VERSION_RE = re.compile(r"^Version:\s*(.+)$", re.MULTILINE)
GLOBAL_MACRO_RE = re.compile(r"^%global\s+(\w+)\s+(.+)$", re.MULTILINE)


def get_api_urls(org: str, base_url: str) -> dict[str, str]:
    """构建 API URL 模板。"""
    return {
        "repos": f"{base_url}/orgs/{org}/repos",
        "contents": f"{base_url}/repos/{{org}}/{{repo}}/contents",
        "branches": f"{base_url}/repos/{{org}}/{{repo}}/branches",
    }


def fetch_all_repos(api_url: str, timeout: int, per_page: int = 100,
                    max_pages: int = 200) -> list[dict]:
    """
    分页获取组织下所有仓库，构造 SSH 格式的 git URL。

    Args:
        api_url: API 端点
        timeout: 请求超时（秒）
        per_page: 每页数量
        max_pages: 最大页数

    Returns:
        仓库信息列表
    """
    page = 1
    all_repos = []

    while page <= max_pages:
        params = {"page": page, "per_page": per_page, "repo_type": "code"}
        resp = requests.get(api_url, params=params, timeout=timeout)
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


def fetch_branches(branches_url: str, timeout: int) -> list[str]:
    """
    获取仓库所有分支名称列表。

    Args:
        branches_url: 分支 API URL
        timeout: 请求超时（秒）

    Returns:
        分支名称列表
    """
    branches = []
    page = 1
    while True:
        try:
            resp = requests.get(
                branches_url,
                params={"page": page, "per_page": 100},
                timeout=timeout,
            )
        except requests.RequestException:
            break
        if resp.status_code != 200:
            break
        data = resp.json()
        if not isinstance(data, list) or not data:
            break
        for b in data:
            if b.get("name"):
                branches.append(b["name"])
        if len(data) < 100:
            break
        page += 1
    return branches


def fetch_spec_names(contents_url: str, branch: str, timeout: int) -> list[str]:
    """
    获取仓库指定分支第一层目录下的所有 spec 文件名。

    Args:
        contents_url: 内容 API URL
        branch: 分支名称
        timeout: 请求超时（秒）

    Returns:
        spec 文件名列表
    """
    try:
        resp = requests.get(contents_url, params={"ref": branch}, timeout=timeout)
    except requests.RequestException:
        return []
    if resp.status_code != 200:
        return []

    items = resp.json()
    if not isinstance(items, list):
        return []

    return [item["name"] for item in items if item["name"].endswith(".spec")]


def fetch_spec_content(contents_url: str, branch: str, spec_name: str,
                       timeout: int) -> str:
    """
    获取 spec 文件原始内容。

    Args:
        contents_url: 内容 API URL
        branch: 分支名称
        spec_name: spec 文件名
        timeout: 请求超时（秒）

    Returns:
        spec 文件内容
    """
    try:
        resp = requests.get(
            contents_url,
            params={"ref": branch, "path": spec_name},
            timeout=timeout,
        )
    except requests.RequestException:
        return ""
    if resp.status_code != 200:
        return ""
    return resp.text


def resolve_macros(spec_text: str, raw_version: str) -> str:
    """
    解析 Version 字段中的 RPM 宏变量，递归替换为实际值。

    Args:
        spec_text: spec 文件完整内容
        raw_version: 原始 Version 值

    Returns:
        解析后的版本字符串
    """
    if not raw_version or "%{" not in raw_version:
        return raw_version

    macros = {}
    for m in GLOBAL_MACRO_RE.finditer(spec_text):
        macros[m.group(1)] = m.group(2).strip()

    result = raw_version
    max_depth = 10
    for _ in range(max_depth):
        changed = False
        new_result = result
        for name, val in macros.items():
            placeholder_full = "%{" + name + "}"
            placeholder_short = "%" + name
            if placeholder_full in new_result:
                new_result = new_result.replace(placeholder_full, val)
                changed = True
            elif placeholder_short in new_result and not val.startswith("%"):
                new_result = new_result.replace(placeholder_short, val)
                changed = True
        if not changed:
            break
        result = new_result

    return result


def extract_version(spec_text: str) -> str:
    """
    从 spec 文件内容提取 Version，并解析宏变量。

    Args:
        spec_text: spec 文件内容

    Returns:
        解析后的版本字符串
    """
    m = VERSION_RE.search(spec_text)
    if not m:
        return ""
    raw = m.group(1).strip()
    return resolve_macros(spec_text, raw)


def save_repos(org: str, name: str, url: str) -> None:
    """
    保存仓库名和 SSH URL 到 repos.json。

    Args:
        org: 组织名称
        name: 仓库名称
        url: SSH URL
    """
    repos_path = get_repos_path()
    records = []
    if repos_path.exists():
        records = json.loads(repos_path.read_text(encoding="utf-8"))

    idx = {r["name"]: i for i, r in enumerate(records)}
    entry = {"name": name, "url": url}
    if name in idx:
        records[idx[name]] = entry
    else:
        records.append(entry)

    records.sort(key=lambda r: r["name"])
    repos_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved: {name}")


def load_repos() -> list[dict[str, Any]]:
    """从 repos.json 加载仓库列表。"""
    repos_path = get_repos_path()
    if not repos_path.exists():
        return []
    return json.loads(repos_path.read_text(encoding="utf-8"))


def load_versions() -> dict[str, Any]:
    """从 Version.json 加载已有版本信息。"""
    versions_path = get_versions_path()
    if not versions_path.exists():
        return {}
    return json.loads(versions_path.read_text(encoding="utf-8"))


def save_versions(versions: dict[str, Any]) -> None:
    """保存版本信息到 Version.json。"""
    versions_path = get_versions_path()
    versions_path.write_text(json.dumps(versions, ensure_ascii=False, indent=2, sort_keys=True),
                            encoding="utf-8")
    print(f"Version.json saved ({len(versions)} repos)")


def process_repo(org: str, name: str, url: str, urls: dict[str, str],
                timeout: int) -> dict[str, Any]:
    """
    获取单个仓库的所有分支及每个分支的 spec Version。

    Args:
        org: 组织名称
        name: 仓库名称
        url: SSH URL
        urls: API URL 模板
        timeout: 请求超时（秒）

    Returns:
        仓库版本信息字典
    """
    result = {"name": name, "url": url, "Version": {}}

    branches = fetch_branches(urls["branches"].format(org=org, repo=name), timeout)
    if not branches:
        return result

    for branch in branches:
        spec_names = fetch_spec_names(urls["contents"].format(org=org, repo=name), branch, timeout)
        if not spec_names:
            result["Version"][branch] = "No Spec"
            continue

        found = False
        for spec_name in spec_names:
            spec_text = fetch_spec_content(
                urls["contents"].format(org=org, repo=name), branch, spec_name, timeout
            )
            if not spec_text:
                continue
            version = extract_version(spec_text)
            if version:
                result["Version"][branch] = version
                found = True
                break
        if not found:
            result["Version"][branch] = "No Spec"

    return result


def collect_repos(org: str, api_url: str, timeout: int, per_page: int,
                  max_pages: int, force: bool = False) -> int:
    """
    获取所有仓库列表并保存。

    Args:
        org: 组织名称
        api_url: API 端点
        timeout: 请求超时（秒）
        per_page: 每页数量
        max_pages: 最大页数
        force: 是否强制重新获取

    Returns:
        仓库总数
    """
    repos_path = get_repos_path()
    if repos_path.exists() and not force:
        existing = json.loads(repos_path.read_text(encoding="utf-8"))
        print(f"repos.json already exists ({len(existing)} repos). Use --re-fetch to overwrite.")
        return len(existing)

    print("=== Fetching all repos ===")
    all_repos = fetch_all_repos(api_url, timeout, per_page, max_pages)
    for r in all_repos:
        name = r.get("name", "")
        url = f"git@atomgit.com:{org}/{name}.git"
        save_repos(org, name, url)
    print(f"\nTotal repos: {len(all_repos)}")
    return len(all_repos)


def collect_versions(org: str, workers: int, urls: dict[str, str],
                    timeout: int) -> int:
    """
    并发遍历所有仓库，收集分支和 Version。

    Args:
        org: 组织名称
        workers: 并发线程数
        urls: API URL 模板
        timeout: 请求超时（秒）

    Returns:
        处理完成的仓库数
    """
    repos = load_repos()
    if not repos:
        print("repos.json not found. Run --repos first.")
        return 0

    existing = load_versions()
    merged: dict[str, Any] = dict(existing)
    pending = [r for r in repos if r["name"] not in merged]
    print(f"Total repos: {len(repos)}, new to process: {len(pending)}")

    if not pending:
        print("All repos already processed")
        return len(merged)

    print(f"Processing {len(pending)} repos (workers={workers}) ...")
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_repo, org, r["name"], r["url"], urls, timeout): r
            for r in pending
        }
        for future in as_completed(futures):
            done += 1
            if done % 50 == 0 or done == len(pending):
                print(f"  Progress: {done}/{len(pending)}")
            try:
                result = future.result()
            except Exception as e:
                result = {"name": futures[future]["name"], "url": futures[future]["url"], "Version": {}}
                print(f"  error: {e}")
            merged[result["name"]] = result
            time.sleep(0.1)

    save_versions(merged)
    return len(merged)


def main(argv: list[str] | None = None) -> int:
    """
    主函数：解析命令行参数并执行对应操作。

    Args:
        argv: 命令行参数列表，None 则使用 sys.argv

    Returns:
        0 表示成功，非 0 表示有错误
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Collect src-openeuler repos and spec versions"
    )
    parser.add_argument("--repos", action="store_true",
                       help="Fetch all repos and save to repos.json")
    parser.add_argument("--versions", action="store_true",
                       help="Fetch all branches and spec versions into Version.json")
    parser.add_argument("--all", action="store_true",
                       help="Run both --repos and --versions")
    parser.add_argument("--re-fetch", action="store_true",
                       help="Overwrite existing repos.json")
    parser.add_argument("--config", type=str, default=None,
                       help="Path to config file")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    org = config['atomgit']['org']
    base_url = config['atomgit']['base_url']
    timeout = config['atomgit']['timeout']
    per_page = config['atomgit']['per_page']
    max_pages = config['atomgit']['max_pages']
    workers = config['atomgit']['workers']

    urls = get_api_urls(org, base_url)
    api_url = urls["repos"]

    # 执行操作
    if args.all or args.repos:
        collect_repos(org, api_url, timeout, per_page, max_pages, args.re_fetch)

    if args.all or args.versions:
        print()
        collect_versions(org, workers, urls, timeout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
