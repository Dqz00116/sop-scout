#!/usr/bin/env python3
"""LLM 配置管理模块

支持多 Provider 配置：Moonshot、Doubao、OpenAI 等
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM 配置数据类"""
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.3
    max_tokens: int = 16384
    top_p: float = 0.9
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class ConfigResolver:
    """配置解析器 - 支持环境变量引用 ${ENV_VAR}"""
    
    ENV_PATTERN = re.compile(r'\$\{(\w+)\}')
    
    @classmethod
    def resolve(cls, value: str) -> str:
        """解析字符串中的环境变量引用"""
        if not isinstance(value, str):
            return value
        
        def replace_env(match):
            env_var = match.group(1)
            env_value = os.getenv(env_var)
            if env_value is None:
                raise ValueError(f"Environment variable '{env_var}' not found")
            return env_value
        
        return cls.ENV_PATTERN.sub(replace_env, value)
    
    @classmethod
    def resolve_dict(cls, data: Dict) -> Dict:
        """递归解析字典中的所有字符串值"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.resolve(value)
            elif isinstance(value, dict):
                result[key] = cls.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    cls.resolve_dict(item) if isinstance(item, dict) 
                    else cls.resolve(item) if isinstance(item, str) 
                    else item 
                    for item in value
                ]
            else:
                result[key] = value
        return result


class LLMConfigManager:
    """LLM 配置管理器"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "extract_sop_cfg.json"
    PRESETS_PATH = Path(__file__).parent.parent.parent / "config" / "llm_presets.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self._presets = self._load_presets()
        self._config = self._load_config()
    
    def _load_presets(self) -> Dict[str, Any]:
        """加载预设配置"""
        if not self.PRESETS_PATH.exists():
            return {}
        
        with open(self.PRESETS_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        import json
        
        if not self.config_path.exists():
            return self._get_default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 兼容旧配置格式
        if "llm" not in config:
            config = self._migrate_old_config(config)
        
        return config
    
    def _migrate_old_config(self, old_config: Dict) -> Dict:
        """迁移旧版配置到新格式"""
        new_config = {
            "llm": {
                "provider": "moonshot",
                "model": old_config.get("config", {}).get("model", "kimi-k2-turbo-preview"),
                "api_key": "${LLM_API_KEY}",
                "base_url": "https://api.moonshot.cn/v1"
            },
            "generation": {
                "temperature": old_config.get("config", {}).get("temperature", 0.3),
                "max_tokens": old_config.get("config", {}).get("max_completion_tokens", 16384),
                "top_p": old_config.get("config", {}).get("top_p", 0.9)
            },
            "prompt": {
                "system": old_config.get("sp", ""),
                "user_template": old_config.get("up", "")
            }
        }
        return new_config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "llm": {
                "provider": "moonshot",
                "model": "kimi-k2-turbo-preview",
                "api_key": "${LLM_API_KEY}",
                "base_url": "https://api.moonshot.cn/v1"
            },
            "generation": {
                "temperature": 0.3,
                "max_tokens": 16384,
                "top_p": 0.9
            },
            "prompt": {
                "system": "",
                "user_template": ""
            }
        }
    
    def get_llm_config(self) -> LLMConfig:
        """获取解析后的 LLM 配置"""
        llm_config = self._config.get("llm", {})
        gen_config = self._config.get("generation", {})
        
        # 解析环境变量
        resolved = ConfigResolver.resolve_dict(llm_config)
        
        # 获取 API key（优先从环境变量）
        provider = resolved.get("provider", "moonshot")
        preset = self._presets.get(provider, {})
        
        api_key_env = preset.get("api_key_env", f"{provider.upper()}_API_KEY")
        api_key = resolved.get("api_key") or os.getenv(api_key_env)
        
        if not api_key:
            raise ValueError(
                f"API key not found for provider '{provider}'. "
                f"Set {api_key_env} environment variable or configure 'api_key' in config."
            )
        
        # 获取 base_url
        base_url = resolved.get("base_url") or preset.get("base_url")
        
        return LLMConfig(
            provider=provider,
            model=resolved.get("model", "kimi-k2-turbo-preview"),
            api_key=api_key,
            base_url=base_url,
            temperature=gen_config.get("temperature", 0.3),
            max_tokens=gen_config.get("max_tokens", 16384),
            top_p=gen_config.get("top_p", 0.9),
            extra_params=llm_config.get("extra_params", {})
        )
    
    def get_prompt_config(self) -> Dict[str, str]:
        """获取提示词配置"""
        prompt_config = self._config.get("prompt", {})
        return {
            "system": prompt_config.get("system", ""),
            "user_template": prompt_config.get("user_template", "")
        }
    
    def list_available_models(self, provider: Optional[str] = None) -> Dict[str, list]:
        """列出可用的模型"""
        if provider:
            preset = self._presets.get(provider, {})
            return {provider: list(preset.get("models", {}).keys())}
        
        return {
            name: list(preset.get("models", {}).keys())
            for name, preset in self._presets.items()
        }


# 便捷函数
def get_llm_config(config_path: Optional[str] = None) -> LLMConfig:
    """获取 LLM 配置"""
    manager = LLMConfigManager(config_path)
    return manager.get_llm_config()


def get_prompt_config(config_path: Optional[str] = None) -> Dict[str, str]:
    """获取提示词配置"""
    manager = LLMConfigManager(config_path)
    return manager.get_prompt_config()
