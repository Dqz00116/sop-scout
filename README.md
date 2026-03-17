# SOP 提取工作流

## 项目概述

基于 LangGraph 的 SOP（标准操作流程）提取工作流，支持从游戏客服聊天记录中批量提取结构化的 SOP 信息，并输出符合火山引擎知识库格式标准的 JSONL 文件。

### 核心功能

- **批量处理**: 支持从 Zip 文件批量处理聊天记录
- **多线程并发**: 使用线程池并发处理文件，大幅提升处理速度
- **质量检测**: 自动检测聊天记录质量，拒绝噪声数据
- **敏感信息过滤**: 自动过滤电话、身份证、密码等敏感信息
- **SOP 提取**: 使用大语言模型智能提取结构化 SOP
- **进度查询**: 实时查询工作流执行进度
- **任务取消**: 支持中途取消长时间运行的任务

### 技术栈

- Python 3.12+
- LangGraph 1.0
- LangChain 1.0
- FastAPI
- doubao-seed-2-0-pro-260215（LLM模型）
- S3 兼容对象存储

### 跨平台支持

本项目支持 **Linux** 和 **Windows** 系统，自动处理跨平台兼容性问题。

- [Windows 部署指南](docs/WINDOWS_DEPLOYMENT.md) - 详细的 Windows 部署说明

## 快速开始

### 1. 环境要求

- Python 3.12 或更高版本
- pip 包管理器

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 LLM API Key

创建或编辑环境变量配置文件：

**方式一：使用 .env 文件**

在项目根目录创建 `.env` 文件：

```bash
# LLM API 配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.example.com/v1

# 对象存储配置（如果使用）
S3_ENDPOINT=https://s3.example.com
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET=your_bucket_name

# 并发配置（可选）
SOP_CONCURRENCY=50
SOP_BATCH_SIZE=10
```

**方式二：直接设置环境变量**

```bash
export LLM_API_KEY=your_api_key_here
export LLM_BASE_URL=https://api.example.com/v1
```

**方式三：在代码中配置**

在 `config/extract_sop_cfg.json` 中配置模型信息：

```json
{
  "config": {
    "model": "doubao-seed-2-0-pro-260215",
    "temperature": 0.3,
    "top_p": 0.7,
    "max_completion_tokens": 2000,
    "thinking": "disabled"
  },
  "tools": [],
  "sp": "你是SOP提取专家...",
  "up": "请从以下聊天记录中提取SOP..."
}
```

### 4. 本地部署步骤

#### 步骤 1: 启动 HTTP 服务

```bash
bash scripts/http_run.sh -m http -p 5000
```

或直接运行：

```bash
python src/main.py --port 5000
```

服务启动后，会监听 `http://127.0.0.1:5000`

#### 步骤 2: 验证服务状态

```bash
curl http://127.0.0.1:5000/
```

返回 `{"status": "ok"}` 表示服务正常

#### 步骤 3: 调用接口

参考 [API 文档](docs/API.md) 了解详细的接口说明

## 运行流程

### 本地运行

运行完整工作流：

```bash
bash scripts/local_run.sh -m flow
```

运行单个节点：

```bash
bash scripts/local_run.sh -m node -n extract_files_node
```

### HTTP 服务

启动 HTTP 服务：

```bash
bash scripts/http_run.sh -m http -p 5000
```

## 接口文档

详细的接口说明请参考：[API 文档](docs/API.md)

## 项目结构

```
├── config                          # 配置目录
│   └── extract_sop_cfg.json       # LLM 配置文件
├── docs                            # 文档目录
│   └── API.md                      # API 接口文档
├── scripts                         # 脚本目录
│   ├── http_run.sh                 # HTTP 服务启动脚本
│   └── local_run.sh                # 本地运行脚本
├── src                             # 源码目录
│   ├── agents                      # Agent 代码
│   ├── graphs                      # 工作流编排
│   │   ├── nodes                   # 节点实现
│   │   ├── state.py                # 状态定义
│   │   ├── loop_graph.py           # 循环子图
│   │   └── graph.py                # 主图
│   ├── main.py                     # 服务入口
│   ├── storage                     # 存储相关
│   ├── tests                       # 测试用例
│   ├── tools                       # 工具定义
│   └── utils                       # 工具类
│       ├── cancel_manager.py       # 取消管理器
│       └── progress_manager.py     # 进度管理器
├── assets                          # 资源目录
├── requirements.txt                # 依赖列表
└── README.md                       # 项目说明
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_API_KEY` | LLM API 密钥 | 必填 |
| `LLM_BASE_URL` | LLM API 基础 URL | 必填 |
| `SOP_CONCURRENCY` | 并发线程数 | 50 |
| `SOP_BATCH_SIZE` | 批处理大小 | 10 |
| `S3_ENDPOINT` | 对象存储端点 | 可选 |
| `S3_ACCESS_KEY` | 对象存储访问密钥 | 可选 |
| `S3_SECRET_KEY` | 对象存储密钥 | 可选 |
| `S3_BUCKET` | 对象存储桶名 | 可选 |

### 并发配置

- `SOP_CONCURRENCY`: 并发处理文件的线程数，默认 50，最大 100
- `SOP_BATCH_SIZE`: 每批处理的文件数，默认 10

## 使用示例

### 1. 创建测试数据

创建包含聊天记录的 Zip 文件：

```bash
# 创建测试文件
echo "用户：你好，我想充值" > chat1.txt
echo "客服：请提供您的账号信息" >> chat1.txt

# 打包成 Zip 文件
zip -r chat_records.zip chat1.txt
```

### 2. 调用提取接口

```bash
curl -X POST http://127.0.0.1:5000/run \
  -H "Content-Type: application/json" \
  -d '{
    "zip_file": {
      "url": "/path/to/chat_records.zip"
    }
  }'
```

### 3. 查询进度

```bash
curl http://127.0.0.1:5000/progress/{run_id}
```

### 4. 取消任务

```bash
curl -X POST http://127.0.0.1:5000/cancel/{run_id}
```

## 输出格式

### JSONL 格式

每行一个 JSON 对象，包含提取的 SOP 信息：

```json
{"question": "用户问题", "answer": "客服回答", "category": "问题分类"}
{"question": "另一个问题", "answer": "另一个回答", "category": "问题分类"}
```

### 文件限制

- 最大行数：30,000 行
- 单行最大字符数：65,535 字符
- 超过限制时自动分割为多个文件

## 常见问题

### Q: 如何更换 LLM 模型？

A: 编辑 `config/extract_sop_cfg.json` 文件，修改 `model` 字段。

### Q: 如何调整并发数？

A: 设置环境变量 `SOP_CONCURRENCY`，例如：`export SOP_CONCURRENCY=100`

### Q: 如何查看日志？

A: 日志文件位于 `/app/work/logs/bypass/app.log`

### Q: 任务超时怎么办？

A: 可以使用 `/cancel/{run_id}` 接口取消任务，或增加 `TIMEOUT_SECONDS` 环境变量。

## 相关文档

- [API 接口文档](docs/API.md)
- [项目结构索引](AGENTS.md)

## License

MIT
