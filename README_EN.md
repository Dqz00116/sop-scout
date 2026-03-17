# 🎯 SOP Scout

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A CLI tool that intelligently extracts Standard Operating Procedures (SOP) from customer service chat records

[中文](README.md)

---

## 📖 Introduction

**SOP Scout** is an intelligent **Standard Operating Procedure (SOP) extraction tool** designed to automatically mine and structure valuable knowledge assets from customer service chat records.

In customer service scenarios, massive amounts of valuable handling experience are scattered across unstructured chat records. SOP Scout leverages Large Language Models (LLM) to intelligently analyze this data and automatically extract standardized procedures, helping enterprises to:

- 📚 **Knowledge Retention**: Transform tacit experience into reusable structured knowledge
- 🚀 **Efficiency Boost**: Enable new employees to ramp up quickly with standardized SOPs
- 🎯 **Quality Assurance**: Unify service standards and reduce human variance
- 🤖 **AI Customer Service**: Provide high-quality training data for AI customer service systems

### ✨ Features

| Feature | Description |
|--------|-------------|
| 🚀 **High Performance** | ThreadPoolExecutor for high concurrent processing |
| 🧠 **AI-Powered** | LLM-based intelligent SOP extraction from conversation context |
| 🔒 **Privacy First** | Auto-identify and mask sensitive information (phone, ID, passwords) |
| 📊 **Quality Control** | Built-in noise filtering and quality detection |
| 🔌 **Multi-Model Support** | Support Moonshot (Kimi), Doubao, OpenAI, etc. |
| 🛠️ **Easy to Use** | Minimal CLI interface, one command to extract |

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

---

## 🚀 Quick Start

### 1. Requirements

- Python 3.12 or higher
- pip package manager

### 2. Installation

```bash
# Clone repository
git clone git@github.com:Dqz00116/sop-scout.git
cd sop-scout

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key

Set the environment variable according to your chosen model:

```bash
# If using Moonshot (Kimi)
export LLM_API_KEY=sk-your-moonshot-api-key

# If using Doubao (Volcengine)
export ARK_API_KEY=sk-your-doubao-api-key

# If using OpenAI
export OPENAI_API_KEY=sk-your-openai-api-key
```

Or create a `.env` file in the project root:
```bash
LLM_API_KEY=sk-your-api-key
```

### 4. Select Model

Edit `config/extract_sop_cfg.json` and modify the `llm.model` field:

```json
{
    "llm": {
        "model": "kimi-k2-turbo"
    },
    ...
}
```

List available models:
```bash
python -c "from src.utils.llm_config import print_models; print_models()"
```

### 5. Run CLI

```bash
# Basic usage
python -m src.cli_simple input.zip -o ./output/

# Advanced usage (adjust concurrency + verbose)
python -m src.cli_simple input.zip -o ./output/ -c 100 -v

# Batch processing (using GNU parallel)
ls *.zip | parallel -j 4 "python -m src.cli_simple {} -o ./output/{/.}/"
```

**CLI Parameters:**

| Parameter | Description | Default |
|----------|-------------|---------|
| `input` | Input zip file path | Required |
| `-o, --output` | Output directory | `./output/` |
| `-c, --concurrency` | Concurrent threads | 50 |
| `-v, --verbose` | Show detailed logs | False |

---

## 📤 Output Format

### JSONL Example

```json
{
  "id": "RECHARGE_order_issue_001",
  "category": "RECHARGE",
  "subcategory": "Order Issue",
  "when": {
    "scenario": "User reports recharge not received",
    "keywords": ["recharge", "not received", "order"],
    "user_queries": ["Where is my recharge?", "Recharge failed, what should I do?"]
  },
  "then": {
    "actions": ["Check order status", "Verify payment channel", "Resend or refund"],
    "response": "Please provide your order number, I will check the recharge record for you."
  },
  "notes": "Need to verify if payment channel is official",
  "source": "User: I recharged 648 but didn't receive. Agent: Please provide order number..."
}
```

### File Limits

- Max lines per file: 30,000
- Max characters per line: 65,535
- Auto-split into multiple files if exceeds limits

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  Input Zip  │────▶│ extract_files│────▶│batch_extract │────▶│merge_results│
│  (Chat Log) │     │  (Extract)   │     │ (Batch Proc) │     │   (Merge)   │
└─────────────┘     └──────────────┘     └──────┬───────┘     └──────┬──────┘
                                                │                     │
                                                ▼                     ▼
                                         ┌──────────────┐      ┌─────────────┐
                                         │  check_quality│      │  save_local │
                                         │  filter_noise │      │  (CLI Out)  │
                                         │filter_sensitive│     └─────────────┘
                                         │  extract_sop  │
                                         └──────────────┘
```

---

## 📁 Project Structure

```
sop-scout/
├── config/                    # Config directory
│   ├── extract_sop_cfg.json  # Main config (model selection, prompts)
│   └── llm_presets.yaml      # LLM presets (models, URLs, etc.)
├── docs/                      # Documentation
│   ├── API.md                # HTTP API docs
│   ├── CLI_MVP_DESIGN.md     # CLI design docs
│   └── WINDOWS_DEPLOYMENT.md # Windows deployment guide
├── src/                       # Source code
│   ├── cli_simple.py         # CLI entry (Coze-free version)
│   ├── graphs/               # LangGraph workflows
│   │   ├── nodes/            # Processing nodes
│   │   ├── simple_graph.py   # Simplified workflow
│   │   └── state.py          # State definitions
│   └── utils/                # Utilities
│       ├── llm_client.py     # LLM client
│       └── llm_config.py     # Config manager
├── requirements.txt           # Dependencies
└── README_EN.md               # This document
```

---

## ⚙️ Advanced Configuration

### Concurrency Configuration

```bash
# Environment variables
export SOP_CONCURRENCY=50        # Concurrent threads (default 50, max 100)
export SOP_BATCH_SIZE=10         # Files per batch

# CLI parameter override
python -m src.cli_simple input.zip -c 100
```

### Custom Model Parameters

Edit `config/extract_sop_cfg.json`:

```json
{
    "llm": {
        "model": "kimi-k2-turbo"
    },
    "generation": {
        "temperature": 0.3,
        "max_tokens": 16384,
        "top_p": 0.9
    },
    "prompt": {
        "system": "Your system prompt...",
        "user_template": "Your user prompt template..."
    }
}
```

### Add Custom Model

Edit `config/llm_presets.yaml`:

```yaml
your-provider:
  name: "Your Provider Name"
  api_key_env: "YOUR_API_KEY_ENV"
  base_url: "https://api.your-provider.com/v1"
  models:
    your-model-alias:
      id: "actual-model-id"
      description: "Model description"
```

---

## ❓ FAQ

**Q: How to list available models?**

```bash
python -c "from src.utils.llm_config import print_models; print_models()"
```

**Q: How to batch process multiple zip files?**

```bash
ls *.zip | parallel -j 4 "python -m src.cli_simple {} -o ./out/{/.}/"
```

**Q: How to handle WSL paths?**

```bash
python -m src.cli_simple /mnt/e/data/chat.zip -o /mnt/e/output/
```

**Q: Processing too slow?**

Increase concurrency (adjust based on your machine):
```bash
python -m src.cli_simple input.zip -c 100
```

**Q: How to switch LLM model?**

Edit `config/extract_sop_cfg.json` and modify the `llm.model` field to an available model alias.

---

## 🤝 Contributing

Issues and PRs are welcome!

---

## 📄 License

[MIT License](LICENSE)

---

<p align="center">
  Made with ❤️ by SOP Scout Team
</p>
