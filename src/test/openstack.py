import os
import time
import requests

BASE_URL = "https://opendev.org/api/v1/repos/openstack/releases/contents"
BRANCH = "master"
RAW_URL = "https://opendev.org/openstack/releases/raw/branch/master"


def fetch_file_list(path: str) -> list[dict]:
    """通过 Gitea API 获取指定路径下的文件列表。

    Args:
        path: 仓库中的相对路径，如 "deliverables/gazpacho"。
    """
    url = f"{BASE_URL}/{path}?ref={BRANCH}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected API response: {data}")
    return data


def save_file(file_info: dict, save_dir: str) -> None:
    """下载单个文件并保存到本地。优先使用 download_url，回退到 raw URL。"""
    name = file_info["name"]
    download_url = file_info.get("download_url") or f"{RAW_URL}/{file_info['path']}"
    dest = os.path.join(save_dir, name)

    resp = requests.get(download_url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    with open(dest, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"  saved: {name}")


def save_deliverable_files(deliverable: str = "gazpacho") -> int:
    """下载指定 deliverable 目录下的所有文件到本地。

    Args:
        deliverable: OpenStack release 版本代号，如 gazpacho, 2025.1 等。

    Returns:
        成功下载的文件数量。
    """
    api_path = f"deliverables/{deliverable}"
    save_dir = os.path.join(os.path.dirname(__file__), "deliverables", deliverable)
    os.makedirs(save_dir, exist_ok=True)

    print(f"Fetching file list for {deliverable} ...")
    file_list = fetch_file_list(api_path)
    print(f"Found {len(file_list)} files, downloading ...")

    count = 0
    for item in file_list:
        if item["type"] != "file":
            continue
        save_file(item, save_dir)
        count += 1
        time.sleep(0.1)

    print(f"Done: {count} files saved to {save_dir}")
    return count


if __name__ == "__main__":
    save_deliverable_files("gazpacho")
