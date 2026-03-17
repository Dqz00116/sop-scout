# API 接口文档

本文档描述 SOP 提取工作流的 HTTP 接口。

## 基础信息

- **Base URL**: `http://127.0.0.1:5000`
- **Content-Type**: `application/json`

## 接口列表

### 1. 启动工作流

启动 SOP 提取工作流，批量处理 Zip 文件中的聊天记录。

**接口路径**: `POST /run`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| zip_file | object | 是 | Zip 文件信息 |
| zip_file.url | string | 是 | Zip 文件的 URL 或本地路径 |
| zip_file.file_type | string | 否 | 文件类型，默认为 "default" |

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| run_id | string | 工作流运行 ID |
| status | string | 状态 |
| message | string | 提示信息 |

---

### 2. 查询进度

查询工作流的执行进度信息。

**接口路径**: `GET /progress/{run_id}`

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| run_id | string | 是 | 工作流运行 ID |

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| run_id | string | 工作流运行 ID |
| total_files | int | 总文件数 |
| processed_files | int | 已处理文件数 |
| extracted_sops | int | 已提取 SOP 数 |
| status | string | 当前状态（running/completed/cancelled/error） |
| current_batch | int | 当前批次号 |
| total_batches | int | 总批次数 |
| start_time | float | 开始时间戳（秒） |
| last_update_time | float | 最后更新时间戳（秒） |
| progress_percent | float | 进度百分比（0-100） |
| estimated_remaining_time | float | 预计剩余时间（秒），可能为 null |
| start_time_formatted | string | 格式化的开始时间 |
| last_update_time_formatted | string | 格式化的最后更新时间 |
| elapsed_time | float | 已运行时间（秒） |
| error_message | string | 错误信息，可能为 null |

---

### 3. 取消任务

取消正在运行的工作流。

**接口路径**: `POST /cancel/{run_id}`

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| run_id | string | 是 | 工作流运行 ID |

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| status | string | 取消状态（success/already_completed/not_found） |
| run_id | string | 工作流运行 ID |
| message | string | 提示信息 |

**status 说明**:

- `success`: 取消信号已发送
- `already_completed`: 任务已完成
- `not_found`: 未找到活动任务

---

### 4. 运行单个节点

运行指定的单个节点。

**接口路径**: `POST /node_run/{node_id}`

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| node_id | string | 是 | 节点 ID |

**请求参数**: 节点特定的输入参数，具体参数参考节点定义。

**响应参数**: 节点特定的输出参数，具体参数参考节点定义。

---

### 5. 流式运行（SSE）

使用 Server-Sent Events 方式流式运行工作流。

**接口路径**: `POST /run_stream`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| zip_file | object | 是 | Zip 文件信息 |
| zip_file.url | string | 是 | Zip 文件的 URL 或本地路径 |

**响应**: 流式事件，每个事件包含节点的执行信息。

---

## 状态说明

### 工作流状态

| 状态 | 说明 |
|------|------|
| running | 运行中 |
| completed | 已完成 |
| cancelled | 已取消 |
| error | 错误 |

### 文件类型

| 类型 | 说明 |
|------|------|
| image | 图片 |
| video | 视频 |
| audio | 音频 |
| document | 文档 |
| default | 默认类型 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 404 | 资源未找到 |
| 500 | 服务器内部错误 |

## 通用说明

### run_id

- 每个工作流执行都有唯一的 `run_id`
- `run_id` 用于查询进度、取消任务等操作
- 格式：UUID 字符串

### Zip 文件要求

- 必须包含 `.txt` 格式的聊天记录文件
- 支持嵌套目录结构
- 会递归查找所有 `.txt` 文件

### 聊天记录格式

聊天记录文件应包含客服与用户的对话，例如：

```
用户：你好，我想充值
客服：请提供您的账号信息
用户：我的账号是user123
客服：好的，已经为您处理充值请求
```

### 进度计算

- `progress_percent`: 基于已处理文件数占总文件数的比例
- `estimated_remaining_time`: 基于平均处理时间估算，可能为 null

### 超时设置

- 默认超时时间：900 秒（15 分钟）
- 可通过环境变量 `TIMEOUT_SECONDS` 配置

### 并发控制

- 默认并发数：50 个线程
- 最大并发数：100 个线程
- 可通过环境变量 `SOP_CONCURRENCY` 配置

## 注意事项

1. **API Key**: 必须配置 LLM API Key，否则无法调用大模型
2. **文件路径**: 支持 HTTP/HTTPS URL 和本地文件路径
3. **进度查询**: 任务完成后，进度信息会保留一段时间
4. **取消操作**: 取消信号会在下一个检查点生效，响应时间约 1-2 秒
5. **输出限制**: 单个文件最多 30,000 行，单行最多 65,535 字符

## 相关文档

- [项目说明](../README.md)
- [项目结构索引](../AGENTS.md)
