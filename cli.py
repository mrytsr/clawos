import os
import config


def cli_main():
    import json as _json
    import secrets as _secrets
    import subprocess as _subprocess
    import sys as _sys
    import time as _time

    try:
        import click as _click
    except Exception as e:
        raise SystemExit(f'缺少依赖 click：{e}')

    def _password_file():
        return os.path.join(config.DATA_DIR, 'clawos_password.json')

    def _ensure_data_dir_and_password():
        os.makedirs(config.DATA_DIR, exist_ok=True)
        p = _password_file()
        if os.path.exists(p):
            return
        password = _secrets.token_hex(8)
        with open(p, 'w', encoding='utf-8') as f:
            _json.dump({'password': password}, f, ensure_ascii=False)

    def _load_password():
        p = _password_file()
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    return (_json.load(f).get('password') or '').strip()
        except Exception:
            return ''
        return ''

    def _run(args, check=False, capture=False):
        if os.name == 'nt':
            raise SystemExit('该 CLI 仅支持 Linux systemd（systemctl --user）')
        kwargs = {}
        if capture:
            kwargs.update({'capture_output': True, 'text': True})
        return _subprocess.run(args, check=check, **kwargs)

    def _service_path():
        return os.path.join(os.path.expanduser('~'), '.config', 'systemd', 'user', 'clawos.service')

    def _installed_app_dir():
        try:
            import app as _app
        except Exception:
            return ''
        p = getattr(_app, '__file__', '') or ''
        if not p:
            return ''
        return os.path.abspath(os.path.dirname(p))

    def _detect_app_dir(app_dir):
        if app_dir:
            app_dir = os.path.abspath(app_dir)
            if not os.path.isfile(os.path.join(app_dir, 'app.py')):
                raise SystemExit('未找到 app.py：' + os.path.join(app_dir, 'app.py'))
            return app_dir

        cwd = os.getcwd()
        if os.path.isfile(os.path.join(cwd, 'app.py')):
            return os.path.abspath(cwd)

        installed = _installed_app_dir()
        if installed and os.path.isfile(os.path.join(installed, 'app.py')):
            return installed

        candidate = os.path.join(os.path.expanduser('~'), 'clawos')
        if os.path.isfile(os.path.join(candidate, 'app.py')):
            return os.path.abspath(candidate)

        raise SystemExit('未找到 app.py 所在目录，请传入 --app-dir')

    def _install_service_internal(app_dir=None, python_bin=None):
        if os.name == 'nt':
            raise SystemExit('该 CLI 仅支持 Linux systemd（systemctl --user）')

        _ensure_data_dir_and_password()
        app_dir = _detect_app_dir(app_dir)

        if not python_bin:
            python_bin = _sys.executable

        service_dir = os.path.dirname(_service_path())
        os.makedirs(service_dir, exist_ok=True)

        app_py = os.path.join(app_dir, 'app.py')
        unit = '\n'.join([
            '[Unit]',
            'Description=ClawOS Web Panel',
            'After=network.target',
            '',
            '[Service]',
            'Type=simple',
            f'WorkingDirectory={app_dir}',
            f'ExecStart={python_bin} {app_py}',
            'Restart=on-failure',
            'RestartSec=5',
            'StandardOutput=journal',
            'StandardError=journal',
            '',
            '[Install]',
            'WantedBy=default.target',
            '',
        ])
        with open(_service_path(), 'w', encoding='utf-8') as f:
            f.write(unit)

        _run(['systemctl', '--user', 'daemon-reload'], check=False)

    def _print_install_service_hint():
        _click.echo('未检测到 systemd unit：' + _service_path(), err=True)
        _click.echo('请先执行: clawos install-service --app-dir <源码目录> --python <python路径>', err=True)
        _click.echo('或执行: clawos install', err=True)

    def _require_service_installed():
        if os.path.exists(_service_path()):
            return
        _print_install_service_hint()
        raise SystemExit(1)

    @_click.group(context_settings={'help_option_names': ['-h', '--help']})
    def clawos():
        pass

    @clawos.command()
    def start():
        _require_service_installed()
        _run(['systemctl', '--user', 'start', 'clawos'], check=False)
        _time.sleep(1)
        r = _run(['systemctl', '--user', 'is-active', '--quiet', 'clawos'], check=False)
        if r.returncode == 0:
            _click.echo('启动成功')
            _click.echo(f'访问地址: http://localhost:{config.SERVER_PORT}')
            return
        _click.echo('启动失败，请检查日志: journalctl --user -u clawos -e', err=True)
        raise SystemExit(1)

    @clawos.command()
    def stop():
        _require_service_installed()
        _run(['systemctl', '--user', 'stop', 'clawos'], check=False)
        _click.echo('已停止')

    @clawos.command()
    def restart():
        _require_service_installed()
        _run(['systemctl', '--user', 'restart', 'clawos'], check=False)
        _click.echo('已重启')

    @clawos.command()
    def status():
        _ensure_data_dir_and_password()
        _click.echo('=== ClawOS 状态 ===')
        _click.echo(f'配置目录: {config.DATA_DIR}')
        _click.echo('日志命令: journalctl --user -u clawos -f')
        _click.echo(f'访问端口: {config.SERVER_PORT}')
        _click.echo('')

        if not os.path.exists(_service_path()):
            _click.echo('运行状态: 未安装 service')
            _click.echo('')
            _print_install_service_hint()
            pwd = _load_password()
            if pwd:
                _click.echo('')
                _click.echo(f'登录密码: {pwd}')
            return

        r = _run(['systemctl', '--user', 'is-active', '--quiet', 'clawos'], check=False)
        if r.returncode == 0:
            _click.echo('运行状态: 运行中')
            _click.echo(f'访问地址: http://localhost:{config.SERVER_PORT}')
        else:
            _click.echo('运行状态: 未运行')

        pwd = _load_password()
        if pwd:
            _click.echo('')
            _click.echo(f'登录密码: {pwd}')

    @clawos.command()
    def log():
        _require_service_installed()
        if os.name == 'nt':
            raise SystemExit('该 CLI 仅支持 Linux systemd（journalctl）')
        raise SystemExit(_subprocess.call(['journalctl', '--user', '-u', 'clawos', '-f']))

    @clawos.command()
    def enable():
        _require_service_installed()
        _run(['systemctl', '--user', 'enable', 'clawos.service'], check=False)
        _click.echo('已启用开机自启')

    @clawos.command()
    def disable():
        _require_service_installed()
        _run(['systemctl', '--user', 'disable', 'clawos.service'], check=False)
        _click.echo('已禁用开机自启')

    @clawos.command(name='install-service')
    @_click.option('--app-dir', type=_click.Path(file_okay=False, dir_okay=True, resolve_path=True))
    @_click.option('--python', 'python_bin', type=_click.Path(dir_okay=False, resolve_path=True))
    def install_service(app_dir, python_bin):
        _install_service_internal(app_dir=app_dir, python_bin=python_bin)
        _click.echo('已写入 systemd unit: ' + _service_path())

    @clawos.command()
    def password():
        _ensure_data_dir_and_password()
        with open(_password_file(), 'r', encoding='utf-8') as f:
            _sys.stdout.write(f.read())

    @clawos.command()
    @_click.option('--app-dir', type=_click.Path(file_okay=False, dir_okay=True, resolve_path=True))
    @_click.option('--python', 'python_bin', type=_click.Path(dir_okay=False, resolve_path=True))
    def install(app_dir, python_bin):
        _install_service_internal(app_dir=app_dir, python_bin=python_bin)
        _run(['systemctl', '--user', 'enable', 'clawos.service'], check=False)
        _run(['systemctl', '--user', 'start', 'clawos'], check=False)
        _click.echo('已安装并启动')
        ctx = _click.get_current_context()
        ctx.invoke(status)

    clawos()
