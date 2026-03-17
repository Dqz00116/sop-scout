# SOP CLI MVP 设计方案

> 基于第一性原则的最小可行产品（MVP）设计

## 一、第一性原则分析

### 1.1 核心需求拆解（不可再拆分）

```
输入: 本地 zip 文件路径
  ↓
处理: 解压 → 提取 SOP（质量检测→过滤→LLM）→ 合并
  ↓
输出: jsonl 文件到指定目录
```

**关键约束**：并行处理必须保留（已存在于 `batch_extract_node` 中）

### 1.2 需求边界

| 范围 | 包含 | 不包含 |
|-----|------|-------|
| 输入 | 本地单个 zip 文件 | HTTP URL、多文件并行 |
| 处理 | 复用现有工作流节点 | 新建处理逻辑 |
| 输出 | 本地 jsonl 文件 | S3 上传、多级目录结构 |
| 并行 | 单文件内多线程（现有） | 多文件进程级并行 |

---

## 二、原方案 vs MVP 方案对比

### 2.1 过度设计识别

| 原方案设计 | 问题 | MVP 改进 |
|-----------|------|---------|
| 两层并行（进程池+线程池） | 复杂度高，调试困难 | 复用现有 `ThreadPoolExecutor`，多文件并行交给 shell |
| Rich/Click 依赖 | 增加安装负担 | 使用标准库 `argparse` + 已有 `tqdm` |
| 多级输出目录结构 | 用户只需 jsonl 文件 | 扁平化输出，直接到指定目录 |
| 新建 `cli_graph.py` | 代码冗余 | 复用现有 graph，仅替换最后一个节点 |
| WSL 主动路径转换 | 过度适配 | Python 自动处理 `/mnt/e/` 路径 |
| 6+ 个 CLI 参数 | 学习成本高 | 仅 4 个核心参数 |

### 2.2 改进收益

| 指标 | 原方案 | MVP 方案 |
|-----|-------|---------|
| 新增文件 | 4+ | 1 |
| 修改现有代码 | 少量 | 1 处（graph.py） |
| 新依赖 | Rich, Click | 0 |
| 预估代码行数 | ~500 | ~100 |
| 实现时间 | 2-3 天 | 2-3 小时 |

---

## 三、MVP 架构设计

### 3.1 文件变更清单

```
src/
├── cli.py              # 新增：CLI 入口文件（约 100 行）
└── graphs/
    └── graph.py        # 修改：添加无上传版本的工作流
```

### 3.2 工作流调整

```python
# 原工作流（HTTP 服务版）
extract_files → batch_extract → merge_results → upload_files → END
                                                  ↓
                                              上传到 S3

# MVP 工作流（CLI 版）
extract_files → batch_extract → merge_results → save_local → END
                                                  ↓
                                              保存到本地目录
```

**变更点**：仅替换最后一个节点 `upload_files` → `save_local`

---

## 四、CLI 接口设计

### 4.1 最简用法

```bash
# 基础用法
python -m src.cli input.zip -o ./output/

# 进阶用法
python -m src.cli input.zip -o ./output/ -c 100 -v
```

### 4.2 参数说明

| 参数 | 短选项 | 类型 | 默认值 | 说明 |
|-----|-------|-----|-------|------|
| `input` | - | string | 必填 | 输入 zip 文件路径 |
| `--output` | `-o` | string | `./output/` | 输出目录 |
| `--concurrency` | `-c` | int | 50 | 并发线程数（覆盖环境变量） |
| `--verbose` | `-v` | flag | False | 详细日志输出 |

### 4.3 输出结构

```bash
$ python -m src.cli 1号.zip -o ./out/

$ ls ./out/
sop_batch_1.jsonl   # 直接输出 jsonl 文件，无嵌套目录
sop_batch_2.jsonl   # 超过 3 万行时自动分割
```

---

## 五、关键实现代码

### 5.1 CLI 入口 (src/cli.py)

```python
#!/usr/bin/env python3
"""SOP Extractor CLI - MVP 版本"""

import argparse
import os
import asyncio
import sys
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.file.file import File
from graphs.graph import main_graph_cli


async def process_zip(zip_path: str, output_dir: str, concurrency: int, verbose: bool):
    """处理单个 zip 文件"""
    
    # 确保路径绝对化
    zip_path = os.path.abspath(zip_path)
    output_dir = os.path.abspath(output_dir)
    
    # 检查输入文件
    if not os.path.exists(zip_path):
        print(f"错误: 文件不存在: {zip_path}", file=sys.stderr)
        sys.exit(1)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置并发数
    os.environ["SOP_CONCURRENCY"] = str(concurrency)
    
    if verbose:
        print(f"处理文件: {zip_path}")
        print(f"输出目录: {output_dir}")
        print(f"并发数: {concurrency}")
    
    try:
        # 调用工作流
        result = await main_graph_cli.ainvoke({
            "zip_file": File(url=zip_path)
        })
        
        # 移动结果文件到输出目录
        jsonl_files = result.get("jsonl_files", [])
        if not jsonl_files:
            print("警告: 未生成任何输出文件", file=sys.stderr)
            return
        
        for src_path in jsonl_files:
            filename = os.path.basename(src_path)
            dst_path = os.path.join(output_dir, filename)
            
            # 如果目标已存在，先删除
            if os.path.exists(dst_path):
                os.remove(dst_path)
            
            shutil.move(src_path, dst_path)
            print(f"✓ {dst_path}")
        
        if verbose:
            print(f"\n完成: 共生成 {len(jsonl_files)} 个文件")
            
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="SOP 提取工具 - 从客服聊天记录中提取结构化 SOP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.cli 1号.zip -o ./output/
  python -m src.cli /mnt/e/data/chat.zip -o ./out/ -c 100 -v
        """
    )
    
    parser.add_argument(
        "input",
        help="输入 zip 文件路径（支持 WSL 路径如 /mnt/e/...）"
    )
    
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="输出目录（默认: ./output）"
    )
    
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=50,
        help="并发线程数（默认: 50）"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    # 运行异步处理
    asyncio.run(process_zip(
        zip_path=args.input,
        output_dir=args.output,
        concurrency=args.concurrency,
        verbose=args.verbose
    ))


if __name__ == "__main__":
    main()
```

### 5.2 工作流调整 (src/graphs/graph.py)

```python
from langgraph.graph import StateGraph, END
from graphs.state import GlobalState, GraphInput, GraphOutput
from graphs.nodes.extract_files_node import extract_files_node
from graphs.nodes.batch_extract_node import batch_extract_node
from graphs.nodes.merge_results_node import merge_results_node


# ========== HTTP 服务版（原） ==========
from graphs.nodes.upload_files_node import upload_files_node

builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)
builder.add_node("extract_files", extract_files_node)
builder.add_node("batch_extract", batch_extract_node)
builder.add_node("merge_results", merge_results_node)
builder.add_node("upload_files", upload_files_node)

builder.set_entry_point("extract_files")
builder.add_edge("extract_files", "batch_extract")
builder.add_edge("batch_extract", "merge_results")
builder.add_edge("merge_results", "upload_files")
builder.add_edge("upload_files", END)

main_graph = builder.compile()


# ========== CLI 版（新增） ==========
def save_local_node(state, config, runtime):
    """
    title: 保存到本地
    desc: 将生成的 JSONL 文件路径直接返回，由 CLI 负责移动
    """
    return {"jsonl_files": state.jsonl_files}

builder_cli = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)
builder_cli.add_node("extract_files", extract_files_node)
builder_cli.add_node("batch_extract", batch_extract_node)
builder_cli.add_node("merge_results", merge_results_node)
builder_cli.add_node("save_local", save_local_node)

builder_cli.set_entry_point("extract_files")
builder_cli.add_edge("extract_files", "batch_extract")
builder_cli.add_edge("batch_extract", "merge_results")
builder_cli.add_edge("merge_results", "save_local")
builder_cli.add_edge("save_local", END)

main_graph_cli = builder_cli.compile()
```

---

## 六、并行策略

### 6.1 单文件内并行（内置）

复用现有的 `batch_extract_node` 中的 `ThreadPoolExecutor`：

```python
# 已有实现，无需修改
with ThreadPoolExecutor(max_workers=concurrency) as executor:
    # 分批提交任务
    for batch_index in range(0, len(chat_files), batch_size):
        future = executor.submit(process_batch, ...)
```

### 6.2 多文件并行（外部）

CLI 保持单文件处理，多文件并行交给外部工具：

```bash
# 方法 1：GNU parallel（推荐）
ls *.zip | parallel -j 4 "python -m src.cli {} -o ./out/{/.}/"

# 方法 2：xargs
ls *.zip | xargs -P 4 -I {} python -m src.cli {} -o ./out/{}

# 方法 3：shell 循环后台执行
for f in *.zip; do
    python -m src.cli "$f" -o "./out/${f%.zip}/" &
done
wait
```

**设计理由**：
- 外部工具更成熟，可控性更强
- CLI 保持简单，单职责原则
- 用户可根据需求选择并行度

---

## 七、WSL2 适配说明

### 7.1 路径处理

Python 自动处理 WSL 路径，无需额外代码：

```bash
# Windows 风格路径（PowerShell/CMD）
python -m src.cli E:\data\1号.zip -o E:\output\

# WSL 风格路径（Bash）
python -m src.cli /mnt/e/data/1号.zip -o /mnt/e/output/

# 相对路径
python -m src.cli ./data/1号.zip -o ./output/
```

### 7.2 环境检测

```bash
# 检测是否在 WSL 中
if grep -q Microsoft /proc/version; then
    echo "Running in WSL"
fi
```

---

## 八、使用示例

### 8.1 基础用法

```bash
# 进入项目目录
cd /mnt/e/Agent/sop-linux

# 激活虚拟环境
source sop/bin/activate

# 处理单个文件
python -m src.cli assets/1号.zip -o ./output/

# 查看输出
ls ./output/
# sop_batch_1.jsonl
```

### 8.2 批量处理

```bash
# 创建输出目录
mkdir -p ./output

# 顺序处理
for f in assets/*.zip; do
    name=$(basename "$f" .zip)
    python -m src.cli "$f" -o "./output/$name/"
done

# 或并行处理（4 个并发）
ls assets/*.zip | parallel -j 4 "python -m src.cli {} -o ./output/{/.}/"
```

### 8.3 调试模式

```bash
python -m src.cli assets/1号.zip -o ./output/ -v
```

---

## 九、测试计划

### 9.1 功能测试

| 测试项 | 命令 | 预期结果 |
|-------|------|---------|
| 基本提取 | `python -m src.cli 1号.zip -o ./out/` | 生成 jsonl 文件 |
| 并发调整 | `-c 100` | 处理速度提升 |
| 详细日志 | `-v` | 显示处理过程 |
| 无效路径 | `python -m src.cli nonexistent.zip` | 错误提示，退出码 1 |
| WSL 路径 | `/mnt/e/.../1号.zip` | 正常处理 |

### 9.2 性能测试

```bash
# 测试不同并发数
time python -m src.cli 1号.zip -o ./out/ -c 10
time python -m src.cli 1号.zip -o ./out/ -c 50
time python -m src.cli 1号.zip -o ./out/ -c 100
```

---

## 十、后续扩展（非 MVP）

| 功能 | 优先级 | 说明 |
|-----|-------|------|
| 多文件内置并行 | P2 | CLI 内添加进程池 |
| 进度条显示 | P2 | 集成 tqdm 到工作流 |
| 配置文件支持 | P3 | 支持 YAML/JSON 配置 |
| 安装为系统命令 | P3 | `pip install -e .` 后使用 `sop-extract` |
| 输出格式选项 | P3 | 支持 JSON/CSV |

---

## 十一、实施检查清单

- [ ] 修改 `src/graphs/graph.py` 添加 `main_graph_cli`
- [ ] 创建 `src/cli.py` 入口文件
- [ ] 测试单个 zip 文件处理
- [ ] 测试并发参数生效
- [ ] 测试 WSL 路径兼容
- [ ] 测试错误处理（无效路径等）
- [ ] 更新 README.md 添加 CLI 使用说明

---

**文档版本**: 1.0  
**创建时间**: 2026-03-17  
**适用范围**: sop-linux MVP CLI 改造
