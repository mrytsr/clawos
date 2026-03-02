#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NullClaw 配置控制器
"""

import os
import json
import threading
from flask import Blueprint, jsonify, request, current_app, send_from_directory

import config

nullclaw_bp = Blueprint('nullclaw', __name__)

NULLCLAW_CONFIG_PATH = os.path.expanduser('~/.nullclaw/config.json')

def load_nullclaw_config():
    """加载nullclaw配置"""
    try:
        if os.path.exists(NULLCLAW_CONFIG_PATH):
            with open(NULLCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"加载nullclaw配置失败: {e}")
    return {}

def save_nullclaw_config(config_data):
    """保存nullclaw配置"""
    try:
        os.makedirs(os.path.dirname(NULLCLAW_CONFIG_PATH), exist_ok=True)
        with open(NULLCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存nullclaw配置失败: {e}")
        return False

@nullclaw_bp.route('/nullclaw-config')
def nullclaw_config_page():
    return send_from_directory(current_app.template_folder, 'nullclaw_config.html')

@nullclaw_bp.route('/api/nullclaw/config', methods=['GET'])
def get_nullclaw_config():
    """获取nullclaw配置"""
    config_data = load_nullclaw_config()
    return jsonify({"success": True, "config": config_data})

@nullclaw_bp.route('/api/nullclaw/config', methods=['POST'])
def set_nullclaw_config():
    """保存nullclaw配置"""
    data = request.get_json()
    config_data = data.get('config', {})
    if save_nullclaw_config(config_data):
        return jsonify({"success": True, "message": "配置已保存"})
    return jsonify({"success": False, "message": "保存失败"})

@nullclaw_bp.route('/api/nullclaw/config/key', methods=['POST'])
def update_nullclaw_key():
    """更新单个配置项"""
    data = request.get_json()
    key = data.get('key')
    value = data.get('value')
    
    config_data = load_nullclaw_config()
    
    # 支持嵌套key如 "agents.defaults.model.primary"
    keys = key.split('.')
    current = config_data
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    current[keys[-1]] = value
    
    if save_nullclaw_config(config_data):
        return jsonify({"success": True, "message": f"已更新 {key}"})
    return jsonify({"success": False, "message": "保存失败"})

@nullclaw_bp.route('/api/nullclaw/restart', methods=['POST'])
def restart_nullclaw():
    """重启nullclaw服务"""
    try:
        os.system('systemctl --user restart nullclaw 2>/dev/null')
        return jsonify({"success": True, "message": "已发送重启指令"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@nullclaw_bp.route('/api/nullclaw/status', methods=['GET'])
def get_nullclaw_status():
    """获取nullclaw服务状态"""
    import subprocess
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', 'nullclaw'], 
                              capture_output=True, text=True)
        status = result.stdout.strip()
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "status": "unknown", "error": str(e)})

# ========== Models API ==========

@nullclaw_bp.route('/api/nullclaw/models', methods=['GET'])
def get_models():
    """获取所有模型Provider配置"""
    config_data = load_nullclaw_config()
    providers = config_data.get('models', {}).get('providers', {})
    return jsonify({"success": True, "providers": providers})

@nullclaw_bp.route('/api/nullclaw/models/<provider>', methods=['POST'])
def add_model(provider):
    """添加模型Provider"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    if 'models' not in config_data:
        config_data['models'] = {}
    if 'providers' not in config_data['models']:
        config_data['models']['providers'] = {}
    
    config_data['models']['providers'][provider] = data
    if save_nullclaw_config(config_data):
        return jsonify({"success": True, "message": f"已添加 provider: {provider}"})
    return jsonify({"success": False, "message": "保存失败"})

@nullclaw_bp.route('/api/nullclaw/models/<provider>', methods=['PUT'])
def update_model(provider):
    """更新模型Provider"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    if config_data.get('models', {}).get('providers', {}).get(provider):
        config_data['models']['providers'][provider].update(data)
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已更新 provider: {provider}"})
    return jsonify({"success": False, "message": "Provider不存在或保存失败"})

@nullclaw_bp.route('/api/nullclaw/models/<provider>', methods=['DELETE'])
def delete_model(provider):
    """删除模型Provider"""
    config_data = load_nullclaw_config()
    
    if config_data.get('models', {}).get('providers', {}).pop(provider, None):
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已删除 provider: {provider}"})
    return jsonify({"success": False, "message": "Provider不存在或保存失败"})

# ========== Channels API ==========

@nullclaw_bp.route('/api/nullclaw/channels', methods=['GET'])
def get_channels():
    """获取所有Channel配置"""
    config_data = load_nullclaw_config()
    channels = config_data.get('channels', {})
    return jsonify({"success": True, "channels": channels})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>', methods=['POST'])
def add_channel(channel_type):
    """添加Channel"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    if 'channels' not in config_data:
        config_data['channels'] = {}
    
    if channel_type not in config_data['channels']:
        config_data['channels'][channel_type] = {}
    
    config_data['channels'][channel_type].update(data)
    if save_nullclaw_config(config_data):
        return jsonify({"success": True, "message": f"已添加 channel: {channel_type}"})
    return jsonify({"success": False, "message": "保存失败"})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>', methods=['PUT'])
def update_channel(channel_type):
    """更新Channel"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    if channel_type in config_data.get('channels', {}):
        config_data['channels'][channel_type].update(data)
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已更新 channel: {channel_type}"})
    return jsonify({"success": False, "message": "Channel不存在或保存失败"})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>', methods=['DELETE'])
def delete_channel(channel_type):
    """删除Channel"""
    config_data = load_nullclaw_config()
    
    if config_data.get('channels', {}).pop(channel_type, None):
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已删除 channel: {channel_type}"})
    return jsonify({"success": False, "message": "Channel不存在或保存失败"})

# ========== Channel Accounts API ==========

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>/accounts', methods=['GET'])
def get_channel_accounts(channel_type):
    """获取Channel的所有账户"""
    config_data = load_nullclaw_config()
    channel = config_data.get('channels', {}).get(channel_type, {})
    accounts = channel.get('accounts', {})
    return jsonify({"success": True, "accounts": accounts})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>/accounts/<account_name>', methods=['POST'])
def add_channel_account(channel_type, account_name):
    """添加Channel账户"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    if 'channels' not in config_data:
        config_data['channels'] = {}
    if channel_type not in config_data['channels']:
        config_data['channels'][channel_type] = {}
    if 'accounts' not in config_data['channels'][channel_type]:
        config_data['channels'][channel_type]['accounts'] = {}
    
    config_data['channels'][channel_type]['accounts'][account_name] = data
    if save_nullclaw_config(config_data):
        return jsonify({"success": True, "message": f"已添加账户: {account_name}"})
    return jsonify({"success": False, "message": "保存失败"})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>/accounts/<account_name>', methods=['PUT'])
def update_channel_account(channel_type, account_name):
    """更新Channel账户"""
    data = request.get_json()
    config_data = load_nullclaw_config()
    
    accounts = config_data.get('channels', {}).get(channel_type, {}).get('accounts', {})
    if account_name in accounts:
        accounts[account_name].update(data)
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已更新账户: {account_name}"})
    return jsonify({"success": False, "message": "账户不存在或保存失败"})

@nullclaw_bp.route('/api/nullclaw/channels/<channel_type>/accounts/<account_name>', methods=['DELETE'])
def delete_channel_account(channel_type, account_name):
    """删除Channel账户"""
    config_data = load_nullclaw_config()
    
    accounts = config_data.get('channels', {}).get(channel_type, {}).get('accounts', {})
    if accounts.pop(account_name, None):
        if save_nullclaw_config(config_data):
            return jsonify({"success": True, "message": f"已删除账户: {account_name}"})
    return jsonify({"success": False, "message": "账户不存在或保存失败"})
