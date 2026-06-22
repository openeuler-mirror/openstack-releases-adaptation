# OpenStack × openEuler 自动化适配工具

## 项目概述

本工具实现 OpenStack 上游版本到 openEuler 发行版的**自动化适配闭环**，涵盖版本采集、差异分析、spec 自动修改、构建验证等环节。

## 软件架构

```
OpenStack Releases (fetcher)
        ↓
Package & Dependency Analysis (fetcher + inventory)
        ↓
Diff & Decision (diff/)
        ↓
Auto-spec Update (spec/)
        ↓
Docker Build Test (builder/docker.py)
        ↓
EUR Build (builder/eur.py)
        ↓
CI Feedback & State (state/ + web/)
```

## 目录结构

```
src/
├── cli.py                # 统一命令行入口
├── config.py             # 全局配置加载
├── etc/
│   └── config.yaml      # 全局配置中心
│
├── fetcher/             # 上游数据采集
│   ├── openstack.py     # OpenStack releases 版本抓取
│   └── constraints.py    # upper-constraints 采集
│
├── inventory/           # openEuler 现状采集
│   ├── repo.py          # src-openeuler 仓库列表
│   └── spec.py          # spec 版本信息采集
│
├── diff/                # 差异分析与决策引擎
│   └── compare.py       # 版本对比，输出 upgrade_plan.json
│
├── spec/                # Spec 自动修改
│   └── modifier.py      # Version bump + Changelog 追加
│
├── builder/             # 构建验证
│   ├── docker.py        # Docker 本地构建
│   └── eur.py           # EUR (Copr) 交互
│
├── state/              # 状态管理
│   └── store.py        # 包级别阶段追踪
│
└── web/               # 状态展示
    └── report.py       # HTML/JSON 报告生成
```

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖包：`requests>=2.28.0`, `pyyaml>=5.4.1`, `packaging`

## 快速开始

### 1. 配置

编辑 `src/etc/config.yaml`，设置目标 OpenStack 版本和 openEuler 分支：

```yaml
openeuler:
  lts: "24.03"
  branch: "openEuler-24.03-LTS-SP4"

openstack:
  current: "bobcat"   # 当前适配版本
```

### 2. 完整流水线

```bash
cd src
python cli.py run --dry-run     # 预览完整流程
python cli.py run               # 执行完整流程
```

### 3. 分步执行

```bash
# Step 1: 采集上游数据
python cli.py fetch

# Step 2: 采集 openEuler 现状
python cli.py inventory

# Step 3: 版本对比分析
python cli.py diff

# Step 4: 自动修改 spec（预览）
python cli.py spec --dry-run

# Step 5: 构建验证
python cli.py build --docker
```

### 4. 状态报告

```bash
python cli.py web
```

## CLI 子命令

| 命令 | 说明 |
|------|------|
| `fetch` | 采集 OpenStack releases + upper-constraints |
| `inventory` | 采集 src-openeuler 仓库列表和 spec 版本 |
| `diff` | 版本对比，生成 upgrade_plan.json |
| `spec` | 自动修改 spec 文件（支持 `--dry-run`） |
| `build --docker` | Docker 本地构建验证 |
| `build --eur` | EUR 远程构建 |
| `web` | 生成适配状态报告 |
| `run` | 完整流水线（fetch → inventory → diff → spec） |

## 数据文件

| 文件 | 说明 |
|------|------|
| `etc/openstack_release.yaml` | OpenStack 各版本组件版本 |
| `data/repos.json` | src-openeuler 仓库列表 |
| `data/Version.json` | 各仓库分支的 spec 版本 |
| `data/constraints.json` | upper-constraints 依赖约束 |
| `state/upgrade_plan.json` | 版本升级决策清单 |
| `state/state.json` | 构建/PR 阶段状态追踪 |

## 配置说明

主要配置项（`src/etc/config.yaml`）：

```yaml
openeuler:
  lts: "24.03"                    # openEuler LTS 版本
  branch: "openEuler-24.03-LTS-SP4"  # 适配分支
  org: "src-openeuler"             # 目标组织

openstack:
  current: "bobcat"               # 当前适配版本
  releases: [...]                  # 支持的版本列表

inventory:
  base_url: "https://api.atomgit.com/api/v5"
  workers: 8                       # 并发线程数

eur:
  enabled: false                   # 启用 EUR 构建
  owner: "openstack"

gitee:
  enabled: false                   # 启用 Gitee PR
  bot: "openstack-bot"
  token_env: "GITEE_TOKEN"
```

## EUR 构建状态

| 状态 | 含义 |
|------|------|
| `pending` | 等待构建 |
| `building` | 构建中 |
| `success` | 可进入 PR |
| `failed` | 需人工介入 |
| `promoted` | 已合入 src-openeuler |

## 参与贡献

1. Fork 本仓库
2. 新建功能分支（如 `feat/add-eur-support`）
3. 提交代码
4. 新建 Pull Request

## 相关链接

- [openEuler](https://www.openeuler.org/)
- [OpenStack Releases](https://releases.openstack.org/)
- [AtomGit](https://atomgit.com/)
