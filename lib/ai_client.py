#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一 Chat Client - 支持多个 AI 供应商
支持的供应商: deepseek, zhipu, openrouter, qwen, realmrouter
"""

import os
import requests
from zhipuai import ZhipuAI
from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image
import numpy as np

PROVIDOR_MODELS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key": "sk-3fa14cdfdf33485386db796940f1d7b5",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "7e4736aea28c419b879303a7bf73d76d.gHS17bvpQ28trJoC",
        "models": ["glm-4-flash", "glm-4"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "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",
        "models": ["minimax/minimax-m2.1"],
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-2b77cf2721c54f768a3596cddef9f276",
        "models": ["qwen3-coder-plus"],
    },
    "realmrouter": {
        "base_url": "https://realmrouter.cn/v1",
        "api_key": "sk-IMUkmlaPzwSco6RPGWh2nADqdz1zDzy8w1nfZdor3JLxERfj",
        "models": ["gpt-3.5-turbo"],
    },
    "minimax": {
        "base_url": "https://api.minimaxi.com/v1",
        "api_key": "sk-api-HsNP7dcbx-HByBD3NlEnDNS8KXfBZ8em3V0Fz4YRFWqzXrEiQISitCK8cNkrHkvsFE8mCq5iPfjcsRDM20AWpZ0PbdogIvthaRVwh-syzz0AhNmhFlbNQ6k",
        "models": ["MiniMax-M2.1", "MiniMax-M2"],
    },
}


class AiClient:
    """统一的 Chat 客户端，支持多个 AI 供应商"""
    
    SUPPORTED_PROVIDERS = list(PROVIDOR_MODELS.keys())
    
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
            models = config.get("models") or []
            self.model = models[0] if models else "default-model"

        self.api_key = (api_key or "").strip() or (config.get("api_key") or "")
        self.base_url = (base_url or "").strip() or (config.get("base_url") or "")
        
        # 初始化对应的客户端
        if provider == 'deepseek':
            if not self.api_key:
                raise ValueError("DEEPSEEK_API_KEY 未配置")
            if not self.base_url:
                raise ValueError("DEEPSEEK_BASE_URL 未配置")
        elif provider == 'zhipu':
            if not self.api_key:
                raise ValueError("ZHIPU_API_KEY 未配置")
            self.client = ZhipuAI(api_key=self.api_key)
        elif provider == 'openrouter':
            if not self.api_key:
                raise ValueError("OPENROUTER_API_KEY 未配置")
            if not self.base_url:
                raise ValueError("OPENROUTER_BASE_URL 未配置")
        elif provider == 'qwen':
            if not self.api_key:
                raise ValueError("DASHSCOPE_API_KEY 未配置")
            if not self.base_url:
                raise ValueError("DASHSCOPE_BASE_URL 未配置")
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        elif provider == 'realmrouter':
            if not self.api_key:
                raise ValueError("REALMROUTER_API_KEY 未配置")
            if not self.base_url:
                raise ValueError("REALMROUTER_BASE_URL 未配置")
        elif provider == 'minimax':
            if not self.api_key:
                raise ValueError("MINIMAX_API_KEY 未配置")
            if not self.base_url:
                raise ValueError("MINIMAX_BASE_URL 未配置")
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
            
    def chat(self, messages, **kwargs):
        """
        统一的对话接口
        
        Args:
            messages (list): 消息列表，格式: [{"role": "user", "content": "Hello"}]
            **kwargs: 其他参数，包括 stream (bool, default False), temperature (float, default 0.7)
        
        Returns:
            dict: API 响应 (非流式)
            response: Response 对象 (流式)
        """
        if self.provider == 'deepseek':
            return self._chat_deepseek(messages, **kwargs)
        elif self.provider == 'zhipu':
            return self._chat_zhipu(messages, **kwargs)
        elif self.provider == 'openrouter':
            return self._chat_openrouter(messages, **kwargs)
        elif self.provider == 'qwen':
            return self._chat_qwen(messages, **kwargs)
        elif self.provider == 'realmrouter':
            return self._chat_realmrouter(messages, **kwargs)
        elif self.provider == 'minimax':
            return self._chat_minimax(messages, **kwargs)
    
    def _chat_deepseek(self, messages, **kwargs):
        """DeepSeek API 调用"""
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model or 'deepseek-chat',
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream)
            response.raise_for_status()
            
            if stream:
                return response
            else:
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"DeepSeek API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            raise e
    
    def _chat_zhipu(self, messages, **kwargs):
        """智谱 AI API 调用"""
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        try:
            response = self.client.chat.completions.create(
                model=self.model or 'glm-4-flash',
                messages=messages,
                stream=stream,
                temperature=temperature,
                **kwargs
            )
            
            if stream:
                return response
            else:
                return response
                
        except Exception as e:
            print(f"Zhipu AI Error: {e}")
            raise e
    
    def _chat_openrouter(self, messages, **kwargs):
        """OpenRouter API 调用"""
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://utjx.cn",
            "X-Title": "Xiandan App",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model or 'minimax/minimax-m2.1',
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream, timeout=60)
            response.raise_for_status()
            
            if stream:
                return response
            else:
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            raise e
    
    def _chat_qwen(self, messages, **kwargs):
        """阿里云百炼 Qwen API 调用（使用 OpenAI SDK）"""
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        try:
            response = self.client.chat.completions.create(
                model=self.model or 'qwen3-coder-plus',
                messages=messages,
                stream=stream,
                temperature=temperature,
                **kwargs
            )
            
            # 直接返回 OpenAI SDK 响应对象，与 zhipu 保持一致
            return response
                
        except Exception as e:
            print(f"Qwen API Error: {e}")
            raise e
    
    def _chat_realmrouter(self, messages, **kwargs):
        """RealmRouter API 调用"""
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model or 'gpt-3.5-turbo',
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, stream=stream, timeout=60)
            response.raise_for_status()
            
            if stream:
                return response
            else:
                return response.json()
                
        except requests.exceptions.RequestException as e:
            print(f"RealmRouter API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response text: {e.response.text}")
            raise e

    def _chat_minimax(self, messages, **kwargs):
        stream = kwargs.pop('stream', False)
        temperature = kwargs.pop('temperature', 0.7)
        try:
            response = self.client.chat.completions.create(
                model=self.model or 'MiniMax-M2.1',
                messages=messages,
                stream=stream,
                temperature=temperature,
                **kwargs
            )
            return response
        except Exception as e:
            print(f"MiniMax API Error: {e}")
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
            response = self.chat(messages)
            
            if self.provider == 'deepseek':
                return response['choices'][0]['message']['content']
            elif self.provider == 'zhipu':
                return response.choices[0].message.content
            elif self.provider == 'openrouter':
                return response['choices'][0]['message']['content']
            elif self.provider == 'qwen':
                return response.choices[0].message.content
            elif self.provider == 'realmrouter':
                return response['choices'][0]['message']['content']
            elif self.provider == 'minimax':
                return response.choices[0].message.content
                
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
            client = ZhipuAI(api_key=self.api_key)
            
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
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
            **kwargs: 其他参数，包含 temperature (默认 0.7)
        
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
            return self.chat(text_messages, stream=False, **kwargs)
        else:
            return self._vision_chat_zhipu(messages, image_list, **kwargs)

    def _vision_chat_zhipu(self, messages, image_list, **kwargs):
        """Zhipu AI 图像聊天接口"""
        try:
            client = ZhipuAI(api_key=self.api_key)
            
            # 从 kwargs 中提取 temperature，避免重复传递
            temperature = kwargs.pop('temperature', 0.7)
            
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

            response = client.chat.completions.create(
                model=self.model,
                messages=processed_messages,
                stream=False,
                temperature=temperature,
                **kwargs
            )
            
            return response
            
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


if __name__ == '__main__':
    """
    简单测试程序：输入 provider-model 字符串 + 一句话，调用 ask 输出 answer
    """
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
