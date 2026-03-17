from langgraph.graph import StateGraph, END
from graphs.state import (
    LoopGlobalState,
    LoopGraphInput,
    LoopGraphOutput,
    CheckQualityInput, CheckQualityOutput,
    FilterNoiseInput, FilterNoiseOutput,
    FilterSensitiveInput, FilterSensitiveOutput,
    ExtractSOPInput, ExtractSPOutput,
    FilterContactSOPInput, FilterContactSPOutput
)
from graphs.nodes.check_quality_node import check_quality_node
from graphs.nodes.filter_noise_node import filter_noise_node
from graphs.nodes.filter_sensitive_node import filter_sensitive_node
from graphs.nodes.extract_sop_node import extract_sop_node
from graphs.nodes.filter_contact_sop_node import filter_contact_sop_node

# 条件判断函数：根据质量检测结果决定是否继续处理
def should_continue(state: CheckQualityOutput) -> str:
    """
    title: 是否继续处理
    desc: 根据质量检测结果判断是否继续处理该文件
    """
    if state.quality_passed:
        return "继续处理"
    else:
        return "跳过文件"

# 创建子图
def create_loop_graph():
    """创建循环子图，用于处理单个文件"""
    
    # 创建状态图
    builder = StateGraph(
        LoopGlobalState,
        input_schema=LoopGraphInput,
        output_schema=LoopGraphOutput
    )
    
    # 添加节点
    builder.add_node("check_quality", check_quality_node)
    builder.add_node("parallel_process", lambda state: state)  # 并行入口节点，不做任何处理
    builder.add_node("filter_noise", filter_noise_node)
    builder.add_node("filter_sensitive", filter_sensitive_node)
    builder.add_node("extract_sop", extract_sop_node, metadata={"type": "agent", "llm_cfg": "config/extract_sop_cfg.json"})
    builder.add_node("filter_contact_sop", filter_contact_sop_node)
    builder.add_node("skip_file", lambda state: {"sop_list": []})

    # 设置入口点
    builder.set_entry_point("check_quality")

    # 添加条件分支
    builder.add_conditional_edges(
        source="check_quality",
        path=should_continue,
        path_map={
            "继续处理": "parallel_process",
            "跳过文件": "skip_file"
        }
    )

    # 添加后续边（实现流水线并行）
    # filter_noise 和 filter_sensitive 从 parallel_process 分支出来，并行执行
    builder.add_edge("parallel_process", "filter_noise")
    builder.add_edge("parallel_process", "filter_sensitive")

    # extract_sop 等待 filter_sensitive 完成（需要filtered_content）
    builder.add_edge("filter_sensitive", "extract_sop")

    # filter_contact_sop 在 extract_sop 之后（需要sop_list）
    builder.add_edge("extract_sop", "filter_contact_sop")

    # 并行汇聚：所有分支完成后结束
    builder.add_edge(["filter_noise", "filter_contact_sop"], END)
    builder.add_edge("skip_file", END)
    
    # 编译子图
    loop_graph = builder.compile()
    
    return loop_graph

# 创建全局子图实例
loop_graph = create_loop_graph()
