#!/usr/bin/env python3
"""LLM 配置管理模块 - 简化版

用户只需在 extract_sop_cfg.json 中指定 model 名称，
其他配置（provider, api_key_env, base_url, model_id）
自动从 llm_presets.yaml 获取。

使用示例:
    # extract_sop_cfg.json
    {
        "llm": {
            "model": "kimi-k2-turbo"  // 或 "doubao-seed-2-0-pro"
        },
        "generation": { ... },
        "prompt": { ... }
    }
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM 配置数据类"""
    provider: str
    model: str              # 实际模型ID
    model_alias: str        # 用户配置的别名
    api_key: str
    base_url: str
    temperature: float = 0.3
    max_tokens: int = 16384
    top_p: float = 0.9


class LLMConfigManager:
    """LLM 配置管理器 - 简化版"""
    
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "extract_sop_cfg.json"
    PRESETS_PATH = Path(__file__).parent.parent.parent / "config" / "llm_presets.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self._presets = self._load_presets()
        self._config = self._load_config()
    
    def _load_presets(self) -> Dict[str, Any]:
        """加载预设配置"""
        if not self.PRESETS_PATH.exists():
            raise FileNotFoundError(f"Presets file not found: {self.PRESETS_PATH}")
        
        with open(self.PRESETS_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        import json
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _find_model_in_presets(self, model_alias: str) -> Tuple[str, str, Dict]:
        """在 presets 中查找模型
        
        Returns:
            (provider_name, model_id, provider_config)
        """
        for provider_name, provider_config in self._presets.items():
            models = provider_config.get("models", {})
            if model_alias in models:
                model_info = models[model_alias]
                model_id = model_info.get("id", model_alias)
                return provider_name, model_id, provider_config
        
        # 未找到时，尝试使用别名作为完整模型ID，默认使用 moonshot
        raise ValueError(
            f"Model '{model_alias}' not found in presets. "
            f"Available models: {self.list_available_models()}"
        )
    
    def get_llm_config(self) -> LLMConfig:
        """获取解析后的 LLM 配置"""
        llm_config = self._config.get("llm", {})
        gen_config = self._config.get("generation", {})
        
        # 获取模型别名
        model_alias = llm_config.get("model", "kimi-k2-turbo")
        
        # 从 presets 查找模型配置
        provider_name, model_id, provider_config = self._find_model_in_presets(model_alias)
        
        # 获取 API key
        api_key_env = provider_config.get("api_key_env")
        api_key = os.getenv(api_key_env)
        
        if not api_key:
            raise ValueError(
                f"API key not found for provider '{provider_name}'. "
                f"Please set environment variable: {api_key_env}"
            )
        
        # 获取 base_url
        base_url = provider_config.get("base_url")
        
        return LLMConfig(
            provider=provider_name,
            model=model_id,                    # 实际模型ID
            model_alias=model_alias,            # 用户配置的别名
            api_key=api_key,
            base_url=base_url,
            temperature=gen_config.get("temperature", 0.3),
            max_tokens=gen_config.get("max_tokens", 16384),
            top_p=gen_config.get("top_p", 0.9)
        )
    
    def get_prompt_config(self) -> Dict[str, str]:
        """获取提示词配置"""
        prompt_config = self._config.get("prompt", {})
        return {
            "system": prompt_config.get("system", ""),
            "user_template": prompt_config.get("user_template", "")
        }
    
    def list_available_models(self) -> Dict[str, list]:
        """列出可用的模型"""
        result = {}
        for provider_name, provider_config in self._presets.items():
            models = provider_config.get("models", {})
            result[provider_name] = list(models.keys())
        return result
    
    def print_available_models(self):
        """打印可用模型列表"""
        print("Available models:")
        for provider, models in self.list_available_models().items():
            preset = self._presets.get(provider, {})
            print(f"\n  [{preset.get('name', provider)}]")
            for model_alias in models:
                model_info = preset.get("models", {}).get(model_alias, {})
                desc = model_info.get("description", "")
                print(f"    - {model_alias:<25} {desc}")


# 便捷函数
def get_llm_config(config_path: Optional[str] = None) -> LLMConfig:
    """获取 LLM 配置"""
    manager = LLMConfigManager(config_path)
    return manager.get_llm_config()


def get_prompt_config(config_path: Optional[str] = None) -> Dict[str, str]:
    """获取提示词配置"""
    manager = LLMConfigManager(config_path)
    return manager.get_prompt_config()


def list_models(config_path: Optional[str] = None) -> Dict[str, list]:
    """列出可用模型"""
    manager = LLMConfigManager(config_path)
    return manager.list_available_models()


def print_models(config_path: Optional[str] = None):
    """打印可用模型"""
    manager = LLMConfigManager(config_path)
    manager.print_available_models()


if __name__ == "__main__":
    # 测试：列出所有可用模型
    print_models()
