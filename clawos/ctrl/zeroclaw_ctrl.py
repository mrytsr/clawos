#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ZeroClaw 配置控制器
"""

import os
import toml
from flask import Blueprint, jsonify, request, current_app, send_from_directory

zeroclaw_bp = Blueprint('zeroclaw', __name__)

ZEROCLAW_CONFIG_PATH = os.path.expanduser('~/.zeroclaw/config.toml')

def load_zeroclaw_config():
    """加载zeroclaw配置"""
    try:
        if os.path.exists(ZEROCLAW_CONFIG_PATH):
            with open(ZEROCLAW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return toml.load(f)
    except Exception as e:
        print(f"加载zeroclaw配置失败: {e}")
    return {}

def save_zeroclaw_config(config_data):
    """保存zeroclaw配置"""
    try:
        os.makedirs(os.path.dirname(ZEROCLAW_CONFIG_PATH), exist_ok=True)
        with open(ZEROCLAW_CONFIG_PATH, 'w', encoding='utf-8') as f:
            toml.dump(config_data, f)
        return True
    except Exception as e:
        print(f"保存zeroclaw配置失败: {e}")
        return False

@zeroclaw_bp.route('/zeroclaw-config')
def zeroclaw_config_page():
    return send_from_directory(current_app.template_folder, 'zeroclaw_config.html')

@zeroclaw_bp.route('/api/zeroclaw/config', methods=['GET'])
def get_zeroclaw_config():
    """获取zeroclaw配置"""
    config_data = load_zeroclaw_config()
    return jsonify({"success": True, "config": config_data})

@zeroclaw_bp.route('/api/zeroclaw/config', methods=['POST'])
def set_zeroclaw_config():
    """保存zeroclaw配置"""
    data = request.get_json()
    config_data = data.get('config', {})
    if save_zeroclaw_config(config_data):
        return jsonify({"success": True, "message": "配置已保存"})
    return jsonify({"success": False, "message": "保存失败"})

@zeroclaw_bp.route('/api/zeroclaw/restart', methods=['POST'])
def restart_zeroclaw():
    """重启zeroclaw服务"""
    import subprocess
    try:
        subprocess.run(['systemctl', '--user', 'restart', 'zeroclaw'], 
                     capture_output=True, text=True)
        return jsonify({"success": True, "message": "已发送重启指令"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@zeroclaw_bp.route('/api/zeroclaw/status', methods=['GET'])
def get_zeroclaw_status():
    """获取zeroclaw服务状态"""
    import subprocess
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', 'zeroclaw'], 
                              capture_output=True, text=True)
        status = result.stdout.strip()
        return jsonify({"success": True, "status": status, "active": status == "active"})
    except Exception as e:
        return jsonify({"success": False, "status": "unknown", "error": str(e), "active": False})

# === 结构化API ===

@zeroclaw_bp.route('/api/zeroclaw/sections', methods=['GET'])
def get_config_sections():
    """获取配置 sections 列表"""
    config = load_zeroclaw_config()
    sections = []
    
    # 基础设置
    if 'default_provider' in config:
        sections.append({"id": "basic", "name": "基础设置", "icon": "⚙️"})
    if 'model_providers' in config:
        sections.append({"id": "providers", "name": "模型供应商", "icon": "🤖"})
    if 'autonomy' in config:
        sections.append({"id": "autonomy", "name": "自主权限", "icon": "🛡️"})
    if 'security' in config:
        sections.append({"id": "security", "name": "安全设置", "icon": "🔒"})
    if 'runtime' in config:
        sections.append({"id": "runtime", "name": "运行环境", "icon": "📦"})
    if 'reliability' in config:
        sections.append({"id": "reliability", "name": "可靠性", "icon": "🔄"})
    if 'scheduler' in config:
        sections.append({"id": "scheduler", "name": "调度器", "icon": "📅"})
    if 'agent' in config:
        sections.append({"id": "agent", "name": "Agent设置", "icon": "🧠"})
    if 'memory' in config:
        sections.append({"id": "memory", "name": "记忆系统", "icon": "💾"})
    if 'gateway' in config:
        sections.append({"id": "gateway", "name": "网关", "icon": "🌐"})
    if 'browser' in config:
        sections.append({"id": "browser", "name": "浏览器", "icon": "🌍"})
    if 'cron' in config:
        sections.append({"id": "cron", "name": "定时任务", "icon": "⏰"})
    
    return jsonify({"success": True, "sections": sections})

@zeroclaw_bp.route('/api/zeroclaw/section/<section_id>', methods=['GET'])
def get_section_config(section_id):
    """获取指定section的配置"""
    config = load_zeroclaw_config()
    
    section_data = {}
    
    if section_id == "basic":
        section_data = {
            "default_provider": config.get("default_provider", ""),
            "default_model": config.get("default_model", ""),
            "default_temperature": config.get("default_temperature", 0.7),
            "model_routes": config.get("model_routes", []),
            "embedding_routes": config.get("embedding_routes", []),
        }
    elif section_id == "providers":
        section_data = config.get("model_providers", {})
    elif section_id == "autonomy":
        section_data = config.get("autonomy", {})
    elif section_id == "security":
        section_data = config.get("security", {})
    elif section_id == "runtime":
        section_data = config.get("runtime", {})
    elif section_id == "reliability":
        section_data = config.get("reliability", {})
    elif section_id == "scheduler":
        section_data = config.get("scheduler", {})
    elif section_id == "agent":
        section_data = config.get("agent", {})
    elif section_id == "memory":
        section_data = config.get("memory", {})
    elif section_id == "gateway":
        section_data = config.get("gateway", {})
    elif section_id == "browser":
        section_data = config.get("browser", {})
    elif section_id == "cron":
        section_data = config.get("cron", {})
    elif section_id == "observability":
        section_data = config.get("observability", {})
    
    return jsonify({"success": True, "data": section_data, "section": section_id})

@zeroclaw_bp.route('/api/zeroclaw/section/<section_id>', methods=['POST'])
def save_section_config(section_id):
    """保存指定section的配置"""
    data = request.get_json()
    section_data = data.get("data", {})
    
    config = load_zeroclaw_config()
    
    if section_id == "basic":
        config["default_provider"] = section_data.get("default_provider", "")
        config["default_model"] = section_data.get("default_model", "")
        config["default_temperature"] = section_data.get("default_temperature", 0.7)
        config["model_routes"] = section_data.get("model_routes", [])
        config["embedding_routes"] = section_data.get("embedding_routes", [])
    elif section_id == "providers":
        config["model_providers"] = section_data
    elif section_id == "autonomy":
        config["autonomy"] = section_data
    elif section_id == "security":
        config["security"] = section_data
    elif section_id == "runtime":
        config["runtime"] = section_data
    elif section_id == "reliability":
        config["reliability"] = section_data
    elif section_id == "scheduler":
        config["scheduler"] = section_data
    elif section_id == "agent":
        config["agent"] = section_data
    elif section_id == "memory":
        config["memory"] = section_data
    elif section_id == "gateway":
        config["gateway"] = section_data
    elif section_id == "browser":
        config["browser"] = section_data
    elif section_id == "cron":
        config["cron"] = section_data
    elif section_id == "observability":
        config["observability"] = section_data
    
    if save_zeroclaw_config(config):
        return jsonify({"success": True, "message": f"{section_id} 配置已保存"})
    return jsonify({"success": False, "message": "保存失败"})
