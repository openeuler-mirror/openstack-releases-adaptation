"""
requirements.py - OpenStack upper-requirements 采集

从 opendev.org 下载各版本的 upper-requirements.txt 并解析。
"""

from typing import Any

import requests

from config import load_config, get_output_path


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


def fetch_constraints(release_version: str, timeout: int = 30) -> dict[str, str]:
    """
    从 opendev.org 下载指定版本的 upper-constraints.txt。

    Args:
        release_version: 如 'stable/2025.1', 'stable/2025.2' 等
        timeout: 请求超时（秒）

    Returns:
        {package: version} 字典
    """
    url = f"https://opendev.org/openstack/requirements/raw/branch/stable/{release_version}/upper-constraints.txt"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return parse_constraints(resp.text)
    except requests.RequestException as e:
        print(f"Error fetching constraints for {release_version}: {e}")
        return {}


def run(config: dict[str, Any] | None = None) -> int:
    """采集所有 release 的 upper-constraints。"""
    if config is None:
        config = load_config()

    releases = config['openstack']['releases']
    output_filename = config['openstack']['output_requirements']
    timeout = config['fetcher']['timeout'] // 1000

    all_constraints = {}
    for release in releases:
        release_name = release.split()[-1]
        release_version = release.split()[0]
        print(f"Fetching constraints for {release_version}...")
        all_constraints[release_version] = fetch_constraints(release_version, timeout)

    output_path = get_output_path(output_filename)
    import json
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_constraints, f, indent=2, ensure_ascii=False)

    print(f"\nRequirements saved to: {output_path}")
    return 0
