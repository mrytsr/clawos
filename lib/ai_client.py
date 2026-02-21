#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一 Chat Client - 支持多个 AI 供应商
支持的供应商: deepseek, zhipu, openrouter, qwen, realmrouter, kimi, qiniu
"""

import os
import requests
import argparse
import time
from zhipuai import ZhipuAI
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image
import numpy as np

PROVIDOR_MODELS = {
    "deepseek": {
        "engine": "openai-api",
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-3fa14cdfdf33485386db796940f1d7b5",
        "models": [
            "deepseek-chat", 
            "deepseek-coder", 
            "deepseek-reasoner"
            ],
    },
    "zhipu": {
        "engine": "zhipu-sdk",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "7e4736aea28c419b879303a7bf73d76d.gHS17bvpQ28trJoC",
        "models": [
            "glm-4-flash", 
            "glm-4", 
            "glm-5"
            ],
    },
    "openrouter": {
        "engine": "openai-api",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "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",
        "extra_headers": {
            "HTTP-Referer": "https://utjx.cn",
            "X-Title": "Xiandan App",
        },
        "models": [
            "minimax/minimax-m2.5",
            "moonshotai/kimi-k2.5",
            "z-ai/glm-5"
        ],
    },
    "qwen": {
        "engine": "openai-sdk",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-2b77cf2721c54f768a3596cddef9f276",
        "models": [
            "qwen3-coder-plus"
            ],
    },
    "kimi": {
        "engine": "openai-sdk",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key": "sk-t2WupFladhnmFxT2rMYQNqrxRaLfCWyaivWfjvFPHK7rZRAK",
        "models": [
            "kimi-k2.5"
            ],
    },
    "realmrouter": {
        "engine": "openai-api",
        "base_url": "https://realmrouter.cn/v1",
        "api_key": "sk-IMUkmlaPzwSco6RPGWh2nADqdz1zDzy8w1nfZdor3JLxERfj",
        "models": [
            "gpt-3.5-turbo"
            ],
    },
    "minimax": {
        "engine": "openai-sdk",
        "base_url": "https://api.minimaxi.com/v1",
        "api_key": "sk-api-HsNP7dcbx-HByBD3NlEnDNS8KXfBZ8em3V0Fz4YRFWqzXrEiQISitCK8cNkrHkvsFE8mCq5iPfjcsRDM20AWpZ0PbdogIvthaRVwh-syzz0AhNmhFlbNQ6k",
        "models": [
            "MiniMax-M2.5", 
            "MiniMax-M2.1", 
            "MiniMax-M2"
        ],
    },
    "qiniu": {
        "engine": "openai-api",
        "base_url": "https://api.qnaigc.com/v1",
        "api_key": "sk-d4bf7a0ef715db08059957204a6a8f04c6dc4d28ac0403b107f6e26f96e4f71b",
        "models": [
            "minimax/minimax-m2.5",
            "z-ai/glm-5",
            "moonshotai/kimi-k2.5",
            "deepseek/deepseek-v3.2-251201",
            "xiaomi/mimo-v2-flash",
            "qwen3-max",
            "search"
        ],
    },
}


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
            provider = provider.strip().lower()
            self.model = (model or "").strip() or None
        else:
            provider = provider_model.strip().lower()
            self.model = None
        
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"不支持的供应商: {provider}，支持的供应商: {self.SUPPORTED_PROVIDERS}")
        
        self.provider = provider
        config = PROVIDOR_MODELS.get(provider) or {}

        if not self.model:
            raise ValueError(f"provider_model 必须包含 model，格式为 '{provider}:<model>'")

        self.engine = (config.get("engine") or "").strip()
        if not self.engine:
            raise ValueError(f"{provider} engine 未配置")
        if self.engine not in self.SUPPORTED_ENGINES:
            raise ValueError(f"不支持的 engine: {self.engine}，支持的 engine: {self.SUPPORTED_ENGINES}")

        self.extra_headers = config.get("extra_headers") or {}

        self.api_key = (api_key or "").strip() or (config.get("api_key") or "")
        self.base_url = (base_url or "").strip() or (config.get("base_url") or "")
        
        # 初始化对应的客户端
        if not self.api_key:
            raise ValueError(f"{provider} API_KEY 未配置")
        if not self.base_url:
            raise ValueError(f"{provider} BASE_URL 未配置")

        if self.engine == 'zhipu-sdk':
            self.client = ZhipuAI(api_key=self.api_key)
        elif self.engine == 'openai-sdk':
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
    
    def _check_feature_support(self, feature_name):
        """检查当前提供商是否支持特定功能"""
        supported_providers = {
            'vision': ['zhipu'],  # 只有 zhipu 支持视觉
            'audio_transcription': ['zhipu']  # 只有 zhipu 支持音频转录
        }
        
        if feature_name in supported_providers and self.provider not in supported_providers[feature_name]:
            raise ValueError(f"当前提供商 '{self.provider}' 不支持 {feature_name} 功能。支持该功能的提供商: {', '.join(supported_providers[feature_name])}")

    def _object_to_dict(self, obj):
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, dict):
            return {k: self._object_to_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._object_to_dict(v) for v in obj]

        model_dump = getattr(obj, "model_dump", None)
        if callable(model_dump):
            try:
                dumped = model_dump()
                if isinstance(dumped, dict):
                    return self._object_to_dict(dumped)
            except Exception:
                pass

        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            try:
                dumped = to_dict()
                if isinstance(dumped, dict):
                    return self._object_to_dict(dumped)
            except Exception:
                pass

        as_dict = getattr(obj, "dict", None)
        if callable(as_dict):
            try:
                dumped = as_dict()
                if isinstance(dumped, dict):
                    return self._object_to_dict(dumped)
            except Exception:
                pass

        try:
            dumped = vars(obj)
            if isinstance(dumped, dict) and dumped:
                return {k: self._object_to_dict(v) for k, v in dumped.items() if not str(k).startswith("_")}
        except Exception:
            pass

        return str(obj)
            
    def chat(self, messages, **kwargs):
        """
        统一的对话接口
        
        Args:
            messages (list): 消息列表，格式: [{"role": "user", "content": "Hello"}]
            **kwargs: 其他参数，包括 temperature (float, default 1)
        
        Returns:
            dict: API 响应
        """
        if self.engine == "openai-api":
            response = self._chat_openai_api(messages, **kwargs)
        elif self.engine == "zhipu-sdk":
            response = self._chat_zhipu_sdk(messages, **kwargs)
        elif self.engine == "openai-sdk":
            response = self._chat_openai_sdk(messages, **kwargs)
        else:
            raise ValueError(f"不支持的 engine: {self.engine}")

        data = self._object_to_dict(response)
        if not isinstance(data, dict):
            raise ValueError(f"chat 返回值非 dict: {type(data)}")
        return data
    
    def _chat_openai_api(self, messages, **kwargs):
        temperature = kwargs.pop('temperature', 0.5)
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        headers.update(self.extra_headers)
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"{self.provider} API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            raise e
    
    def _chat_zhipu_sdk(self, messages, **kwargs):
        temperature = kwargs.pop('temperature', 0.5)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            
            return response
                
        except Exception as e:
            print(f"{self.provider} SDK Error: {e}")
            raise e
    
    def _chat_openai_sdk(self, messages, **kwargs):
        temperature = kwargs.pop('temperature', 0.5)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"{self.provider} SDK Error: {e}")
            raise e
    
    def ask(self, question, system_prompt="You are a helpful assistant."):
        """
        简单的问答接口
        
        Args:
            question (str): 用户问题
            system_prompt (str): 系统提示词
         
        Returns:
            str: AI 回答
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        try:
            data = self.chat(messages) or {}
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            return message.get("content")
                
        except Exception as e:
            print(f"ask error: {e}")
            return None

    def transcribe_audio(self, audio_path):
        """
        使用 Zhipu AI 转录音频文件为文本 (GLM-ASR-2512).
        
        Args:
            audio_path (str): 音频文件路径.
            
        Returns:
            str: 转录的文本.
        """
        # 检查音频转录功能支持
        self._check_feature_support('audio_transcription')
            
        try:
            with open(audio_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model="glm-asr-2512",
                    file=audio_file
                )
            return response.text
            
        except Exception as e:
            print(f"Zhipu ASR Error: {e}")
            return None

    def vision_chat(self, messages, image_list=None, **kwargs):
        """
        支持图像输入的聊天接口
        
        Args:
            messages (list): 消息列表，格式: [{"role": "user", "content": "Hello"}]
            image_list (list): 图像列表，可以是文件路径或 PIL 图像对象
            **kwargs: 其他参数，包含 temperature (默认 1)
        
        Returns:
            dict: API 响应
        """
        # 检查视觉功能支持
        if self.provider != 'zhipu':
            # 对于其他供应商，如果有图像输入，需要先转换为文本描述
            print(f"警告: {self.provider} 供应商不支持图像输入，图像将被忽略")
            # 只保留文本消息
            text_messages = []
            for msg in messages:
                content = msg.get('content', '')
                if isinstance(content, list):
                    # 如果是多模态内容，只保留文本部分
                    text_content = []
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            text_content.append(item)
                    if text_content:
                        new_msg = msg.copy()
                        new_msg['content'] = text_content
                        text_messages.append(new_msg)
                else:
                    text_messages.append(msg)
            return self.chat(text_messages, **kwargs)
        else:
            return self._vision_chat_zhipu(messages, image_list, **kwargs)

    def _vision_chat_zhipu(self, messages, image_list, **kwargs):
        """Zhipu AI 图像聊天接口"""
        try:
            # 从 kwargs 中提取 temperature，避免重复传递
            temperature = kwargs.pop('temperature', 0.5)
            
            # 准备图像内容
            image_contents = []
            
            if image_list:
                for img in image_list:
                    image_contents.extend(self._prepare_image_content(img))
            
            # 处理消息内容，将图像添加进去
            processed_messages = []
            for msg in messages:
                content = msg.get('content', '')
                role = msg.get('role', 'user')
                
                if isinstance(content, str):
                    # 原始内容是字符串，加上图像内容
                    new_content = []
                    new_content.append({"type": "text", "text": content})
                    new_content.extend(image_contents)
                    processed_messages.append({"role": role, "content": new_content})
                elif isinstance(content, list):
                    # 原始内容是列表，追加图像内容
                    new_content = content + image_contents
                    processed_messages.append({"role": role, "content": new_content})
                else:
                    processed_messages.append(msg)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=processed_messages,
                temperature=temperature,
                **kwargs
            )
            
            data = self._object_to_dict(response)
            if not isinstance(data, dict):
                raise ValueError(f"vision_chat 返回值非 dict: {type(data)}")
            return data
            
        except Exception as e:
            print(f"Zhipu Vision Chat Error: {e}")
            raise e

    def _prepare_image_content(self, img_input):
        """准备图像内容用于多模态模型"""
        contents = []
        
        # 处理不同的图像输入类型
        if isinstance(img_input, str):
            # 文件路径
            with open(img_input, "rb") as img_file:
                img_str = base64.b64encode(img_file.read()).decode("utf-8")
                contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_str
                    }
                })
        elif isinstance(img_input, Image.Image):
            # PIL 图像对象
            buffered = BytesIO()
            img_input.save(buffered, format="JPEG", quality=70)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": img_str
                }
            })
        elif isinstance(img_input, np.ndarray):
            # numpy 数组 (如 OpenCV 图像)
            img = Image.fromarray(img_input[:, :, ::-1])  # BGR to RGB
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=70)
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            contents.append({
                "type": "image_url",
                "image_url": {
                    "url": img_str
                }
            })
        
        return contents


def _extract_first_content(data):
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    return "" if content is None else str(content)


def _truncate_text(text, limit):
    raw = (text or "").replace("\n", " ").replace("\r", " ").strip()
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 1)] + "…"


def _print_table(rows, max_content=120):
    headers = ["provider", "model", "status", "latency_ms", "content"]
    normalized = []
    for row in rows:
        normalized.append({
            "provider": str(row.get("provider") or ""),
            "model": str(row.get("model") or ""),
            "status": str(row.get("status") or ""),
            "latency_ms": str(row.get("latency_ms") or ""),
            "content": _truncate_text(row.get("content") or "", max_content)
        })

    widths = {h: len(h) for h in headers}
    for row in normalized:
        for h in headers:
            widths[h] = max(widths[h], len(row[h]))

    def line_sep():
        return "+".join([""] + ["-" * (widths[h] + 2) for h in headers] + [""])

    print(line_sep())
    print("| " + " | ".join([h.ljust(widths[h]) for h in headers]) + " |")
    print(line_sep())
    for row in normalized:
        print("| " + " | ".join([row[h].ljust(widths[h]) for h in headers]) + " |")
    print(line_sep())


def _scan_models(question):
    rows = []
    for provider, config in PROVIDOR_MODELS.items():
        for model in (config.get("models") or []):
            provider_model = f"{provider}:{model}"
            start = time.perf_counter()
            status = "ok"
            content = ""
            try:
                client = AiClient(provider_model)
                data = client.chat([{"role": "user", "content": question}])
                content = _extract_first_content(data) or str(data)
            except Exception as e:
                status = "error"
                content = str(e)
            elapsed = int((time.perf_counter() - start) * 1000)
            rows.append({
                "provider": provider,
                "model": model,
                "status": status,
                "latency_ms": elapsed,
                "content": content
            })
    return rows


if __name__ == '__main__':
    """
    简单测试程序：输入 provider-model 字符串 + 一句话，调用 ask 输出 answer
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--question", default="夸一夸七牛云 AI 推理服务")
    args = parser.parse_args()

    if args.scan:
        rows = _scan_models(args.question)
        _print_table(rows)
        raise SystemExit(0)

    print("=" * 60)
    print("AiClient 测试")
    print("=" * 60)

    try:
        print("\n可用 provider:model（一行一个，直接复制）：")
        for provider, config in PROVIDOR_MODELS.items():
            for model in (config.get("models") or []):
                print(f"{provider}:{model}")
        print()

        provider_model = input("请输入 provider:model（如 deepseek:deepseek-chat / minimax:MiniMax-M2.1）：").strip()
        if not provider_model:
            provider_model = "deepseek:deepseek-chat"

        question = input("请输入一句话：").strip()
        if not question:
            question = "Hi, how are you?"

        client = AiClient(provider_model)
        answer = client.ask(question=question, system_prompt="You are a helpful assistant.")

        print("\n" + "-" * 60)
        print(f"provider_model: {provider_model}")
        print(f"question: {question}")
        print(f"answer: {answer}")
        print("-" * 60)

        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
