## 项目概述
- **名称**: SOP提取工作流（性能优化版 + 跨平台支持）
- **功能**: 从游戏客服聊天记录中批量提取结构化SOP，支持Zip文件输入，多线程并发处理，输出符合火山引擎知识库格式标准的JSONL文件
- **跨平台支持**: 自动处理 Windows/Linux 系统的路径差异，使用 `tempfile.gettempdir()` 获取系统临时目录
- **性能优化**:
  - 批量LLM调用：将文件分批处理，每批预过滤后批量调用LLM，预计提升30-50%吞吐量
  - 流水线并行：规则处理步骤（filter_noise、filter_sensitive）并行执行，预计减少20-30%单文件处理时间
  - 提示词优化：精简系统提示词和用户提示词，减少Token消耗，预计减少10-20%LLM调用时间

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| extract_files | `nodes/extract_files_node.py` | task | 解压Zip文件并提取所有.txt文件 | - | - |
| **batch_extract** | `nodes/batch_extract_node.py` | task | **批量提取SOP（性能优化）**：文件分批、预过滤、批量LLM调用 | - | - |
| merge_results | `nodes/merge_results_node.py` | task | 合并所有提取的SOP | - | - |
| upload_files | `nodes/upload_files_node.py` | task | 上传JSONL文件到对象存储 | - | - |
| parallel_process | `loop_graph.py` | task | 并行入口节点，用于启动流水线并行 | - | - |
| check_quality | `nodes/check_quality_node.py` | condition | 质量检测，判断文件是否包含有效对话 | "通过"→parallel_process, "不通过"→skip_file | - |
| filter_noise | `nodes/filter_noise_node.py` | task | 过滤噪声段落（与filter_sensitive并行） | - | - |
| filter_sensitive | `nodes/filter_sensitive_node.py` | task | 过滤敏感信息（与filter_noise并行） | - | - |
| extract_sop | `nodes/extract_sop_node.py` | agent | 提取SOP | - | `config/extract_sop_cfg.json` |
| filter_contact_sop | `nodes/filter_contact_sop_node.py` | task | 过滤引导联系客服的SOP | - | - |
| skip_file | `loop_graph.py` | task | 跳过低质量文件 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支)

## 子图清单
| 子图名 | 文件位置 | 功能描述 | 被调用节点 |
|-------|---------|------|---------|-----------|
| loop_graph | `graphs/loop_graph.py` | 单文件处理流程（质量检测→并行过滤→提取→格式化） | batch_extract |

## 技能使用
- 节点`extract_sop`使用大语言模型技能（doubao-seed-2-0-pro-260215）
- 节点`upload_files`使用对象存储技能

## 并发处理配置
- **并发方式**: ThreadPoolExecutor（线程池）
- **默认并发数**: 50个线程（可通过环境变量 `SOP_CONCURRENCY` 配置）
- **最大并发数**: 100个线程（硬编码限制）
- **批处理大小**: 10个文件/批（可通过环境变量 `SOP_BATCH_SIZE` 配置）
- **超时时间**: 单个文件处理超时120秒，批次等待超时2秒

## 环境变量配置
```bash
SOP_CONCURRENCY=50        # 并发线程数（默认50，最大100）
SOP_BATCH_SIZE=10         # 批处理大小（默认10）
```

## 性能优化说明
1. **批量预过滤 + 单个文件LLM调用**：
   - 文件分批处理（默认每批10个文件）
   - 每批文件先进行规则处理（质量检测、噪声过滤、敏感信息过滤）- 批量并行
   - 通过预过滤的文件内容，每个文件单独调用LLM提取SOP - 保证质量
   - 预期效果：预过滤并行处理提升效率，单文件LLM调用保证SOP字段完整性

2. **流水线并行**：
   - 在循环子图中，filter_noise 和 filter_sensitive 并行执行
   - 两者都从 parallel_process 节点出发，利用多核CPU并行处理
   - 预期效果：单文件处理时间减少20-30%

3. **提示词优化**：
   - 精简 extract_sop_cfg.json 中的系统提示词（SP）和用户提示词（UP）
   - 减少冗余描述，保留核心指令和约束
   - 预期效果：Token消耗减少约60%，LLM调用时间减少10-20%
