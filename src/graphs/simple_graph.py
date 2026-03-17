#!/usr/bin/env python3
"""简化版工作流 - 去扣子版

使用标准 LangGraph，不依赖扣子 SDK
"""

from langgraph.graph import StateGraph, END
from src.graphs.state import GlobalState, GraphInput, GraphOutput

# 导入去扣子版节点函数
from src.graphs.nodes.extract_files_node import extract_files_node
from src.graphs.nodes.batch_extract_node import batch_extract_node
from src.graphs.nodes.merge_results_node import merge_results_node


def save_local_node(state: GlobalState) -> dict:
    """保存到本地节点 - 直接返回文件列表"""
    return {"jsonl_file_urls": state.jsonl_file_urls}


# 创建简化版工作流
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
builder.add_node("extract_files", extract_files_node)
builder.add_node("batch_extract", batch_extract_node)
builder.add_node("merge_results", merge_results_node)
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
