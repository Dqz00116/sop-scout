# SOP Scout - 项目描述

## 中文版本

**SOP Scout** 是一个智能的**标准操作流程（SOP）提取工具**，专门用于从游戏客服聊天记录中自动挖掘和结构化有价值的知识资产。

### 核心价值

在客服场景中，大量有价值的处理经验分散在海量的聊天记录中。SOP Scout 通过大语言模型（LLM）智能分析这些非结构化数据，自动提取出标准化的处理流程，帮助企业：

- 📚 **沉淀知识**：将隐性经验转化为可复用的结构化知识
- 🚀 **提升效率**：新员工可通过标准化 SOP 快速上手
- 🎯 **保证质量**：统一服务标准，减少人为差异
- 🤖 **智能客服**：为 AI 客服系统提供高质量训练数据

### 技术亮点

| 特性 | 说明 |
|-----|------|
| **LangGraph 工作流** | 基于状态图的工作流编排，模块化设计 |
| **批量并行处理** | ThreadPoolExecutor 实现高并发，支持每秒处理 50+ 文件 |
| **智能质量检测** | 自动过滤低质量、噪声对话 |
| **敏感信息脱敏** | 自动识别并过滤电话、身份证、密码等敏感内容 |
| **火山引擎兼容** | 输出标准 JSONL 格式，直接对接火山引擎知识库 |

### 输出格式

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
    "response": "请您提供订单号，我帮您查询..."
  },
  "notes": "需核实支付渠道是否为官方",
  "source": "关键对话片段"
}
```

---

## English Version

**SOP Scout** is an intelligent **Standard Operating Procedure (SOP) extraction tool** designed to automatically mine and structure valuable knowledge assets from customer service chat records.

### Core Value

In customer service scenarios, massive amounts of valuable handling experience are scattered across unstructured chat records. SOP Scout leverages Large Language Models (LLM) to intelligently analyze this data and automatically extract standardized procedures, helping enterprises to:

- 📚 **Knowledge Retention**: Transform tacit experience into reusable structured knowledge
- 🚀 **Efficiency Boost**: Enable new employees to ramp up quickly with standardized SOPs
- 🎯 **Quality Assurance**: Unify service standards and reduce human variance
- 🤖 **AI Customer Service**: Provide high-quality training data for AI customer service systems

### Technical Highlights

| Feature | Description |
|--------|-------------|
| **LangGraph Workflow** | State-based workflow orchestration with modular design |
| **Batch Parallel Processing** | ThreadPoolExecutor for high concurrency, 50+ files/sec |
| **Intelligent Quality Detection** | Auto-filter low-quality and noisy conversations |
| **Sensitive Data Masking** | Auto-identify and filter phone numbers, IDs, passwords |
| **Volcano Engine Compatible** | Standard JSONL output, direct integration with Volcano Engine KB |

### Supported Categories

- **ACCOUNT**: Registration / Login / Password / Binding / Recovery
- **RECHARGE**: Recharge / Orders / Refunds / Purchase Issues
- **BUG**: Crashes / Lags / Display Issues / Recording Problems
- **ACTIVITY**: Event Rewards / Rules / Seasons
- **REPORT**: Cheating / Nickname Violations / Misconduct
- **KNOWLEDGE**: In-game Q&A
- **FEEDBACK**: Issues requiring escalation or pending official response

### Quick Start

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

### License

MIT License - Feel free to use and modify for your needs.

---

## 一句话描述

> **中文**：SOP Scout - 从客服聊天记录中智能提取标准操作流程（SOP）的 CLI 工具
> 
> **English**: SOP Scout - A CLI tool that intelligently extracts Standard Operating Procedures from customer service chat records

## GitHub About 设置建议

```
🏷️ Topics: sop-extraction, customer-service, llm, langgraph, knowledge-management, cli-tool, python

📋 Description: 从游戏客服聊天记录中提取结构化 SOP 的智能工具 / Intelligent SOP extraction tool from game customer service chat records
```
