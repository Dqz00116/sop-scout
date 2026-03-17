import os
import json
import tempfile
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import MergeResultsInput, MergeResultsOutput

def merge_results_node(state: MergeResultsInput, config: RunnableConfig, runtime: Runtime[Context]) -> MergeResultsOutput:
    """
    title: 聚合结果
    desc: 将所有提取的SOP聚合为符合火山引擎知识库格式的JSONL文件
    integrations: 
    """
    ctx = runtime.context
    
    # 火山引擎知识库格式限制
    MAX_LINES_PER_FILE = 30000
    MAX_CHARS_PER_LINE = 65535
    
    accumulated_sops = []
    jsonl_files = []
    file_index = 1
    
    for sop in state.all_sops:
        # 转换为火山引擎知识库格式
        sop_obj = {
            "id": sop.get("id", ""),
            "category": sop.get("category", ""),
            "subcategory": sop.get("subcategory", ""),
            "when": {
                "scenario": sop.get("when", {}).get("scenario", ""),
                "keywords": sop.get("when", {}).get("keywords", []),
                "user_queries": sop.get("when", {}).get("user_queries", [])
            },
            "then": {
                "actions": sop.get("then", {}).get("actions", []),
                "response": sop.get("then", {}).get("response", "")
            },
            "notes": sop.get("notes", ""),
            "source": sop.get("source", "")
        }
        
        # 检查单行字符数是否超过限制
        json_line = json.dumps(sop_obj, ensure_ascii=False)
        if len(json_line) > MAX_CHARS_PER_LINE:
            json_line = json_line[:MAX_CHARS_PER_LINE-3] + "..."
        
        accumulated_sops.append(sop_obj)
        
        # 检查是否达到文件行数限制
        if len(accumulated_sops) >= MAX_LINES_PER_FILE:
            jsonl_file_path = _save_jsonl_file(accumulated_sops, file_index)
            jsonl_files.append(jsonl_file_path)
            accumulated_sops = []
            file_index += 1
    
    # 保存剩余的SOP
    if accumulated_sops:
        jsonl_file_path = _save_jsonl_file(accumulated_sops, file_index)
        jsonl_files.append(jsonl_file_path)
    
    return MergeResultsOutput(jsonl_files=jsonl_files)

def _save_jsonl_file(sops, file_index):
    """保存JSONL文件"""
    jsonl_lines = []
    for sop in sops:
        json_line = json.dumps(sop, ensure_ascii=False)
        jsonl_lines.append(json_line)

    jsonl_content = "\n".join(jsonl_lines)

    # 使用系统临时目录（跨平台兼容）
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, f"sop_batch_{file_index}.jsonl")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(jsonl_content)

    return file_path
