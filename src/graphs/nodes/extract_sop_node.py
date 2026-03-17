#!/usr/bin/env python3
"""SOP提取节点 - 支持多 LLM Provider

从过滤敏感信息后的聊天记录中提取结构化的SOP信息
"""

import json
from pathlib import Path
from jinja2 import Template

from src.graphs.state import ExtractSOPInput, ExtractSPOutput
from src.utils.llm_client import LLMClient
from src.utils.llm_config import get_llm_config, get_prompt_config


def extract_sop_node(state: ExtractSOPInput) -> ExtractSPOutput:
    """
    title: SOP提取
    desc: 从过滤敏感信息后的聊天记录中提取结构化的SOP信息
    integrations: 大语言模型
    """
    
    # 加载配置
    llm_config = get_llm_config()
    prompt_config = get_prompt_config()
    
    # 获取提示词
    sp = prompt_config["system"]
    up_template = prompt_config["user_template"]
    
    # 渲染用户提示词
    up_tpl = Template(up_template)
    user_prompt_content = up_tpl.render({"filtered_content": state.filtered_content})
    
    # 初始化LLM客户端
    client = LLMClient.from_config(llm_config)
    
    # 构建消息
    messages = [
        {"role": "system", "content": sp},
        {"role": "user", "content": user_prompt_content}
    ]
    
    # 调用LLM
    response_text = client.invoke(
        messages=messages,
        model=llm_config.model,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
        top_p=llm_config.top_p
    )
    
    # 解析JSON响应
    sop_list = _parse_sop_response(response_text)
    
    return ExtractSPOutput(sop_list=sop_list)


def _parse_sop_response(response_text: str) -> list:
    """解析LLM响应中的SOP列表
    
    Args:
        response_text: LLM返回的文本
        
    Returns:
        SOP列表，解析失败返回空列表
    """
    if not response_text:
        return []
    
    # 清理 markdown 代码块
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
    except json.JSONDecodeError:
        # 尝试正则提取JSON数组
        import re
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data if isinstance(data, list) else [data]
            except:
                pass
    
    return []
