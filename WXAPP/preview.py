#!/usr/bin/env python3
"""
微信小程序预览工具
调用 miniprogram-ci 进行预览
"""

import subprocess
import os
import sys

# 硬编码配置
APPID = 'wx36dfd5007f439a12'
PRIVATE_KEY = './privatekey.key'
ROBOT = '1'
DESCRIPTION = '快速预览'
VERSION = '1.0.0'
QRCODE_FORMAT = 'image'

def preview(project_path=None, output_file='preview-qrcode.png'):
    """执行小程序预览"""
    
    # 默认当前目录
    if not project_path:
        project_path = '.'
    
    project_path = os.path.abspath(project_path)
    
    # 检查项目路径
    if not os.path.exists(project_path):
        print(f"错误: 项目路径不存在: {project_path}")
        return False
    
    if not os.path.exists(PRIVATE_KEY):
        print(f"警告: 私钥文件不存在: {PRIVATE_KEY}")
    
    cmd = [
        'npx', 'miniprogram-ci', 'preview',
        '--appid', APPID,
        '--project-path', project_path,
        '--private-key-path', PRIVATE_KEY,
        '--robot', ROBOT,
        '--qrcode-format', QRCODE_FORMAT,
        '--qrcode-output-dest', output_file,
        '--upload-version', VERSION,
        '--upload-description', DESCRIPTION,
        '--enable-es6',
    ]
    
    print(f"预览参数:")
    print(f"  项目路径: {project_path}")
    print(f"  输出文件: {output_file}")
    print(f"  Robot编号: {ROBOT}")
    print(f"  AppID: {APPID}")
    print(f"  描述: {DESCRIPTION}")
    print()
    print("执行预览...")
    print("-" * 40)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_path
        )
        if result.returncode == 0:
            print(result.stdout)
            print("-" * 40)
            print("预览成功!")
            return True
        else:
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"执行失败: {e}")
        return False

if __name__ == '__main__':
    # 获取命令行参数作为输出文件名
    output = sys.argv[1] if len(sys.argv) > 1 else 'preview-qrcode.png'
    success = preview(output_file=output)
    sys.exit(0 if success else 1)
