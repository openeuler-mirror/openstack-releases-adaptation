import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yaml

BASE_URL = "https://opendev.org/api/v1/repos/openstack/releases/contents"
RAW_URL = "https://opendev.org/openstack/releases/raw/branch/master"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DELIVERABLES_DIR = os.path.join(os.path.dirname(__file__), "deliverables")

OPENDEV_GIT = "https://opendev.org"


def fetch_deliverable_list(deliverable: str) -> list[dict]:
    """通过 Gitea API 获取指定 deliverable 目录下的文件列表。"""
    url = f"{BASE_URL}/deliverables/{deliverable}?ref=master"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected API response: {data}")
    return data


def fetch_yaml_content(file_info: dict, deliverable: str) -> dict:
    """下载单个 YAML 文件并解析为字典。"""
    name = file_info["name"]
    download_url = file_info.get("download_url") or f"{RAW_URL}/deliverables/{deliverable}/{name}"
    try:
        resp = requests.get(download_url, timeout=15)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return {"name": name, "data": yaml.safe_load(resp.text)}
    except Exception as e:
        print(f"  failed: {name} ({e})")
        return {"name": name, "data": None}


def parse_deliverable(name: str, data: dict) -> dict | None:
    """从单个 deliverable YAML 中提取软件包名称、仓库地址和版本范围。

    Returns:
        {
            "name": "neutron",
            "type": "service",
            "team": "neutron",
            "release_model": "cycle-with-rc",
            "repo": "https://opendev.org/openstack/neutron",
            "versions": ["28.0.0.0b1", "28.0.0.0rc1", "28.0.0"],
            "version_range": {"min": "28.0.0.0b1", "max": "28.0.0"},
            "branches": [{"name": "stable/2026.1", "location": "28.0.0.0rc1"}],
        }
        如果解析失败返回 None。
    """
    if not data or not isinstance(data, dict):
        return None

    pkg_name = data.get("launchpad") or os.path.splitext(name)[0]

    # 提取仓库地址：从 repository-settings 或 releases.projects 中获取
    repos = list(data.get("repository-settings", {}).keys())
    releases = data.get("releases", [])
    if not repos and releases:
        for rel in releases:
            for proj in rel.get("projects", []):
                repo_key = proj.get("repo", "")
                if repo_key and repo_key not in repos:
                    repos.append(repo_key)

    repo_url = f"{OPENDEV_GIT}/{repos[0]}" if repos else ""

    # 提取所有版本号，用于确定版本范围
    versions = [rel["version"] for rel in releases if rel.get("version")]

    version_range = {}
    if versions:
        # diff-start 字段指示与上一版本的边界
        diff_start = None
        for rel in releases:
            if rel.get("diff-start"):
                diff_start = rel["diff-start"]
                break
        min_ver = diff_start if diff_start else versions[0]
        version_range = {"min": min_ver, "max": versions[-1]}

    # 提取分支信息
    branches = data.get("branches", [])

    return {
        "name": pkg_name,
        "type": data.get("type", ""),
        "team": data.get("team", ""),
        "release_model": data.get("release-model", ""),
        "repo": repo_url,
        "versions": versions,
        "version_range": version_range,
        "branches": branches,
    }


def collect_deliverables(
    deliverable: str = "gazpacho",
    skip_existing: bool = True,
    workers: int = 8,
) -> dict[str, dict]:
    """收集指定版本下所有 deliverable 的软件包信息。

    Args:
        deliverable: OpenStack release 版本代号。
        skip_existing: 如果为 True，跳过已下载的文件。
        workers: 并发下载线程数。

    Returns:
        { "package_name": { ... }, ... }
    """
    save_dir = os.path.join(DELIVERABLES_DIR, deliverable)
    os.makedirs(save_dir, exist_ok=True)

    # 检查本地是否已有文件
    local_files = set(os.listdir(save_dir)) if os.path.exists(save_dir) else set()
    if local_files:
        print(f"Found {len(local_files)} local YAML files in {save_dir}")

    # 如果本地没有文件，从远程获取
    if not local_files:
        print(f"Fetching file list for {deliverable} ...")
        file_list = fetch_deliverable_list(deliverable)
        print(f"Found {len(file_list)} files, downloading (workers={workers}) ...")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_info = {
                pool.submit(
                    fetch_yaml_content,
                    item,
                    deliverable,
                ): item
                for item in file_list
                if item["type"] == "file"
            }
            for future in as_completed(future_to_info):
                result = future.result()
                if result["data"] is not None:
                    local_path = os.path.join(save_dir, result["name"])
                    with open(local_path, "w", encoding="utf-8") as f:
                        yaml.dump(result["data"], f, default_flow_style=False, allow_unicode=True)
        print(f"Downloaded and saved to {save_dir}")
    else:
        print("Using local YAML files")

    # 解析所有本地 YAML 文件
    packages = {}
    yaml_files = sorted(f for f in os.listdir(save_dir) if f.endswith(".yaml") or f.endswith(".yml"))
    print(f"\nParsing {len(yaml_files)} deliverable files ...")

    for filename in yaml_files:
        filepath = os.path.join(save_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"  parse error: {filename} ({e})")
            continue

        pkg = parse_deliverable(filename, data)
        if pkg:
            packages[pkg["name"]] = pkg

    print(f"Parsed {len(packages)} packages")
    return packages


def save_packages_json(packages: dict, deliverable: str) -> str:
    """将软件包信息保存到 JSON 文件。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"deliverables_{deliverable}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(packages, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"Saved {len(packages)} packages to {path}")
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Collect OpenStack deliverable package info")
    parser.add_argument("deliverable", nargs="?", default="gazpacho", help="OpenStack release name (default: gazpacho)")
    parser.add_argument("--re-fetch", action="store_true", help="Re-download YAML files from remote")
    args = parser.parse_args()

    packages = collect_deliverables(args.deliverable, skip_existing=not args.re_fetch)
    save_packages_json(packages, args.deliverable)
    print(f"\nTotal: {len(packages)} packages for release {args.deliverable}")
