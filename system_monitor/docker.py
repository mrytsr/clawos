# 系统监控模块 - Docker 管理

from flask import jsonify
import subprocess


def list_docker_images():
    """获取Docker镜像列表"""
    try:
        result = subprocess.run(
            ['docker', 'images', '--format', '{{.Repository}}|{{.Tag}}|{{.ID}}|{{.Size}}|{{.CreatedSince}}'],
            capture_output=True, text=True
        )
        images = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    images.append({
                        'repository': parts[0],
                        'tag': parts[1],
                        'id': parts[2],
                        'size': parts[3],
                        'created': parts[4]
                    })
        return {'success': True, 'images': images}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def list_docker_containers():
    """获取Docker容器列表"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.ID}}|{{.Image}}|{{.Status}}|{{.Names}}|{{.Ports}}'],
            capture_output=True, text=True
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 5:
                    containers.append({
                        'id': parts[0],
                        'image': parts[1],
                        'status': parts[2],
                        'name': parts[3],
                        'ports': parts[4]
                    })
        return {'success': True, 'containers': containers}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def remove_docker_image(image_id):
    """删除Docker镜像"""
    try:
        subprocess.run(['docker', 'rmi', image_id], capture_output=True, text=True)
        return {'success': True, 'message': f'镜像已删除'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def remove_docker_container(container_id, force=False):
    """删除Docker容器"""
    try:
        cmd = ['docker', 'rm']
        if force:
            cmd.append('-f')
        cmd.append(container_id)
        subprocess.run(cmd, capture_output=True, text=True)
        return {'success': True, 'message': f'容器已删除'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def stop_docker_container(container_id):
    """停止Docker容器"""
    try:
        subprocess.run(['docker', 'stop', container_id], capture_output=True, text=True)
        return {'success': True, 'message': f'容器已停止'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def start_docker_container(container_id):
    """启动Docker容器"""
    try:
        subprocess.run(['docker', 'start', container_id], capture_output=True, text=True)
        return {'success': True, 'message': f'容器已启动'}
    except Exception as e:
        return {'success': False, 'message': str(e)}
