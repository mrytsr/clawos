#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一 Chat Client - 支持多个 AI 供应商
支持的供应商: deepseek, zhipu, openrouter, qwen, realmrouter, kimi, qiniu
"""
import json
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
            "glm-4v-flash2",
            "glm-4-flash", 
            "glm-4", 
            "glm-5",
            "glm-4v"
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
print(json.dumps(PROVIDOR_MODELS, ensure_ascii=False, indent=2))
