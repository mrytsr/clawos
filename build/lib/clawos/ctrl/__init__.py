from __future__ import annotations

from flask import jsonify


def api_ok(data=None, status=200):
    return jsonify({'success': True, 'data': data}), status


def api_error(message='Bad Request', status=400, code=None):
    payload = {'success': False, 'error': {'message': message}}
    if code is not None:
        payload['error']['code'] = code
    return jsonify(payload), status
