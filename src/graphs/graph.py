from langgraph.graph import StateGraph, END
from graphs.state import GlobalState, GraphInput, GraphOutput
from graphs.nodes.extract_files_node import extract_files_node
from graphs.nodes.batch_extract_node import batch_extract_node
from graphs.nodes.merge_results_node import merge_results_node
from graphs.nodes.upload_files_node import upload_files_node

# 创建状态图，指定工作流的入参和出参
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# 添加节点
builder.add_node("extract_files", extract_files_node)
builder.add_node("batch_extract", batch_extract_node)
builder.add_node("merge_results", merge_results_node)
builder.add_node("upload_files", upload_files_node)

# 设置入口点
builder.set_entry_point("extract_files")

# 添加边
builder.add_edge("extract_files", "batch_extract")
builder.add_edge("batch_extract", "merge_results")
builder.add_edge("merge_results", "upload_files")
builder.add_edge("upload_files", END)

# 编译图
main_graph = builder.compile()
