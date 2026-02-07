from flask import Blueprint, request

import config


auth_bp = Blueprint('auth', __name__)


@auth_bp.before_app_request
def require_auth():
    remote_addr = request.remote_addr or ''
    if remote_addr in {'127.0.0.1', '::1'}:
        return None
    if remote_addr.startswith('127.'):
        return None
    if request.endpoint == 'static':
        return None
    if request.path.startswith('/socket.io'):
        return None
    auth = request.authorization
    if (
        auth
        and auth.password == config.AUTH_PASSWORD
    ):
        return None

    body = (
        '<!doctype html>'
        '<html lang="zh-CN"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>需要登录</title>'
        '</head>'
        '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,'
        'Helvetica,Arial,sans-serif;padding:24px;">'
        '<h2 style="margin:0 0 12px 0;">需要登录</h2>'
        '<div style="color:#57606a;line-height:1.6;">'
        '此页面启用了 Basic Auth。请在浏览器弹窗中输入账号密码。'
        '</div>'
        '<div style="margin-top:12px;padding:12px;border:1px solid #d0d7de;'
        'border-radius:8px;background:#f6f8fa;">'
        f'<div>密码：{config.AUTH_PASSWORD}</div>'
        '</div>'
        '</body></html>'
    )
    return (
        body,
        401,
        {
            'WWW-Authenticate': 'Basic realm="Login Required"',
            'Content-Type': 'text/html; charset=utf-8',
        },
    )


@auth_bp.route('/logout')
def logout():
    body = (
        '<!doctype html>'
        '<html lang="zh-CN"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>退出登录</title>'
        '</head>'
        '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,'
        'Helvetica,Arial,sans-serif;padding:24px;">'
        '<h2 style="margin:0 0 12px 0;">已退出登录</h2>'
        '<div style="color:#57606a;line-height:1.6;">'
        '请刷新页面重新输入密码。'
        '</div>'
        '</body></html>'
    )
    return (
        body,
        401,
        {
            'WWW-Authenticate': 'Basic realm="Login Required"',
            'Cache-Control': 'no-store',
            'Content-Type': 'text/html; charset=utf-8',
        },
    )
