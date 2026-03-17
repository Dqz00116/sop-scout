# 🎯 SOP Scout

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **从客服聊天记录中智能提取标准操作流程（SOP）的 CLI 工具**
> 
> A CLI tool that intelligently extracts Standard Operating Procedures (SOP) from customer service chat records

[中文](#中文文档) | [English](#english-docs)

---

## 中文文档

### 📖 项目简介

**SOP Scout** 是一个智能的**标准操作流程（SOP）提取工具**，专门用于从游戏客服聊天记录中自动挖掘和结构化有价值的知识资产。

在客服场景中，大量有价值的处理经验分散在海量的聊天记录中。SOP Scout 通过大语言模型（LLM）智能分析这些非结构化数据，自动提取出标准化的处理流程，帮助企业：

- 📚 **沉淀知识**：将隐性经验转化为可复用的结构化知识
- 🚀 **提升效率**：新员工可通过标准化 SOP 快速上手
- 🎯 **保证质量**：统一服务标准，减少人为差异
- 🤖 **智能客服**：为 AI 客服系统提供高质量训练数据

### ✨ 核心特性

| 特性 | 说明 |
|-----|------|
| 🚀 **高性能批量处理** | ThreadPoolExecutor 实现 50+ 文件/秒并发处理 |
| 🧠 **AI 智能提取** | 基于 LLM 理解对话上下文，提取结构化 SOP |
| 🔒 **隐私保护** | 自动识别并过滤电话、身份证、密码等敏感信息 |
| 📊 **质量检测** | 内置噪声过滤，自动拒绝低质量对话 |
| 🔌 **火山引擎兼容** | 输出标准 JSONL 格式，直接对接知识库 |
| 🛠️ **简单易用** | 极简 CLI 接口，一行命令完成提取 |

### 📋 支持的问题分类

| 分类 | 描述 |
|-----|------|
| **ACCOUNT** | 注册/登录/密码/绑定/解绑/注销/找回 |
| **RECHARGE** | 充值/黑金/订单/补发/退款/购买 |
| **BUG** | 闪退/卡顿/显示异常/录像问题 |
| **ACTIVITY** | 活动奖励/规则/赛季 |
| **REPORT** | 外挂/昵称违规/不文明行为举报 |
| **KNOWLEDGE** | 游戏内知识问答 |
| **FEEDBACK** | 需要反馈给相关部门/等待官方消息 |

### 🚀 快速开始

#### 1. 环境要求

- Python 3.12 或更高版本
- pip 包管理器
- LLM API Key（支持 OpenAI 兼容格式）

#### 2. 安装

```bash
# 克隆仓库
git clone git@github.com:Dqz00116/sop-scout.git
cd sop-scout

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置 API Key

```bash
# 方式一：环境变量
export LLM_API_KEY=your_api_key_here
export LLM_BASE_URL=https://api.example.com/v1

# 方式二：.env 文件（推荐）
cp .env.example .env
# 编辑 .env 文件填写你的 API Key
```

#### 4. CLI 使用

```bash
# 基础用法
python -m src.cli input.zip -o ./output/

# 进阶用法（调整并发数）
python -m src.cli input.zip -o ./output/ -c 100 -v

# 批量处理（使用 GNU parallel）
ls *.zip | parallel -j 4 "python -m src.cli {} -o ./output/{/.}/"
```

**CLI 参数说明：**

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| `input` | 输入 zip 文件路径 | 必填 |
| `-o, --output` | 输出目录 | `./output/` |
| `-c, --concurrency` | 并发线程数 | 50 |
| `-v, --verbose` | 显示详细日志 | False |

### 📤 输出格式

#### JSONL 示例

```json
{
  "id": "RECHARGE_订单问题_001",
  "category": "RECHARGE",
  "subcategory": "订单问题",
  "when": {
    "scenario": "用户反馈充值后未到账",
    "keywords": ["充值", "未到账", "订单"],
    "user_queries": ["我充的钱怎么没到账？", "充值失败了怎么办？"]
  },
  "then": {
    "actions": ["查询订单状态", "核实支付渠道", "补发或退款"],
    "response": "请您提供订单号，我帮您查询充值记录。如确认未到账，将为您补发。"
  },
  "notes": "需核实支付渠道是否为官方",
  "source": "用户：我充了648但是没到账。客服：请您提供订单号..."
}
```

#### 文件限制

- 单个文件最大行数：30,000 行
- 单行最大字符数：65,535 字符
- 超过限制自动分割为多个文件

### 🏗️ 架构设计

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  Input Zip  │────▶│ extract_files│────▶│batch_extract │────▶│merge_results│
│  (聊天记录)  │     │   (解压提取)  │     │  (批量并行)   │     │  (合并输出)  │
└─────────────┘     └──────────────┘     └──────┬───────┘     └──────┬──────┘
                                                │                     │
                                                ▼                     ▼
                                         ┌──────────────┐      ┌─────────────┐
                                         │  check_quality│      │  save_local │
                                         │  filter_noise │      │  (CLI 输出) │
                                         │filter_sensitive│     └─────────────┘
                                         │  extract_sop  │
                                         └──────────────┘
```

### 📁 项目结构

```
sop-scout/
├── config/                    # 配置目录
│   └── extract_sop_cfg.json  # LLM 提示词配置
├── docs/                      # 文档目录
│   ├── API.md                # HTTP API 文档
│   ├── CLI_MVP_DESIGN.md     # CLI 设计文档
│   └── WINDOWS_DEPLOYMENT.md # Windows 部署指南
├── scripts/                   # 脚本目录
│   ├── http_run.sh           # HTTP 服务启动
│   └── local_run.sh          # 本地运行脚本
├── src/                       # 源码目录
│   ├── cli.py                # 🆕 CLI 入口（即将推出）
│   ├── graphs/               # LangGraph 工作流
│   │   ├── nodes/            # 处理节点
│   │   ├── graph.py          # 主工作流
│   │   └── state.py          # 状态定义
│   ├── utils/                # 工具类
│   └── main.py               # HTTP 服务入口
├── requirements.txt           # 依赖列表
└── README.md                  # 本文档
```

### ⚙️ 高级配置

#### 并发配置

```bash
# 环境变量
export SOP_CONCURRENCY=50        # 并发线程数（默认 50，最大 100）
export SOP_BATCH_SIZE=10         # 每批处理文件数

# CLI 参数覆盖
python -m src.cli input.zip -c 100
```

#### 自定义模型

编辑 `config/extract_sop_cfg.json`：

```json
{
  "config": {
    "model": "your-model-name",
    "temperature": 0.3,
    "max_completion_tokens": 16384
  },
  "sp": "你的系统提示词...",
  "up": "你的用户提示词..."
}
```

### 🔧 HTTP 服务模式（可选）

如需使用 HTTP API 服务：

```bash
# 启动服务
python src/main.py --port 5000

# 调用接口
curl -X POST http://127.0.0.1:5000/run \
  -H "Content-Type: application/json" \
  -d '{"zip_file": {"url": "/path/to/chat.zip"}}'

# 查询进度
curl http://127.0.0.1:5000/progress/{run_id}
```

详见 [API 文档](docs/API.md)

### ❓ 常见问题

**Q: 如何批量处理多个 zip 文件？**

A: 使用 GNU parallel：
```bash
ls *.zip | parallel -j 4 "python -m src.cli {} -o ./out/{/.}/"
```

**Q: 如何处理 WSL 路径？**

A: 直接使用 Linux 风格路径：
```bash
python -m src.cli /mnt/e/data/1号.zip -o /mnt/e/output/
```

**Q: 任务处理太慢？**

A: 增加并发数（根据机器配置调整）：
```bash
python -m src.cli input.zip -c 100
```

**Q: 如何更换 LLM 模型？**

A: 编辑 `config/extract_sop_cfg.json` 文件，修改 `model` 字段。

### 🤝 贡献指南

欢迎提交 Issue 和 PR！

### 📄 许可证

[MIT License](LICENSE)

---

## English Docs

### 📖 Introduction

**SOP Scout** is an intelligent **Standard Operating Procedure (SOP) extraction tool** designed to automatically mine and structure valuable knowledge assets from customer service chat records.

In customer service scenarios, massive amounts of valuable handling experience are scattered across unstructured chat records. SOP Scout leverages Large Language Models (LLM) to intelligently analyze this data and automatically extract standardized procedures.

### ✨ Features

- 🚀 **High Performance**: ThreadPoolExecutor for 50+ files/sec concurrent processing
- 🧠 **AI-Powered**: LLM-based intelligent SOP extraction from conversation context
- 🔒 **Privacy First**: Auto-identify and mask sensitive information (phone, ID, passwords)
- 📊 **Quality Control**: Built-in noise filtering and quality detection
- 🔌 **Compatible**: Standard JSONL output, direct integration with Volcano Engine KB
- 🛠️ **Easy to Use**: Minimal CLI interface, one command to extract

### 📋 Supported Categories

| Category | Description |
|---------|-------------|
| **ACCOUNT** | Registration / Login / Password / Binding / Recovery |
| **RECHARGE** | Recharge / Orders / Refunds / Purchase Issues |
| **BUG** | Crashes / Lags / Display Issues / Recording Problems |
| **ACTIVITY** | Event Rewards / Rules / Seasons |
| **REPORT** | Cheating / Nickname Violations / Misconduct |
| **KNOWLEDGE** | In-game Q&A |
| **FEEDBACK** | Issues requiring escalation or pending response |

### 🚀 Quick Start

```bash
# Clone repository
git clone git@github.com:Dqz00116/sop-scout.git
cd sop-scout

# Install dependencies
pip install -r requirements.txt

# Configure API key
export LLM_API_KEY=your_api_key
export LLM_BASE_URL=https://api.example.com/v1

# Run extraction
python -m src.cli input.zip -o ./output/
```

### 📄 License

[MIT License](LICENSE)

---

<p align="center">
  Made with ❤️ by SOP Scout Team
</p>
