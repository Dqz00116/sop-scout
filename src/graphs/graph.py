from langgraph.graph import StateGraph, END
from graphs.state import GlobalState, GraphInput, GraphOutput
from graphs.nodes.extract_files_node import extract_files_node
from graphs.nodes.batch_extract_node import batch_extract_node
from graphs.nodes.merge_results_node import merge_results_node
from graphs.nodes.upload_files_node import upload_files_node

# ========== HTTP 服务版（原） ==========
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
    return {"jsonl_file_urls": state.jsonl_file_urls}

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
