"""
docker.py - Docker 本地构建验证

在 Docker 容器中构建 RPM，提供快速失败反馈。
"""

from typing import Any

from config import load_config


def docker_build(pkg: str, spec_path: str, config: dict[str, Any] | None = None) -> bool:
    """
    在 Docker 容器中构建单个包。

    Args:
        pkg: 包名
        spec_path: spec 文件路径
        config: 配置字典

    Returns:
        True 构建成功，False 失败
    """
    if config is None:
        config = load_config()

    if not config["builder"]["docker"]["enabled"]:
        print("Docker build is not enabled in config")
        return False

    print(f"TODO: Docker build for {pkg} (spec: {spec_path})")
    return True


def run(config: dict[str, Any] | None = None) -> int:
    """批量 Docker 构建验证。"""
    print("Docker build runner not yet implemented")
    return 0
