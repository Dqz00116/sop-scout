import os
import json
import re
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from graphs.state import ExtractSOPInput, ExtractSPOutput

def extract_sop_node(state: ExtractSOPInput, config: RunnableConfig, runtime: Runtime[Context]) -> ExtractSPOutput:
    """
    title: SOP提取
    desc: 从过滤敏感信息后的聊天记录中提取结构化的SOP信息
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 从config的metadata读取配置文件路径
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 使用jinja2模板渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"filtered_content": state.filtered_content})
    
    # 初始化LLM客户端
    client = LLMClient(ctx=ctx)
    
    # 调用LLM
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt_content)
    ]
    
    response = client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.7),
        max_completion_tokens=llm_config.get("max_completion_tokens", 32768),
        thinking=llm_config.get("thinking", "disabled")
    )
    
    # 安全提取文本内容
    def get_text_content(content):
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            if content and isinstance(content[0], str):
                return " ".join(content)
            else:
                return " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
        return str(content)
    
    response_text = get_text_content(response.content)
    
    # 解析JSON响应
    try:
        sop_list = json.loads(response_text)
        if not isinstance(sop_list, list):
            sop_list = [sop_list]
    except json.JSONDecodeError:
        # 如果JSON解析失败，尝试提取JSON部分
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                sop_list = json.loads(json_match.group())
            except:
                sop_list = []
        else:
            sop_list = []
    
    return ExtractSPOutput(sop_list=sop_list)
