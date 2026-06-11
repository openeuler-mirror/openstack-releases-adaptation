import csv
import os
import time
import requests

ORG = "src-openeuler"
BASE_URL = f"https://api.atomgit.com/api/v5/orgs/{ORG}/repos"
REPO_CONTENTS_URL = "https://api.atomgit.com/api/v5/repos/{org}/{repo}/contents"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
REPO_CSV = os.path.join(DATA_DIR, "repos.csv")
SPEC_CSV = os.path.join(DATA_DIR, "specs.csv")


def fetch_all_repos(per_page: int = 100, max_pages: int = 200) -> list[dict]:
    """分页获取组织下所有仓库信息。"""
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


def save_repos_to_csv(repos: list[dict], path: str = REPO_CSV) -> None:
    """将仓库列表保存到 CSV 文件（name, html_url）。

    如果文件已存在，会覆盖写入。
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "html_url"])
        for r in repos:
            writer.writerow([r["name"], r["html_url"]])
    print(f"Saved {len(repos)} repos to {path}")


def load_repos_from_csv(path: str = REPO_CSV) -> list[dict]:
    """从 CSV 文件加载仓库列表。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Repo CSV not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def fetch_spec_files(repo_name: str) -> list[dict]:
    """获取仓库 master 分支下所有的 spec 文件信息（包括子目录）。"""
    spec_files = []
    _list_files_recursive(ORG, repo_name, "", spec_files)
    return spec_files


def _list_files_recursive(org: str, repo: str, path: str, spec_files: list[dict]) -> None:
    """递归列出目录下文件，收集 .spec 文件。"""
    url = REPO_CONTENTS_URL.format(org=org, repo=repo)
    params = {"ref": "master", "path": path} if path else {"ref": "master"}
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return
    items = resp.json()
    if not isinstance(items, list):
        return
    for item in items:
        if item["type"] == "dir":
            _list_files_recursive(org, repo, item["path"], spec_files)
        elif item["name"].endswith(".spec"):
            spec_files.append({
                "repo": repo,
                "path": item["path"],
                "name": item["name"],
                "download_url": item.get("download_url", ""),
            })


def save_specs_to_csv(specs: list[dict], path: str = SPEC_CSV) -> None:
    """将 spec 文件列表保存到 CSV。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo", "path", "name", "download_url"])
        for s in specs:
            writer.writerow([s["repo"], s["path"], s["name"], s["download_url"]])
    print(f"Saved {len(specs)} spec files to {path}")


def collect_all_specs(skip_existing: bool = True) -> list[dict]:
    """遍历所有仓库，收集每个仓库中的 spec 文件。

    Args:
        skip_existing: 如果为 True，跳过 spec CSV 中已有的仓库。

    Returns:
        所有找到的 spec 文件信息列表。
    """
    repos = load_repos_from_csv()
    print(f"Loaded {len(repos)} repos from CSV")

    # 加载已有 spec 记录（用于跳过）
    existing_repos: set[str] = set()
    if skip_existing and os.path.exists(SPEC_CSV):
        existing_repos = {
            row["repo"]
            for row in load_repos_from_csv(SPEC_CSV)
        }
        print(f"Skipping {len(existing_repos)} repos already processed")

    all_specs = []
    # 继承已有数据
    if skip_existing and existing_repos:
        all_specs.extend(load_repos_from_csv(SPEC_CSV))

    for i, repo in enumerate(repos):
        name = repo["name"]
        if skip_existing and name in existing_repos:
            continue
        print(f"[{i + 1}/{len(repos)}] Checking {name} ...")
        specs = fetch_spec_files(name)
        if specs:
            all_specs.extend(specs)
            for s in specs:
                print(f"  found spec: {s['path']}")
        else:
            print(f"  no spec files")
        time.sleep(0.2)

    save_specs_to_csv(all_specs)
    return all_specs


if __name__ == "__main__":
    repos = fetch_all_repos()
    save_repos_to_csv(repos)
    print(f"\nTotal repos in {ORG}: {len(repos)}\n")
    collect_all_specs()
