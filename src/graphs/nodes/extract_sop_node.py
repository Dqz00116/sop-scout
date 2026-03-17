#!/usr/bin/env python3
"""SOP提取节点 - 去扣子版

从过滤敏感信息后的聊天记录中提取结构化的SOP信息
"""

import os
import json
import re
from pathlib import Path
from jinja2 import Template
from src.graphs.state import ExtractSOPInput, ExtractSPOutput
from src.utils.llm_client import SimpleLLMClient


def extract_sop_node(state: ExtractSOPInput) -> ExtractSPOutput:
    """
    title: SOP提取
    desc: 从过滤敏感信息后的聊天记录中提取结构化的SOP信息
    integrations: 大语言模型
    """
    
    # 读取配置文件（使用项目根目录下的 config）
    project_root = Path(__file__).parent.parent.parent.parent
    cfg_file = project_root / "config" / "extract_sop_cfg.json"
    
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 使用jinja2模板渲染提示词
    up_tpl = Template(up)
    user_prompt_content = up_tpl.render({"filtered_content": state.filtered_content})
    
    # 初始化简化版LLM客户端
    client = SimpleLLMClient()
    
    # 调用LLM（使用标准消息格式）
    messages = [
        {"role": "system", "content": sp},
        {"role": "user", "content": user_prompt_content}
    ]
    
    # 获取模型配置（使用 Moonshot K2 系列作为默认）
    model = llm_config.get("model", "kimi-k2-0711-preview")
    temperature = llm_config.get("temperature", 0.3)
    max_tokens = llm_config.get("max_completion_tokens", 16384)
    
    response_text = client.invoke(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
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
        return []
    except json.JSONDecodeError:
        # 尝试正则提取JSON数组
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return data if isinstance(data, list) else [data]
            except:
                pass
        return []
