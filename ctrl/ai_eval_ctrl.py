#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 模型评测控制器 - 后台任务版
"""

import os
import sys
import json
import time
import requests
import threading
from flask import Blueprint, jsonify, request

import config

ai_eval_bp = Blueprint('ai_eval', __name__)

# 模型存储文件
MODELS_FILE = os.path.join(config.DATA_DIR, 'ai_models.json')
# 评测状态文件
EVAL_STATE_FILE = os.path.join(config.DATA_DIR, 'ai_eval_state.json')

# 评测题目
REASONING_QUESTIONS = [
    {"question": "解方程组：2x+3y-z=10, x-y+2z=-5, 3x+2y+z=8。请用矩阵消元法求解。", "answer_type": "math_system"},
    {"question": "计算定积分：∫(0到π) x·sin(x) dx，给出详细步骤。", "answer_type": "calculus"},
    {"question": "数列a₁=1,a₂=3,aₙ=2aₙ₋₁+aₙ₋₂。求a₆并证明通项公式。", "answer_type": "sequence"},
    {"question": "概率题：袋中有5红球、3蓝球、2绿球。连续抽3次（不放回），求至少抽到2个红球的概率。", "answer_type": "probability"},
    {"question": "五人跑步：A在B前面，C第三，D紧跟E后，B不在最后。请推断所有名次。", "answer_type": "logical_race"},
]

LANGUAGE_QUESTIONS = [
    {"question": "语法纠错：'The committee have made their decision yesterday.' 找出错误并改正。", "answer_type": "grammar_error"},
    {"question": "同义改写：'Although the company had been experiencing significant financial difficulties, the CEO decided to continue operations.' 简化。", "answer_type": "paraphrase"},
    {"question": "词义辨析：affect vs effect 用法区别。", "answer_type": "vocab_distinction"},
    {"question": "阅读理解：Climate change impacts through extreme weather. Paris Agreement aims 1.5°C limit. 问题：主要观点是什么？", "answer_type": "academic_reading"},
    {"question": "情感分析：'简直太垃圾了！' 情感强度(1-10)和类型。", "answer_type": "sentiment"},
]

CODE_QUESTIONS = [
    {"question": "用Python实现LRU缓存，get和put方法，时间复杂度O(1)。", "answer_type": "lru_cache"},
    {"question": "用JS实现发布-订阅模式，subscribe、unsubscribe、publish方法。", "answer_type": "pub_sub"},
    {"question": "员工表employees查询各部门工资最高的前3名，按部门排序。", "answer_type": "complex_sql"},
    {"question": "在旋转数组[4,5,6,7,0,1,2]中查找0，返回索引或-1。", "answer_type": "binary_search"},
    {"question": "用Python实现堆排序过程。", "answer_type": "heap_sort"},
]

# 全局评测状态
EVAL_STATE = {
    "running": False,
    "models": [],
    "results": [],
    "current": {"model_idx": 0, "category": "", "question_idx": 0},
    "start_time": None
}

def load_models():
    """加载模型列表"""
    models = load_ai_client_models()
    if os.path.exists(MODELS_FILE):
        try:
            with open(MODELS_FILE, 'r', encoding='utf-8') as f:
                user_models = json.load(f)
                for m in user_models:
                    m['source'] = 'user'
                models.extend(user_models)
        except:
            pass
    return models

def load_ai_client_models():
    """从 ai_client 加载预设模型"""
    models = []
    try:
        sys.path.insert(0, '/root/clawos')
        from lib.ai_client import PROVIDOR_MODELS
        for provider, config in PROVIDOR_MODELS.items():
            base_url = config.get('base_url', '')
            api_key = config.get('api_key', '')
            provider_models = config.get('models', [])
            for model in provider_models:
                models.append({
                    "base_url": base_url,
                    "api_key": api_key,
                    "model": model,
                    "display_name": f"{provider}:{model}",
                    "source": "ai_client"
                })
    except Exception as e:
        print(f"加载 ai_client 模型失败: {e}")
    return models

def save_models(models):
    """保存模型列表（只保存用户添加的）"""
    os.makedirs(os.path.dirname(MODELS_FILE), exist_ok=True)
    user_models = [m for m in models if m.get('source') == 'user']
    with open(MODELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_models, f, ensure_ascii=False, indent=2)

def load_eval_state():
    """加载评测状态"""
    if os.path.exists(EVAL_STATE_FILE):
        try:
            with open(EVAL_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"running": False, "results": [], "current": {}, "start_time": None}

def save_eval_state(state):
    """保存评测状态"""
    os.makedirs(os.path.dirname(EVAL_STATE_FILE), exist_ok=True)
    with open(EVAL_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# ========== API 接口 ==========

@ai_eval_bp.route('/api/ai/models', methods=['GET'])
def get_models():
    """获取模型列表"""
    models = load_models()
    return jsonify({"success": True, "models": models})

@ai_eval_bp.route('/api/ai/models/add', methods=['POST'])
def add_model():
    """添加模型"""
    data = request.json
    base_url = data.get('base_url', '').strip()
    api_key = data.get('api_key', '').strip()
    model = data.get('model', '').strip()
    display_name = data.get('display_name', '').strip()
    
    if not base_url or not api_key or not model:
        return jsonify({"success": False, "error": "缺少必要参数"})
    
    models = load_models()
    for m in models:
        if m['base_url'] == base_url and m['model'] == model:
            return jsonify({"success": False, "error": "模型已存在"})
    
    models.append({
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "display_name": display_name or model,
        "source": "user"
    })
    save_models(models)
    return jsonify({"success": True})

@ai_eval_bp.route('/api/ai/models/delete', methods=['POST'])
def delete_model():
    """删除模型"""
    data = request.json
    base_url = data.get('base_url', '')
    model = data.get('model', '')
    models = load_models()
    models = [m for m in models if not (m['base_url'] == base_url and m['model'] == model)]
    save_models(models)
    return jsonify({"success": True})

@ai_eval_bp.route('/api/ai/eval/status', methods=['GET'])
def get_eval_status():
    """获取评测状态"""
    state = load_eval_state()
    return jsonify({"success": True, "status": state})

@ai_eval_bp.route('/api/ai/eval/start', methods=['POST'])
def start_eval():
    """开始评测"""
    data = request.json
    model_indices = data.get('models', [])
    
    if not model_indices:
        return jsonify({"success": False, "error": "请选择模型"})
    
    # 获取选中的模型
    all_models = load_models()
    selected_models = [all_models[i] for i in model_indices if i < len(all_models)]
    
    if not selected_models:
        return jsonify({"success": False, "error": "无效的模型选择"})
    
    # 获取已有结果（不清除）
    existing_results = []
    if os.path.exists(EVAL_STATE_FILE):
        try:
            with open(EVAL_STATE_FILE, 'r', encoding='utf-8') as f:
                old_state = json.load(f)
                existing_results = old_state.get("results", [])
        except:
            pass
    
    # 初始化状态（保留已有结果）
    state = {
        "running": True,
        "models": selected_models,
        "results": existing_results,  # 保留之前的结果
        "current": {"model_idx": 0, "category": "", "question_idx": 0, "total_models": len(selected_models)},
        "start_time": time.time()
    }
    save_eval_state(state)
    
    # 后台启动评测线程
    thread = threading.Thread(target=run_evaluation_background, args=(selected_models,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True})

@ai_eval_bp.route('/api/ai/eval/stop', methods=['POST'])
def stop_eval():
    """停止评测"""
    state = load_eval_state()
    state["running"] = False
    save_eval_state(state)
    return jsonify({"success": True})

@ai_eval_bp.route('/api/eval/clear', methods=['POST'])
def clear_eval():
    """清除评测结果"""
    state = {"running": False, "results": [], "current": {}, "start_time": None}
    save_eval_state(state)
    return jsonify({"success": True})

@ai_eval_bp.route('/api/eval/delete', methods=['POST'])
def delete_eval():
    """删除单个评测结果"""
    data = request.json
    index = data.get('index', -1)
    
    state = load_eval_state()
    if 0 <= index < len(state.get("results", [])):
        state["results"].pop(index)
        save_eval_state(state)
    
    return jsonify({"success": True})

# ========== 后台评测 ==========

def run_evaluation_background(models):
    """后台评测线程"""
    all_categories = [
        ("reasoning", REASONING_QUESTIONS),
        ("language", LANGUAGE_QUESTIONS),
        ("code", CODE_QUESTIONS)
    ]
    
    for model_idx, model in enumerate(models):
        # 检查是否停止
        state = load_eval_state()
        if not state.get("running"):
            break
        
        model_result = {
            "model": model.get("display_name") or model.get("model"),
            "base_url": model.get("base_url"),
            "api_key": model.get("api_key"),
            "reasoning": 0,
            "language": 0,
            "code": 0,
            "overall_score": 0
        }
        
        for cat_idx, (cat_name, questions) in enumerate(all_categories):
            # 更新进度
            state = load_eval_state()
            state["current"] = {
                "model_idx": model_idx,
                "model_name": model.get("display_name") or model.get("model"),
                "category": cat_name,
                "category_idx": cat_idx,
                "question_idx": 0,
                "total_questions": len(questions)
            }
            save_eval_state(state)
            
            # 评测该类别
            score = test_category(questions, model.get("base_url"), model.get("api_key"), model.get("model"), model_idx, cat_name)
            model_result[cat_name] = score
            
            # 检查是否停止
            state = load_eval_state()
            if not state.get("running"):
                break
        
        # 计算总分
        model_result["overall_score"] = (model_result["reasoning"] + model_result["language"] + model_result["code"]) / 3
        
        # 保存结果
        state = load_eval_state()
        state["results"].append(model_result)
        save_eval_state(state)
    
    # 完成
    state = load_eval_state()
    state["running"] = False
    state["current"] = {}
    save_eval_state(state)

def test_category(questions, base_url, api_key, model_name, model_idx, cat_name):
    """测试一个类别"""
    total_score = 0
    
    for q_idx, q in enumerate(questions):
        # 更新进度
        state = load_eval_state()
        if state.get("running"):
            state["current"]["question_idx"] = q_idx
            save_eval_state(state)
        
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "你是一个智能助手，请准确简洁地回答问题。"},
                    {"role": "user", "content": q['question']}
                ],
                "temperature": 0.7
            }
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 特殊处理
            if "zhipu" in base_url.lower() or "bigmodel" in base_url.lower():
                headers["Authorization"] = api_key
            
            # 处理 URL
            full_url = base_url
            if '/v1/chat/completions' not in full_url:
                if full_url.endswith('/v4'):
                    full_url = full_url + '/chat/completions'
                elif full_url.endswith('/v1'):
                    full_url = full_url + '/chat/completions'
                else:
                    full_url = full_url.rstrip('/') + '/v1/chat/completions'
            
            response = requests.post(full_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                content = response.json()
                if 'choices' in content and len(content['choices']) > 0:
                    text = content['choices'][0]['message'].get('content', '')
                    score = evaluate_response(q, text)
                    total_score += score
        except Exception as e:
            print(f"Error: {e}")
    
    return total_score / len(questions) if questions else 0

def evaluate_response(question, response):
    """评估回答质量"""
    score = 0
    response_lower = response.lower()
    
    if len(response) > 50:
        score += 20
    if any(kw in response for kw in ["步骤", "因为", "首先", "其次", "therefore", "because", "step"]):
        score += 20
    if any(kw in response_lower for kw in ["答案", "结果", "result", "solution", "解"]):
        score += 20
    if any(kw in response_lower for kw in ["def ", "function", "select", "return", "class", "import"]):
        score += 20
    if any(kw in response_lower for kw in ["错误", "不对", "修复", "fix", "bug", "正确"]):
        score += 10
    
    return min(score, 100)
