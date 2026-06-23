"""
openstack.py - OpenStack releases 版本信息采集

从 releases.openstack.org 抓取各版本组件版本。
"""

import re
from typing import Any

import requests
import yaml

from config import load_config, get_data_path


def fetch_release_packages(release: str, base_url: str, timeout: int,
                           verify_ssl: bool) -> dict[str, str]:
    """抓取单个 release 的所有组件版本。"""
    release_name = release.split()[-1]
    release_version = release.split()[0]
    url = base_url + release_name

    try:
        content = requests.get(url, verify=verify_ssl, timeout=timeout).content.decode()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {release}: {e}")
        return {}

    links = re.findall(r'https://.*\.tar\.gz', content)
    results = {}

    for pkg_link in links:
        if any(tag in pkg_link for tag in [f"{release_name}-last", f"{release_version}-last",
                                            f"{release_name}-eom", f"{release_version}-eom"]):
            continue

        tmp = pkg_link.split("/")
        pkg_full_name = tmp[4]
        pkg_name = pkg_full_name[0:pkg_full_name.rfind('-')]
        pkg_ver = pkg_full_name[pkg_full_name.rfind('-') + 1:pkg_full_name.rfind('.tar')]

        if pkg_name not in results:
            results[pkg_name] = pkg_ver
        else:
            try:
                from packaging import version
                if version.parse(results[pkg_name]) < version.parse(pkg_ver):
                    results[pkg_name] = pkg_ver
            except Exception:
                pass

    return results


def run(config: dict[str, Any] | None = None, config_path: str | None = None) -> int:
    """
    抓取所有 OpenStack releases 版本信息。

    Args:
        config: 配置字典（优先）
        config_path: 配置文件路径

    Returns:
        0 成功，非 0 失败
    """
    if config is None:
        config = load_config(config_path)

    releases = config['openstack']['releases']
    base_url = config['openstack']['base_url']
    timeout = config['fetcher']['timeout']
    verify_ssl = config['fetcher']['verify_ssl']
    output_filename = config['openstack']['output_release']

    all_results = {}
    for release in releases:
        print(f"Fetching {release}...")
        results = fetch_release_packages(release, base_url, timeout, verify_ssl)
        all_results[release.split()[0]] = results

        output_path = get_data_path(release.split()[0],output_filename)
        with open(output_path, 'w', encoding='utf-8') as fp:
            yaml.dump(all_results, fp)

        print(f"\nResults saved to: {output_path}")
    return 0
