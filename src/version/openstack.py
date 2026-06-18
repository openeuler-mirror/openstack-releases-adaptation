"""
openstack.py - OpenStack releases 版本信息抓取

从 https://releases.openstack.org 抓取各版本的组件版本信息，
输出到 etc/openstack_release.yaml。

Usage:
    python -m src.version.openstack
    python src/version/openstack.py
    from src.version.openstack import main
"""

from packaging import version
import re
import sys

import requests
import yaml

from .config import load_config, get_output_path


def fetch_release_packages(release: str, base_url: str, timeout: int,
                           verify_ssl: bool) -> dict[str, str]:
    """
    抓取单个 release 的所有组件版本。

    Args:
        release: Release 名称（如 '2024.1 caracal'）
        base_url: OpenStack releases 基础 URL
        timeout: 请求超时（毫秒）
        verify_ssl: 是否验证 SSL

    Returns:
        组件名到版本的字典
    """
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
        # 跳过 -last 和 -eom 版本
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
                if version.parse(results[pkg_name]) < version.parse(pkg_ver):
                    results[pkg_name] = pkg_ver
            except Exception as e:
                print(f"{release}: {pkg_name}")
                print(f"Error occurred: {e}\n")

    return results


def main(config_path: str | None = None) -> int:
    """
    主函数：抓取所有 OpenStack releases 版本信息。

    Args:
        config_path: 配置文件路径，None 则自动查找

    Returns:
        0 表示成功，非 0 表示有错误
    """
    config = load_config(config_path)
    releases = config['releases']
    base_url = config['openstack']['base_url']
    timeout = config['openstack']['timeout']
    verify_ssl = config['openstack']['verify_ssl']
    output_filename = config['openstack']['output']

    all_results = {}
    for release in releases:
        print(f"Fetching {release}...")
        results = fetch_release_packages(release, base_url, timeout, verify_ssl)
        all_results[release.split()[0]] = results

    output_path = get_output_path(output_filename)
    with open(output_path, 'w', encoding='utf-8') as fp:
        yaml.dump(all_results, fp)

    print(f"\nResults saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
