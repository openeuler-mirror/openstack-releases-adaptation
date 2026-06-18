"""
config.py - 公共配置管理模块

提供统一的配置加载逻辑，支持：
- 从 YAML 配置文件加载
- 环境变量覆盖
- 默认值 fallback

配置项：
    releases: OpenStack release 列表
    openstack.*: openstack.py 抓取配置
    atomgit.*: atomgit.py 配置
    data_dir: 数据文件目录
"""

import os
import yaml
from typing import Any

# 项目根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
ETC_DIR = os.path.join(PROJECT_ROOT, "etc")
DATA_DIR = os.path.join(PROJECT_ROOT, "src", "version", "data")

# 默认配置
DEFAULT_CONFIG = {
    "releases": [
        'queens', 'rocky', 'train', 'stein', 'ussuri',
        'victoria', 'wallaby', 'xena', 'yoga', 'zed',
        '2023.1 antelope', '2023.2 bobcat', '2024.1 caracal', '2024.2 dalmatian',
        '2025.1 epoxy', '2025.2 flamingo', '2026.1 gazpacho', '2026.2 hibiscus'
    ],
    "openstack": {
        "base_url": "https://releases.openstack.org/",
        "timeout": 10000,
        "verify_ssl": True,
        "output": "openstack_release.yaml"
    },
    "atomgit": {
        "org": "src-openeuler",
        "base_url": "https://api.atomgit.com/api/v5",
        "timeout": 15,
        "per_page": 100,
        "max_pages": 200,
        "workers": 8,
        "repos_file": "repos.json",
        "versions_file": "Version.json"
    }
}


def get_config_path(env_var: str = 'RELEASES_CONFIG') -> str | None:
    """获取配置文件路径，支持多层查找。"""
    paths = [
        os.environ.get(env_var),
        os.path.join(ETC_DIR, 'releases.yaml'),
    ]
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """
    加载配置，支持多层 fallback。

    Args:
        config_path: 指定配置文件路径，如果为 None 则自动查找

    Returns:
        配置字典，包含 openstack 和 atomgit 子配置
    """
    config = {
        "releases": DEFAULT_CONFIG["releases"].copy(),
        "openstack": DEFAULT_CONFIG["openstack"].copy(),
        "atomgit": DEFAULT_CONFIG["atomgit"].copy()
    }

    if config_path is None:
        config_path = get_config_path()

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            if file_config:
                if 'releases' in file_config:
                    config['releases'] = file_config['releases']
                if 'openstack' in file_config:
                    config['openstack'].update(file_config['openstack'])
                if 'atomgit' in file_config:
                    config['atomgit'].update(file_config['atomgit'])
            print(f"Loaded config from: {config_path}")
        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")

    return config


def ensure_etc_dir() -> str:
    """确保 etc 目录存在，返回其路径。"""
    os.makedirs(ETC_DIR, exist_ok=True)
    return ETC_DIR


def get_output_path(filename: str) -> str:
    """获取输出文件完整路径（相对于 etc 目录）。"""
    return os.path.join(ensure_etc_dir(), filename)


def get_data_path(filename: str) -> str:
    """获取数据文件完整路径（相对于 data 目录）。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, filename)


def get_repos_path() -> str:
    """获取 repos.json 文件路径。"""
    return get_data_path("repos.json")


def get_versions_path() -> str:
    """获取 Version.json 文件路径。"""
    return get_data_path("Version.json")
