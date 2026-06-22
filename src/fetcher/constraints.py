"""
constraints.py - OpenStack upper-constraints 采集

从 opendev.org 下载各版本的 upper-constraints.txt 并解析。
"""

from pathlib import Path
from typing import Any

import requests

from config import load_config, get_data_path


def parse_constraints(text: str) -> dict[str, str]:
    """解析 upper-constraints.txt 内容为 {package: version} 字典。"""
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('-'):
            continue
        if '===' not in line:
            continue
        pkg, _, ver = line.partition('===')
        result[pkg.strip().lower().replace('-', '_')] = ver.strip()
    return result


def fetch_constraints(release_name: str, timeout: int = 30) -> dict[str, str]:
    """
    从 opendev.org 下载指定版本的 upper-constraints.txt。

    Args:
        release_name: 如 'bobcat', 'antelope'
        timeout: 请求超时（秒）

    Returns:
        {package: version} 字典
    """
    url = f"https://opendev.org/openstack/requirements/raw/branch/stable/{release_name}/upper-constraints.txt"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return parse_constraints(resp.text)
    except requests.RequestException as e:
        print(f"Error fetching constraints for {release_name}: {e}")
        return {}


def run(config: dict[str, Any] | None = None) -> int:
    """采集所有 release 的 upper-constraints。"""
    if config is None:
        config = load_config()

    releases = config['openstack']['releases']
    timeout = config['fetcher']['timeout'] // 1000

    all_constraints = {}
    for release in releases:
        name = release.split()[-1]
        print(f"Fetching constraints for {name}...")
        all_constraints[name] = fetch_constraints(name, timeout)

    output_path = get_data_path("constraints.json")
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_constraints, f, indent=2, ensure_ascii=False)

    print(f"\nConstraints saved to: {output_path}")
    return 0
