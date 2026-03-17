#!/usr/bin/env python3
"""简化版工作流 - 去扣子版

使用标准 LangGraph，不依赖扣子 SDK
"""

import sys
from langgraph.graph import StateGraph, END
from src.graphs.state import GlobalState, GraphInput, GraphOutput

# 导入去扣子版节点函数
from src.graphs.nodes.extract_files_node import extract_files_node
from src.graphs.nodes.batch_extract_node import batch_extract_node
from src.graphs.nodes.merge_results_node import merge_results_node


def log_progress(message: str):
    """打印进度信息"""
    print(f"[PROGRESS] {message}", file=sys.stderr, flush=True)


def extract_files_with_log(state: GlobalState) -> dict:
    """解压文件并打印进度"""
    from src.graphs.state import ExtractFilesInput
    log_progress("Step 1/4: Extracting files from zip...")
    input_data = ExtractFilesInput(zip_file=state.zip_file)
    result = extract_files_node(input_data)
    file_count = len(result.chat_files)
    log_progress(f"Step 1/4: Extracted {file_count} text file(s)")
    return {"chat_files": result.chat_files}


def batch_extract_with_log(state: GlobalState) -> dict:
    """批量提取并打印进度"""
    from src.graphs.state import ExtractFilesOutput
    log_progress("Step 2/4: Extracting SOP from chat records...")
    input_data = ExtractFilesOutput(chat_files=state.chat_files)
    result = batch_extract_node(input_data)
    return {"all_sops": result.all_sops}


def merge_results_with_log(state: GlobalState) -> dict:
    """合并结果并打印进度"""
    from src.graphs.state import MergeResultsInput
    log_progress("Step 3/4: Merging results to JSONL...")
    input_data = MergeResultsInput(all_sops=state.all_sops)
    result = merge_results_node(input_data)
    file_count = len(result.jsonl_file_urls)
    log_progress(f"Step 3/4: Generated {file_count} JSONL file(s)")
    return {"jsonl_file_urls": result.jsonl_file_urls}


def save_local_node(state: GlobalState) -> dict:
    """保存到本地节点 - 直接返回文件列表"""
    log_progress("Step 4/4: Finalizing output...")
    return {"jsonl_file_urls": state.jsonl_file_urls}


# 创建简化版工作流
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点（包装版带进度日志）
builder.add_node("extract_files", extract_files_with_log)
builder.add_node("batch_extract", batch_extract_with_log)
builder.add_node("merge_results", merge_results_with_log)
builder.add_node("save_local", save_local_node)

# 设置入口点
builder.set_entry_point("extract_files")

# 添加边
builder.add_edge("extract_files", "batch_extract")
builder.add_edge("batch_extract", "merge_results")
builder.add_edge("merge_results", "save_local")
builder.add_edge("save_local", END)

# 编译工作流
simple_graph = builder.compile()
