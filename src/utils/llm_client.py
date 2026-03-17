#!/usr/bin/env python3
"""简化版 LLM 客户端 - 替换扣子 LLMClient

支持标准 OpenAI 格式 API（Moonshot / OpenAI / 兼容接口）
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI


class SimpleLLMClient:
    """简化版 LLM 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """初始化客户端
        
        Args:
            api_key: API 密钥，默认从环境变量 LLM_API_KEY 读取
            base_url: API 基础 URL，默认从环境变量 LLM_BASE_URL 读取
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        
        if not self.api_key:
            raise ValueError("API key is required. Set LLM_API_KEY environment variable.")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def invoke(
        self,
        messages: List[Dict[str, str]],
        model: str = "kimi-k2-0711-preview",
        temperature: float = 0.3,
        max_tokens: Optional[int] = 16384,
        **kwargs
    ) -> str:
        """调用 LLM
        
        Args:
            messages: 消息列表，格式 [{"role": "system"|"user"|"assistant", "content": str}]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            LLM 生成的文本内容
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            return content if content else ""
            
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")
    
    def invoke_json(
        self,
        messages: List[Dict[str, str]],
        model: str = "kimi-k2-0711-preview",
        temperature: float = 0.3,
        max_tokens: Optional[int] = 16384,
        **kwargs
    ) -> Any:
        """调用 LLM 并解析 JSON 响应
        
        Returns:
            解析后的 JSON 对象
        """
        content = self.invoke(messages, model, temperature, max_tokens, **kwargs)
        
        # 尝试提取 JSON 内容（处理 markdown 代码块）
        content = content.strip()
        
        # 处理 ```json ... ``` 格式
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse LLM response as JSON: {e}\nContent: {content[:500]}")


# 便捷函数：创建默认客户端实例
def get_default_client() -> SimpleLLMClient:
    """获取默认配置的客户端实例"""
    return SimpleLLMClient()
