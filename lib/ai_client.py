#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一 Chat Client - 支持多个 AI 供应商
支持的供应商: deepseek, zhipu, openrouter, qwen, realmrouter, kimi, qiniu

使用前请在 ~/.local/clawos/ai_client_config.json 中配置 API Key，格式:
{
    "deepseek": "your-api-key",
    "zhipu": "your-api-key",
    ...
}

或设置环境变量: DEEPSEEK_API_KEY, ZHIPU_API_KEY 等
"""

import os
import json
import requests
import argparse
import time
from zhipuai import ZhipuAI
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image
import numpy as np

# 配置文件路径
_CONFIG_FILE = os.path.expanduser("~/.local/clawos/ai_client_config.json")

def _read_config_file():
    config = {}
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f) or {}
        except:
            config = {}
    return config

def load_provider_models():
    cfg = _read_config_file()
    providers_cfg = cfg.get("providers") if isinstance(cfg, dict) else None
    if not isinstance(providers_cfg, dict):
        providers_cfg = cfg if isinstance(cfg, dict) else {}

    provider_models = {k: dict(v) for k, v in PROVIDOR_MODELS.items()}

    for provider in list(provider_models.keys()):
        value = providers_cfg.get(provider)
        if isinstance(value, str):
            provider_models[provider]["api_key"] = value
            continue
        if isinstance(value, dict):
            if "engine" in value:
                provider_models[provider]["engine"] = value.get("engine", "") or provider_models[provider].get("engine", "")
            if "base_url" in value:
                provider_models[provider]["base_url"] = value.get("base_url", "") or provider_models[provider].get("base_url", "")
            if "api_key" in value:
                provider_models[provider]["api_key"] = value.get("api_key", "") or ""
            if "models" in value:
                models = value.get("models", [])
                provider_models[provider]["models"] = models if isinstance(models, list) else []
            if "extra_headers" in value and isinstance(value.get("extra_headers"), dict):
                provider_models[provider]["extra_headers"] = value.get("extra_headers", {})

    for provider, value in providers_cfg.items():
        if provider in provider_models:
            continue
        if isinstance(value, str):
            provider_models[provider] = {"engine": "openai-api", "base_url": "", "api_key": value, "models": []}
        elif isinstance(value, dict):
            provider_models[provider] = {
                "engine": value.get("engine", "openai-api"),
                "base_url": value.get("base_url", ""),
                "api_key": value.get("api_key", ""),
                "models": value.get("models", []) if isinstance(value.get("models", []), list) else [],
            }
            if isinstance(value.get("extra_headers"), dict):
                provider_models[provider]["extra_headers"] = value.get("extra_headers", {})

    return provider_models

def save_provider_models(provider_models: dict):
    os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
    with open(_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump({"providers": provider_models}, f, ensure_ascii=False, indent=2)

def _get_api_key(provider: str) -> str:
    """获取 API Key，优先使用配置文件，其次环境变量"""
    cfg = _read_config_file()
    if isinstance(cfg, dict):
        providers_cfg = cfg.get("providers") if isinstance(cfg.get("providers"), dict) else cfg
        if isinstance(providers_cfg, dict) and provider in providers_cfg:
            value = providers_cfg.get(provider)
            if isinstance(value, str) and value:
                return value
            if isinstance(value, dict) and value.get("api_key"):
                return value.get("api_key", "")
    # 其次环境变量
    env_key = f"{provider.upper()}_API_KEY"
    return os.getenv(env_key, "")

PROVIDOR_MODELS = {}


class AiClient:
    """统一的 Chat 客户端，支持多个 AI 供应商"""
    
    SUPPORTED_PROVIDERS = list(PROVIDOR_MODELS.keys())
    SUPPORTED_ENGINES = ["openai-api", "openai-sdk", "zhipu-sdk"]
    
    def __init__(self, provider_model='deepseek:deepseek-chat', api_key: str | None = None, base_url: str | None = None):
        """
        初始化 Chat 客户端
        
        Args:
            provider_model (str): AI 供应商和模型，格式: '{provider}:{model}'，例如 'deepseek:deepseek-chat'
        """
        provider_model = (provider_model or "").strip()
        if ":" in provider_model:
            provider, model = provider_model.split(":", 1)
        else:
            provider = provider_model
            model = None
        
        # 获取供应商配置
        provider = provider.lower()
        provider_models = load_provider_models()
        if provider not in provider_models:
            raise ValueError(f"不支持的供应商: {provider}，支持的供应商: {', '.join(provider_models.keys())}")
        
        provider_config = provider_models[provider]
        
        # 获取 API Key（参数 > 环境变量/配置文件）
        self.api_key = (api_key or "").strip() or _get_api_key(provider) or provider_config.get("api_key", "")
        
        # 如果没有 API Key，尝试从旧版配置文件读取
        if not self.api_key:
            legacy_config_file = os.path.expanduser("~/.local/clawos/config.json")
            if os.path.exists(legacy_config_file):
                try:
                    with open(legacy_config_file, 'r') as f:
                        legacy = json.load(f)
                        self.api_key = legacy.get("api_key", "")
                except:
                    pass
        
        if not self.api_key:
            print(f"警告: 未找到 {provider} 的 API Key，请配置后重试")
        
        # 获取 base_url
        self.base_url = (base_url or "").strip() or provider_config.get("base_url", "")
        
        # 获取模型
        if model:
            self.model = model
        else:
            models = provider_config.get("models", []) or []
            if not models:
                raise ValueError(f"{provider} 未配置可用模型，请在 {_CONFIG_FILE} 中设置 models")
            self.model = models[0]
        self.engine = provider_config.get("engine", "openai-api")
        
        # 初始化客户端
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """根据引擎初始化客户端"""
        if self.engine == "zhipu-sdk":
            if self.api_key:
                self.client = ZhipuAI(api_key=self.api_key)
        elif self.engine in ["openai-api", "openai-sdk"]:
            if self.api_key and self.base_url:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
    
    def chat(self, messages: list, temperature: float = 0.7, **kwargs):
        """
        发送聊天请求
        
        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}]
            temperature: 温度参数
            **kwargs: 其他参数
        
        Returns:
            响应文本或流式响应
        """
        if not self.client:
            raise RuntimeError("客户端未初始化，请检查 API Key")
        
        extra_params = {}
        if "stream" in kwargs and kwargs["stream"]:
            extra_params["stream"] = True
        
        if self.engine == "zhipu-sdk":
            # 智谱 SDK
            # 转换消息格式
            glm_messages = []
            for msg in messages:
                role = msg.get("role", "user")
                if role == "system":
                    role = "system"
                elif role == "assistant":
                    role = "assistant"
                else:
                    role = "user"
                glm_messages.append({"role": role, "content": msg.get("content", "")})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=glm_messages,
                temperature=temperature,
                **extra_params
            )
            return response.choices[0].message.content
        else:
            # OpenAI 兼容 API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                **extra_params
            )
            return response.choices[0].message.content
    
    def chat_with_image(self, messages: list, image_url: str, image_detail: str = "high", **kwargs):
        """
        发送带图片的聊天请求
        
        Args:
            messages: 消息列表
            image_url: 图片 URL 或 base64
            image_detail: 图片细节级别 "low", "high", "auto"
        
        Returns:
            响应文本
        """
        # 支持 base64 和 URL
        if image_url.startswith("data:image"):
            image_data = image_url
        elif os.path.isfile(image_url):
            with open(image_url, "rb") as f:
                img = Image.open(f)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode()
                image_data = f"data:image/png;base64,{img_b64}"
        else:
            image_data = image_url
        
        # 构建 vision 消息
        vision_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user" and msg.get("content"):
                    vision_messages.append({
                        "role": msg["role"],
                        "content": [
                            {"type": "text", "text": msg["content"]},
                            {"type": "image_url", "image_url": {"url": image_data, "detail": image_detail}}
                        ]
                    })
                else:
                    vision_messages.append(msg)
        
        return self.chat(vision_messages, **kwargs)
    
    def list_models(self):
        """列出所有可用模型"""
        models = []
        for provider, config in load_provider_models().items():
            for model in config.get("models", []):
                models.append({
                    "provider": provider,
                    "model": model,
                    "base_url": config.get("base_url", ""),
                    "api_key": "***" if config.get("api_key") else "",
                })
        return models


# ========== CLI ==========

def main():
    parser = argparse.ArgumentParser(description="统一 Chat Client CLI")
    parser.add_argument("-m", "--model", default="deepseek:deepseek-chat", help="模型，如 deepseek:deepseek-chat")
    parser.add_argument("-k", "--api-key", help="API Key")
    parser.add_argument("-u", "--base-url", help="Base URL")
    parser.add_argument("-p", "--prompt", help="提示词")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    parser.add_argument("--stream", "-s", action="store_true", help="流式输出")
    args = parser.parse_args()
    
    client = AiClient(args.model, args.api_key, args.base_url)
    
    if args.interactive:
        messages = []
        print(f"已加载模型: {args.model}，输入 exit 退出")
        while True:
            try:
                user_input = input("\n你: ").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                if not user_input:
                    continue
                messages.append({"role": "user", "content": user_input})
                response = client.chat(messages)
                messages.append({"role": "assistant", "content": response})
                print(f"\nAI: {response}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")
    elif args.prompt:
        messages = [{"role": "user", "content": args.prompt}]
        response = client.chat(messages, stream=args.stream)
        if args.stream:
            for chunk in response:
                print(chunk, end="", flush=True)
        else:
            print(response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
