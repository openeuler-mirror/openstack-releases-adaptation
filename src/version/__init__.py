"""
version - OpenStack 版本适配工具包

提供 OpenStack 各版本组件版本信息抓取、AtomGit 仓库版本收集、
版本对比等功能。

主要模块：
    - openstack: OpenStack releases 版本抓取
    - atomgit: AtomGit 仓库版本收集
    - config: 公共配置管理

Usage:
    # CLI 模式
    python -m src.version.openstack
    python -m src.version.atomgit --all

    # 模块导入
    from src.version import openstack, atomgit, config
"""

from .config import (
    DEFAULT_CONFIG,
    load_config,
    get_config_path,
    get_output_path,
    get_data_path,
    get_repos_path,
    get_versions_path,
    ensure_etc_dir,
)

from .openstack import main as openstack_main, fetch_release_packages
from .atomgit import (
    main as atomgit_main,
    collect_repos,
    collect_versions,
    fetch_all_repos,
    fetch_branches,
    extract_version,
)

__version__ = "1.0.0"
__all__ = [
    # config
    "DEFAULT_CONFIG",
    "load_config",
    "get_config_path",
    "get_output_path",
    "get_data_path",
    "get_repos_path",
    "get_versions_path",
    "ensure_etc_dir",
    # openstack
    "openstack_main",
    "fetch_release_packages",
    # atomgit
    "atomgit_main",
    "collect_repos",
    "collect_versions",
    "fetch_all_repos",
    "fetch_branches",
    "extract_version",
]
