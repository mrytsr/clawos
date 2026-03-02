import threading
import time
import uuid
import inspect

from flask import Blueprint, jsonify, request


_TASKS = {}
_LOCK = threading.Lock()


def update_task(task_id, status=None, message=None, progress=None):
    with _LOCK:
        if task_id not in _TASKS:
            return False
        if isinstance(status, str) and status:
            _TASKS[task_id]['status'] = status
        if isinstance(message, str):
            _TASKS[task_id]['message'] = message
        if progress is not None:
            try:
                p = float(progress)
            except Exception:
                p = None
            if p is not None:
                if p < 0:
                    p = 0.0
                if p > 100:
                    p = 100.0
                _TASKS[task_id]['progress'] = p
        return True


def create_task(run_fn, name=None):
    task_id = uuid.uuid4().hex
    with _LOCK:
        _TASKS[task_id] = {
            'taskId': task_id,
            'name': name or '',
            'status': 'pending',
            'message': '',
            'progress': 0.0,
            'createdAt': int(time.time() * 1000),
        }

    def _runner():
        try:
            try:
                sig = inspect.signature(run_fn)
                if len(sig.parameters) >= 1:
                    run_fn(task_id)
                else:
                    run_fn()
            except (TypeError, ValueError):
                run_fn()
            update_task(task_id, status='success', progress=100.0)
        except Exception as e:
            update_task(task_id, status='failed', message=str(e))

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return task_id


def get_task(task_id):
    with _LOCK:
        return dict(_TASKS.get(task_id) or {})


task_bp = Blueprint('task', __name__)


@task_bp.route('/api/task/status')
def api_task_status():
    task_id = request.args.get('taskId', '').strip()
    if not task_id:
        return jsonify({
            'success': False,
            'error': {'message': 'taskId required'},
        }), 400
    task = get_task(task_id)
    if not task:
        return jsonify({
            'success': False,
            'error': {'message': 'task not found'},
            'taskId': task_id,
            'status': 'failed',
        }), 404
    return jsonify({
        'success': True,
        'taskId': task_id,
        'status': task.get('status'),
        'message': task.get('message', ''),
        'progress': task.get('progress', 0.0),
    })
