"""
eur.py - EUR 构建交互

与 EUR (Copr) 平台交互：创建 project、添加 package、触发构建、查询状态。
"""

from typing import Any

from config import load_config


def run(config: dict[str, Any] | None = None) -> int:
    """EUR 构建入口。"""
    if config is None:
        config = load_config()

    if not config["eur"]["enabled"]:
        print("EUR build is not enabled in config")
        return 0

    print("EUR build integration not yet implemented")
    return 0
