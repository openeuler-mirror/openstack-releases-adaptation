#!/usr/bin/env python3
"""
cli.py - OpenStack × openEuler 自动化适配工具

统一命令行入口，按流水线顺序执行各模块任务。

Usage:
    python cli.py fetch              # 采集上游数据
    python cli.py inventory           # 采集 openEuler 现状
    python cli.py diff               # 版本对比分析
    python cli.py spec               # 自动修改 spec
    python cli.py build             # 构建验证
    python cli.py web               # 生成报告
    python cli.py run                # 完整流水线
    python cli.py --help            # 显示帮助
"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 sys.path
_SRC = Path(__file__).parent.resolve()
sys.path.insert(0, str(_SRC.parent))

import config
import fetcher
import inventory
import diff
import spec
import builder
import state
import web


def cmd_fetch(args):
    """上游数据采集：OpenStack releases + constraints"""
    cfg = config.load_config(args.config)
    print("=== Fetch: OpenStack releases ===")
    fetcher.fetch_releases(cfg)
    print("\n=== Fetch: Upper-constraints ===")
    fetcher.fetch_constraints(cfg)
    return 0


def cmd_inventory(args):
    """openEuler 现状采集：仓库列表 + spec 版本"""
    cfg = config.load_config(args.config)
    print("=== Inventory: Repos ===")
    inventory.scan_repos(cfg)
    print("\n=== Inventory: Spec Versions ===")
    inventory.scan_versions(cfg)
    return 0


def cmd_diff(args):
    """版本对比与决策分析"""
    cfg = config.load_config(args.config)
    return diff.compare(cfg)


def cmd_spec(args):
    """自动修改 spec 文件"""
    cfg = config.load_config(args.config)
    return spec.modify(cfg, dry_run=args.dry_run)


def cmd_build(args):
    """构建验证"""
    cfg = config.load_config(args.config)
    if args.docker:
        return builder.docker_build(cfg)
    if args.eur:
        return builder.eur_build(cfg)
    print("Specify --docker or --eur")
    return 1


def cmd_web(args):
    """生成状态报告"""
    cfg = config.load_config(args.config)
    return web.generate_report(cfg)


def cmd_run(args):
    """完整流水线：fetch → inventory → diff → spec → build"""
    cfg = config.load_config(args.config)

    print("Step 1/4: Fetch upstream data")
    fetcher.fetch_releases(cfg)
    fetcher.fetch_constraints(cfg)

    print("\nStep 2/4: Inventory openEuler state")
    inventory.scan_repos(cfg)
    inventory.scan_versions(cfg)

    print("\nStep 3/4: Compare and analyze")
    diff.compare(cfg)

    print("\nStep 4/4: Modify specs")
    spec.modify(cfg, dry_run=args.dry_run)

    print("\nPipeline completed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="OpenStack × openEuler 自动化适配工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s fetch              # 采集上游数据
  %(prog)s inventory          # 采集 openEuler 现状
  %(prog)s diff               # 版本对比
  %(prog)s spec --dry-run    # 预览 spec 修改
  %(prog)s build --docker     # Docker 构建
  %(prog)s run --dry-run     # 完整流水线（预览）
        """
    )
    parser.add_argument("--config", type=str, default=None,
                       help="配置文件路径 (默认: etc/config.yaml)")
    sub = parser.add_subparsers(dest="command", required=True)

    # fetch
    p_fetch = sub.add_parser("fetch", help="采集上游数据")

    # inventory
    p_inv = sub.add_parser("inventory", help="采集 openEuler 现状")

    # diff
    p_diff = sub.add_parser("diff", help="版本对比与决策分析")

    # spec
    p_spec = sub.add_parser("spec", help="自动修改 spec")
    p_spec.add_argument("--dry-run", action="store_true", help="仅预览不写入")

    # build
    p_build = sub.add_parser("build", help="构建验证")
    p_build.add_argument("--docker", action="store_true", help="Docker 构建")
    p_build.add_argument("--eur", action="store_true", help="EUR 构建")

    # web
    p_web = sub.add_parser("web", help="生成状态报告")

    # run
    p_run = sub.add_parser("run", help="完整流水线")
    p_run.add_argument("--dry-run", action="store_true", help="仅预览不写入")

    args = parser.parse_args(argv)

    handlers = {
        "fetch": cmd_fetch,
        "inventory": cmd_inventory,
        "diff": cmd_diff,
        "spec": cmd_spec,
        "build": cmd_build,
        "web": cmd_web,
        "run": cmd_run,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
