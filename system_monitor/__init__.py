# 系统监控模块导出

from .process import list_processes, kill_process, get_process_ports_detail
from .packages import (
    list_system_packages, uninstall_system_package,
    list_pip_packages, install_pip_package, uninstall_pip_package,
    list_npm_packages, install_npm_package, uninstall_npm_package
)
from .docker import (
    list_docker_images, list_docker_containers,
    remove_docker_image, remove_docker_container,
    stop_docker_container, start_docker_container
)
from .systemd import list_systemd_services, control_systemd_service
from .disk import list_disks
from .network import list_network
from .git import get_all_git_repos_info

__all__ = [
    # 进程管理
    'list_processes', 'kill_process', 'get_process_ports_detail',
    # 系统包管理
    'list_system_packages', 'uninstall_system_package',
    # pip 包管理
    'list_pip_packages', 'install_pip_package', 'uninstall_pip_package',
    # npm 包管理
    'list_npm_packages', 'install_npm_package', 'uninstall_npm_package',
    # Docker
    'list_docker_images', 'list_docker_containers',
    'remove_docker_image', 'remove_docker_container',
    'stop_docker_container', 'start_docker_container',
    # Systemd
    'list_systemd_services', 'control_systemd_service',
    # 磁盘
    'list_disks',
    # 网络
    'list_network',
    # Git
    'get_all_git_repos_info',
]
