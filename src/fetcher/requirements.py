"""
requirements.py - OpenStack upper-requirements 采集

从 opendev.org 下载各版本的 upper-requirements.txt 并解析。
"""

from typing import Any

import requests
import yaml

from config import load_config, get_output_path


def fetch_constraints(release_version: str, timeout: int = 30) -> dict[str, str]:
    """
    从 opendev.org 下载指定版本的 upper-constraints.txt。

    Args:
        release_version: 如 'stable/2025.1', 'stable/2025.2' 等
        timeout: 请求超时（秒）

    Returns:
        {package: version} 字典
    """
    try:
        url = f"https://opendev.org/openstack/requirements/raw/branch/stable/{release_version}/upper-constraints.txt"
        upper_projects = requests.get(url, verify=True).content.decode().split('\n')
        requrements = {}
        for upper_project in upper_projects:
            if not upper_project or "===" not in upper_project:
                continue
            
            project_name, project_version = upper_project.split('===')
            project_version = project_version.split(';')[0]
            if project_name not in requrements:
                requrements[project_name.strip()] = project_version.strip()
            else:
                try:
                    from packaging import version
                    if version.parse(requrements[project_name.strip()]) < version.parse(project_version.strip()):
                        requrements[project_name.strip()] = project_version.strip()
                except Exception:
                    pass
        return requrements
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
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(all_constraints, f)

    print(f"\nRequirements saved to: {output_path}")
    return 0
