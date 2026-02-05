from flask import request

from ctrl import api_error, api_ok

from ctrl.task_ctrl import create_task
from lib import (
    disk_utils,
    docker_utils,
    git_utils,
    network_utils,
    packages_utils,
    process_utils,
    systemd_utils,
)


def register_system(app):
    def _wrap(result, fail_status=400):
        if isinstance(result, dict) and result.get('success'):
            data = dict(result)
            data.pop('success', None)
            return api_ok(data)
        message = None
        if isinstance(result, dict):
            message = result.get('message')
        return api_error(message or 'Error', status=fail_status)

    @app.route('/api/process/list')
    def api_process_list():
        result = process_utils.list_processes()
        return _wrap(result)

    @app.route('/api/process/kill/<int:pid>', methods=['POST'])
    def api_process_kill(pid):
        result = process_utils.kill_process(pid)
        return _wrap(result)

    @app.route('/api/process/ports/<int:pid>')
    def api_process_ports(pid):
        result = process_utils.get_process_ports_detail(pid)
        return _wrap(result)

    @app.route('/api/system-packages/list')
    def api_system_packages():
        result = packages_utils.list_system_packages()
        return _wrap(result)

    @app.route('/api/system-packages/uninstall', methods=['POST'])
    def api_system_packages_uninstall():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = packages_utils.uninstall_system_package(data.get('name'), data.get('manager'))
        return _wrap(result)

    @app.route('/api/pip/list')
    def api_pip_list():
        result = packages_utils.list_pip_packages()
        return _wrap(result)

    @app.route('/api/pip/install', methods=['POST'])
    def api_pip_install():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = packages_utils.install_pip_package(data.get('package'))
        return _wrap(result)

    @app.route('/api/pip/uninstall', methods=['POST'])
    def api_pip_uninstall():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = packages_utils.uninstall_pip_package(data.get('package'))
        return _wrap(result)

    @app.route('/api/npm/list')
    def api_npm_list():
        result = packages_utils.list_npm_packages()
        return _wrap(result)

    @app.route('/api/npm/install', methods=['POST'])
    def api_npm_install():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = packages_utils.install_npm_package(data.get('package'))
        return _wrap(result)

    @app.route('/api/npm/uninstall', methods=['POST'])
    def api_npm_uninstall():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = packages_utils.uninstall_npm_package(data.get('package'))
        return _wrap(result)

    @app.route('/api/docker/images')
    def api_docker_images():
        result = docker_utils.list_docker_images()
        return _wrap(result)

    @app.route('/api/docker/containers')
    def api_docker_containers():
        result = docker_utils.list_docker_containers()
        return _wrap(result)

    @app.route('/api/docker/image/rm', methods=['POST'])
    def api_docker_image_rm():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = docker_utils.remove_docker_image(data.get('id'))
        return _wrap(result)

    @app.route('/api/docker/container/rm', methods=['POST'])
    def api_docker_container_rm():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = docker_utils.remove_docker_container(data.get('id'), data.get('force', False))
        return _wrap(result)

    @app.route('/api/docker/container/stop', methods=['POST'])
    def api_docker_container_stop():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = docker_utils.stop_docker_container(data.get('id'))
        return _wrap(result)

    @app.route('/api/docker/container/start', methods=['POST'])
    def api_docker_container_start():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        result = docker_utils.start_docker_container(data.get('id'))
        return _wrap(result)

    @app.route('/api/systemd/list')
    def api_systemd_list():
        result = systemd_utils.list_systemd_services()
        return _wrap(result)

    @app.route('/api/systemd/control', methods=['POST'])
    def api_systemd_control():
        data = request.json
        if not isinstance(data, dict):
            return api_error('Invalid JSON', status=400)
        service = data.get('service')
        action = data.get('action')
        def _run():
            result = systemd_utils.control_systemd_service(service, action)
            if isinstance(result, dict) and result.get('success'):
                return
            message = None
            if isinstance(result, dict):
                message = result.get('message')
            raise RuntimeError(message or 'Error')

        task_id = create_task(_run, name=f'systemd:{action}:{service}')
        return api_ok({'taskId': task_id})

    @app.route('/api/disk/list')
    def api_disk_list():
        result = disk_utils.list_disks()
        return _wrap(result)

    @app.route('/api/network/list')
    def api_network_list():
        result = network_utils.list_network()
        return _wrap(result)

    @app.route('/api/git/list')
    def api_git_list():
        result = git_utils.get_all_git_repos_info()
        return api_ok({'repos': result})
