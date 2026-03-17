#!/usr/bin/env python3
"""LLM 客户端 - 支持多 Provider（Moonshot / Doubao / OpenAI）

配置方式:
    1. 在 config/extract_sop_cfg.json 中设置 llm.model
    2. 模型信息自动从 config/llm_presets.yaml 获取
    3. API key 从对应的环境变量读取

使用示例:
    from src.utils.llm_client import LLMClient
    from src.utils.llm_config import get_llm_config
    
    config = get_llm_config()
    client = LLMClient.from_config(config)
    
    response = client.invoke(messages=[...])
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI

from src.utils.llm_config import LLMConfig, get_llm_config


class LLMClient:
    """通用 LLM 客户端"""
    
    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        default_model: Optional[str] = None
    ):
        """初始化客户端
        
        Args:
            provider: Provider 名称 (moonshot/doubao/openai)
            api_key: API 密钥
            base_url: API 基础 URL
            default_model: 默认模型名称
        """
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        
        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    @classmethod
    def from_config(cls, config: LLMConfig) -> "LLMClient":
        """从配置对象创建客户端"""
        return cls(
            provider=config.provider,
            api_key=config.api_key,
            base_url=config.base_url,
            default_model=config.model
        )
    
    @classmethod
    def from_default_config(cls) -> "LLMClient":
        """从默认配置创建客户端"""
        config = get_llm_config()
        return cls.from_config(config)
    
    def invoke(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 16384,
        top_p: float = 0.9,
        **kwargs
    ) -> str:
        """调用 LLM (chat.completions API)
        
        Args:
            messages: 消息列表
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            top_p: Top-p 采样参数
            
        Returns:
            LLM 生成的文本内容
        """
        model = model or self.default_model
        if not model:
            raise ValueError("Model name is required")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                **kwargs
            )
            
            content = response.choices[0].message.content
            return content if content else ""
            
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")
    
    def invoke_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 16384,
        **kwargs
    ) -> Any:
        """调用 LLM 并解析 JSON 响应"""
        content = self.invoke(messages, model, temperature, max_tokens, **kwargs)
        return self._parse_json_response(content)
    
    @staticmethod
    def _parse_json_response(response_text: str) -> Any:
        """解析 JSON 响应（处理 markdown 代码块）"""
        if not response_text:
            return []
        
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            # 尝试提取 JSON 数组
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            # 尝试提取 JSON 对象
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            raise RuntimeError(f"Failed to parse response as JSON: {text[:500]}")


# 便捷函数
def create_client() -> LLMClient:
    """创建 LLM 客户端（从默认配置）"""
    return LLMClient.from_default_config()
