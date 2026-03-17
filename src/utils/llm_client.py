#!/usr/bin/env python3
"""LLM 客户端 - 支持多 Provider（Moonshot / Doubao / OpenAI）

使用示例:
    # 方式1：通过配置管理器
    config = get_llm_config()
    client = LLMClient.from_config(config)
    
    # 方式2：手动创建
    client = LLMClient(
        provider="doubao",
        api_key="sk-xxx",
        base_url="https://ark.cn-beijing.volces.com/api/v3"
    )
    
    # 调用
    response = client.invoke(
        messages=[{"role": "user", "content": "你好"}],
        model="doubao-seed-2-0-pro-260215"
    )
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI
from enum import Enum

from src.utils.llm_config import LLMConfig, get_llm_config


class Provider(str, Enum):
    """支持的 LLM Provider"""
    MOONSHOT = "moonshot"
    DOUBAO = "doubao"
    OPENAI = "openai"


class LLMClient:
    """通用 LLM 客户端"""
    
    def __init__(
        self,
        provider: str = "moonshot",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None
    ):
        """初始化客户端
        
        Args:
            provider: Provider 名称 (moonshot/doubao/openai)
            api_key: API 密钥，默认从环境变量读取
            base_url: API 基础 URL
            default_model: 默认模型名称
        """
        self.provider = Provider(provider)
        
        # 获取 API key
        if api_key is None:
            api_key = self._get_api_key_from_env()
        
        if not api_key:
            raise ValueError(
                f"API key is required for provider '{provider}'. "
                f"Set environment variable or pass api_key parameter."
            )
        
        # 获取 base_url
        if base_url is None:
            base_url = self._get_default_base_url()
        
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model
        
        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取 API key"""
        env_vars = {
            Provider.MOONSHOT: ["LLM_API_KEY", "MOONSHOT_API_KEY"],
            Provider.DOUBAO: ["ARK_API_KEY", "DOUBAO_API_KEY"],
            Provider.OPENAI: ["OPENAI_API_KEY"]
        }
        
        for var in env_vars.get(self.provider, []):
            value = os.getenv(var)
            if value:
                return value
        return None
    
    def _get_default_base_url(self) -> str:
        """获取默认 base URL"""
        defaults = {
            Provider.MOONSHOT: "https://api.moonshot.cn/v1",
            Provider.DOUBAO: "https://ark.cn-beijing.volces.com/api/v3",
            Provider.OPENAI: "https://api.openai.com/v1"
        }
        return defaults.get(self.provider, "https://api.moonshot.cn/v1")
    
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
            messages: 消息列表，格式 [{"role": "system"|"user"|"assistant", "content": str}]
            model: 模型名称，默认使用配置中的模型
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            top_p: Top-p 采样参数
            **kwargs: 其他参数
            
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
    
    def invoke_responses(
        self,
        input_data: Union[str, List[Dict]],
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 LLM (responses API - 支持多模态)
        
        Args:
            input_data: 输入内容，可以是字符串或消息列表
            model: 模型名称
            **kwargs: 其他参数
            
        Returns:
            LLM 生成的文本内容
        """
        model = model or self.default_model
        if not model:
            raise ValueError("Model name is required")
        
        try:
            # 构建 input 参数
            if isinstance(input_data, str):
                input_param = [{"role": "user", "content": input_data}]
            else:
                input_param = input_data
            
            response = self.client.responses.create(
                model=model,
                input=input_param,
                **kwargs
            )
            
            # 从 response 中提取文本
            if hasattr(response, 'output_text'):
                return response.output_text
            elif hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content
            else:
                return str(response)
            
        except Exception as e:
            # 如果 responses API 不支持，回退到 chat.completions
            if "responses" in str(e).lower():
                # 转换为标准消息格式
                if isinstance(input_data, list) and len(input_data) > 0:
                    content = input_data[0].get("content", "")
                    if isinstance(content, list):
                        # 提取文本内容
                        text_parts = [
                            item.get("text", "") 
                            for item in content 
                            if isinstance(item, dict) and item.get("type") == "input_text"
                        ]
                        text = " ".join(text_parts)
                    else:
                        text = str(content)
                else:
                    text = str(input_data)
                
                return self.invoke(
                    messages=[{"role": "user", "content": text}],
                    model=model,
                    **{k: v for k, v in kwargs.items() if k in ['temperature', 'max_tokens', 'top_p']}
                )
            raise RuntimeError(f"LLM API call failed: {e}")
    
    def invoke_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 16384,
        **kwargs
    ) -> Any:
        """调用 LLM 并解析 JSON 响应
        
        Returns:
            解析后的 JSON 对象
        """
        content = self.invoke(messages, model, temperature, max_tokens, **kwargs)
        return self._parse_json_response(content)
    
    @staticmethod
    def _parse_json_response(response_text: str) -> Any:
        """解析 JSON 响应（处理 markdown 代码块）"""
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
            return data
        except json.JSONDecodeError:
            # 尝试正则提取 JSON 数组
            import re
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
def create_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMClient:
    """创建 LLM 客户端
    
    Args:
        provider: 指定 provider，默认从配置读取
        api_key: API key，默认从环境变量读取
        base_url: Base URL，默认从配置或预设读取
    """
    if provider is None:
        # 尝试从配置读取
        try:
            config = get_llm_config()
            return LLMClient.from_config(config)
        except:
            # 默认使用 moonshot
            return LLMClient(provider="moonshot", api_key=api_key, base_url=base_url)
    
    return LLMClient(provider=provider, api_key=api_key, base_url=base_url)
