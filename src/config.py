"""
config.py - 全局配置加载模块

从 etc/config.yaml 加载配置，支持环境变量覆盖和默认值 fallback。
"""

import os
from pathlib import Path
from typing import Any

import yaml

# 项目路径
SRC_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SRC_DIR.parent.resolve()
ETC_DIR = SRC_DIR / "etc"
DATA_DIR = SRC_DIR / "data"
STATE_DIR = SRC_DIR / "state"


# 默认配置
DEFAULTS = {
    "openeuler": {"lts": "24.03", "branch": "openEuler-24.03-LTS-SP4", "org": "src-openeuler"},
    "openstack": {
        "current": "bobcat",
        "base_url": "https://releases.openstack.org/",
        "releases": [
            'queens', 'rocky', 'train', 'stein', 'ussuri',
            'victoria', 'wallaby', 'xena', 'yoga', 'zed',
            '2023.1 antelope', '2023.2 bobcat', '2024.1 caracal', '2024.2 dalmatian',
            '2025.1 epoxy', '2025.2 flamingo', '2026.1 gazpacho', '2026.2 hibiscus'
        ],
        "output": "openstack_release.yaml"
    },
    "fetcher": {"timeout": 10000, "verify_ssl": True},
    "inventory": {
        "base_url": "https://api.atomgit.com/api/v5",
        "timeout": 15, "per_page": 100, "max_pages": 200, "workers": 8,
        "repos_file": "repos.json", "versions_file": "Version.json"
    },
    "eur": {"enabled": False, "base_url": "", "owner": "openstack", "prefix": "openstack:"},
    "gitee": {"enabled": False, "bot": "openstack-bot", "token_env": "GITEE_TOKEN", "max_pr_per_day": 10},
    "builder": {"docker": {"enabled": False, "image": "openeuler/openstack-builder:24.03", "timeout": 600}},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典，override 覆盖 base。"""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _apply_env_overrides(config: dict) -> None:
    """用环境变量覆盖配置项。"""
    if os.environ.get("GITEE_TOKEN"):
        config["gitee"]["token"] = os.environ["GITEE_TOKEN"]
    if os.environ.get("OPENSTACK_CURRENT"):
        config["openstack"]["current"] = os.environ["OPENSTACK_CURRENT"]


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """
    加载配置。

    优先级：显式指定路径 > RELEASES_CONFIG 环境变量 > etc/config.yaml > 默认值
    """
    config = {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}

    if config_path is None:
        config_path = os.environ.get("RELEASES_CONFIG")

    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, file_config)
    else:
        default_path = ETC_DIR / "config.yaml"
        if default_path.exists():
            with open(default_path, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
            config = _deep_merge(config, file_config)

    _apply_env_overrides(config)
    return config


def get_output_path(filename: str) -> Path:
    """获取 etc 目录下输出文件路径。"""
    ETC_DIR.mkdir(parents=True, exist_ok=True)
    return ETC_DIR / filename


def get_data_path(filename: str) -> Path:
    """获取 data 目录下数据文件路径。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / filename


def get_state_path(filename: str) -> Path:
    """获取 state 目录下状态文件路径。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / filename
