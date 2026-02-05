import os
import tempfile
import unittest
from unittest import mock

from flask import Flask
import werkzeug

import ctrl.api_ctrl as api_ctrl


if not getattr(werkzeug, '__version__', None):
    werkzeug.__version__ = '0'


class ApiCtrlTest(unittest.TestCase):
    def _create_app(self, root_dir, conversation_file, trash_dir):
        app = Flask(__name__)
        app.extensions['api_ctx'] = api_ctrl._ApiContext(
            root_dir=root_dir,
            conversation_file=conversation_file,
            trash_dir=trash_dir,
            terminal_supported=os.name != 'nt',
        )
        app.register_blueprint(api_ctrl.api_bp)
        return app

    def test_menu_includes_terminal_when_supported(self):
        app = Flask(__name__)
        with app.app_context():
            ctx_no_terminal = api_ctrl._ApiContext(
                root_dir='.',
                conversation_file='conversation.json',
                trash_dir='trash',
                terminal_supported=False,
            )
            resp, status = api_ctrl._api_menu(ctx_no_terminal)
            self.assertEqual(status, 200)
            items = resp.get_json()['data']['items']
            self.assertFalse(
                any(i.get('action') == 'terminal' for i in items)
            )

            ctx_with_terminal = api_ctrl._ApiContext(
                root_dir='.',
                conversation_file='conversation.json',
                trash_dir='trash',
                terminal_supported=True,
            )
            resp, status = api_ctrl._api_menu(ctx_with_terminal)
            self.assertEqual(status, 200)
            items = resp.get_json()['data']['items']
            self.assertTrue(
                any(i.get('action') == 'terminal' for i in items)
            )

    def test_conversation_save_history_stats_clear(self):
        with tempfile.TemporaryDirectory() as td:
            conversation_file = os.path.join(td, 'conversation.json')
            app = self._create_app(
                root_dir=td,
                conversation_file=conversation_file,
                trash_dir=os.path.join(td, 'trash'),
            )
            client = app.test_client()

            rv = client.post('/api/save', json='not-a-dict')
            self.assertEqual(rv.status_code, 400)
            self.assertFalse(rv.get_json()['success'])

            rv = client.post(
                '/api/save',
                json={'type': 'bot', 'text': 'hello'},
            )
            self.assertEqual(rv.status_code, 200)
            self.assertTrue(rv.get_json()['success'])

            rv = client.post('/api/save', json={'type': 'user', 'text': 'hi'})
            self.assertEqual(rv.status_code, 200)

            rv = client.get('/api/history')
            self.assertEqual(rv.status_code, 200)
            history = rv.get_json()['data']['history']
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]['text'], 'hello')
            self.assertEqual(history[1]['text'], 'hi')

            rv = client.get('/api/stats')
            self.assertEqual(rv.status_code, 200)
            stats = rv.get_json()['data']
            self.assertEqual(stats['sent_count'], 1)
            self.assertEqual(stats['conv_count'], 2)

            rv = client.post('/api/clear')
            self.assertEqual(rv.status_code, 200)

            rv = client.get('/api/history')
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.get_json()['data']['history'], [])

    def test_search_error_and_ok(self):
        with tempfile.TemporaryDirectory() as td:
            conversation_file = os.path.join(td, 'conversation.json')
            app = self._create_app(
                root_dir=td,
                conversation_file=conversation_file,
                trash_dir=os.path.join(td, 'trash'),
            )
            client = app.test_client()

            with mock.patch.object(
                api_ctrl.file_utils,
                'search_files',
                return_value={'error': 'boom'},
            ):
                rv = client.get('/api/search?q=abc')
                self.assertEqual(rv.status_code, 500)
                body = rv.get_json()
                self.assertFalse(body['success'])
                self.assertEqual(body['error']['message'], 'boom')

            with mock.patch.object(
                api_ctrl.file_utils,
                'search_files',
                return_value={'items': []},
            ):
                rv = client.get('/api/search?q=abc')
                self.assertEqual(rv.status_code, 200)
                body = rv.get_json()
                self.assertTrue(body['success'])
                self.assertEqual(body['data'], {'items': []})

    def test_trash_list_clear_and_restore_branches(self):
        with tempfile.TemporaryDirectory() as td:
            root_dir = os.path.join(td, 'root')
            trash_dir = os.path.join(td, 'trash')
            os.makedirs(root_dir, exist_ok=True)
            os.makedirs(trash_dir, exist_ok=True)
            conversation_file = os.path.join(td, 'conversation.json')
            app = self._create_app(
                root_dir=root_dir,
                conversation_file=conversation_file,
                trash_dir=trash_dir,
            )
            client = app.test_client()

            dated_name = '20250101120000_hello.txt'
            with open(
                os.path.join(trash_dir, dated_name),
                'w',
                encoding='utf-8',
            ) as f:
                f.write('x')
            os.makedirs(os.path.join(trash_dir, 'a_dir'), exist_ok=True)

            rv = client.get('/api/trash/list')
            self.assertEqual(rv.status_code, 200)
            payload = rv.get_json()['data']
            self.assertEqual(payload['count'], 2)
            first = payload['items'][0]
            self.assertIn('deleted_at', first)

            rv = client.post(
                '/api/trash/restore/a/bad',
                json={'target_path': 'x'},
            )
            self.assertEqual(rv.status_code, 404)

            ctx = api_ctrl._ApiContext(
                root_dir=root_dir,
                conversation_file=conversation_file,
                trash_dir=trash_dir,
                terminal_supported=False,
            )
            with (
                app.app_context(),
                app.test_request_context(
                    method='POST',
                    json={'target_path': 'x'},
                ),
            ):
                _resp, status = api_ctrl._api_trash_restore(ctx, 'a/bad')
                self.assertEqual(status, 400)

            rv = client.post(
                '/api/trash/restore/not-exist',
                json={'target_path': 'x'},
            )
            self.assertEqual(rv.status_code, 404)

            rv = client.post(f'/api/trash/restore/{dated_name}', json={})
            self.assertEqual(rv.status_code, 400)

            rv = client.post(
                f'/api/trash/restore/{dated_name}',
                json={'target_path': '../outside.txt'},
            )
            self.assertEqual(rv.status_code, 403)

            conflict_path = os.path.join(root_dir, 'restored.txt')
            with open(conflict_path, 'w', encoding='utf-8') as f:
                f.write('y')
            rv = client.post(
                f'/api/trash/restore/{dated_name}',
                json={'target_path': 'restored.txt'},
            )
            self.assertEqual(rv.status_code, 409)
            os.remove(conflict_path)

            with mock.patch.object(
                api_ctrl.shutil,
                'move',
                side_effect=OSError('move failed'),
            ):
                rv = client.post(
                    f'/api/trash/restore/{dated_name}',
                    json={'target_path': 'restored.txt'},
                )
                self.assertEqual(rv.status_code, 500)
                error_message = rv.get_json()['error']['message']
                self.assertEqual(error_message, 'move failed')

            rv = client.post(
                f'/api/trash/restore/{dated_name}',
                json={'target_path': 'restored.txt'},
            )
            self.assertEqual(rv.status_code, 200)
            restored_path = os.path.join(root_dir, 'restored.txt')
            self.assertTrue(os.path.exists(restored_path))
            trashed_path = os.path.join(trash_dir, dated_name)
            self.assertFalse(os.path.exists(trashed_path))

            with open(
                os.path.join(trash_dir, 'tmp.txt'),
                'w',
                encoding='utf-8',
            ) as f:
                f.write('z')
            rv = client.post('/api/trash/clear')
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(os.listdir(trash_dir), [])

    def test_file_info_status_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            conversation_file = os.path.join(td, 'conversation.json')
            app = self._create_app(
                root_dir=td,
                conversation_file=conversation_file,
                trash_dir=os.path.join(td, 'trash'),
            )
            client = app.test_client()

            with mock.patch.object(
                api_ctrl.file_utils,
                'get_file_details',
                return_value={'success': False, 'message': '无效路径'},
            ):
                rv = client.get('/api/file/info?path=bad')
                self.assertEqual(rv.status_code, 403)

            with mock.patch.object(
                api_ctrl.file_utils,
                'get_file_details',
                return_value={'success': False, 'message': '文件不存在'},
            ):
                rv = client.get('/api/file/info?path=missing')
                self.assertEqual(rv.status_code, 404)

            with mock.patch.object(
                api_ctrl.file_utils,
                'get_file_details',
                return_value={'success': False, 'message': 'other'},
            ):
                rv = client.get('/api/file/info?path=other')
                self.assertEqual(rv.status_code, 400)

            with mock.patch.object(
                api_ctrl.file_utils,
                'get_file_details',
                return_value={'success': True, 'info': {'name': 'x'}},
            ):
                rv = client.get('/api/file/info?path=x')
                self.assertEqual(rv.status_code, 200)
                self.assertEqual(rv.get_json()['data'], {'name': 'x'})


if __name__ == '__main__':
    unittest.main()
