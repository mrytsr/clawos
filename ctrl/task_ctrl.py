import threading
import time
import uuid

from flask import jsonify, request


_TASKS = {}
_LOCK = threading.Lock()


def create_task(run_fn, name=None):
    task_id = uuid.uuid4().hex
    with _LOCK:
        _TASKS[task_id] = {
            'taskId': task_id,
            'name': name or '',
            'status': 'pending',
            'message': '',
            'createdAt': int(time.time() * 1000),
        }

    def _runner():
        try:
            run_fn()
            with _LOCK:
                if task_id in _TASKS:
                    _TASKS[task_id]['status'] = 'success'
        except Exception as e:
            with _LOCK:
                if task_id in _TASKS:
                    _TASKS[task_id]['status'] = 'failed'
                    _TASKS[task_id]['message'] = str(e)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return task_id


def get_task(task_id):
    with _LOCK:
        return dict(_TASKS.get(task_id) or {})


def register_task(app):
    @app.route('/api/task/status')
    def api_task_status():
        task_id = request.args.get('taskId', '').strip()
        if not task_id:
            return jsonify({'success': False, 'error': {'message': 'taskId required'}}), 400
        task = get_task(task_id)
        if not task:
            return jsonify({'success': False, 'error': {'message': 'task not found'}, 'taskId': task_id, 'status': 'failed'}), 404
        return jsonify({'success': True, 'taskId': task_id, 'status': task.get('status'), 'message': task.get('message', '')})

