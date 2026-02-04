from flask import request


def register_bot_proxy(socketio):
    websocket_module = None
    bot_proxy_supported = True
    try:
        import websocket as websocket_module
    except Exception:
        bot_proxy_supported = False

    bot_gateway_clients = {}

    def on_ws_message(ws, message):
        sid = getattr(ws, 'sid', None)
        if sid:
            try:
                socketio.server.emit('bot_to_proxy', message, room=sid, namespace='/')
            except Exception:
                pass

    def on_ws_error(ws, error):
        pass

    def on_ws_close(ws, close_status_code, close_msg):
        sid = getattr(ws, 'sid', None)
        if sid and sid in bot_gateway_clients:
            del bot_gateway_clients[sid]

    def create_bot_connection(sid):
        if not bot_proxy_supported or websocket_module is None:
            return None
        if sid in bot_gateway_clients:
            return bot_gateway_clients[sid]
        ws = websocket_module.WebSocketApp(
            'ws://127.0.0.1:18789',
            on_message=on_ws_message,
            on_error=on_ws_error,
            on_close=on_ws_close
        )
        ws.sid = sid
        bot_gateway_clients[sid] = ws

        def run_ws():
            ws.run_forever()

        socketio.start_background_task(run_ws)
        return ws

    @socketio.on('proxy_to_bot')
    def bot_forward_message(data):
        if not bot_proxy_supported:
            return
        sid = request.sid
        try:
            ws = create_bot_connection(sid)
            if ws is None:
                return
            if ws.sock and ws.sock.connected:
                ws.send(data)
            else:
                if sid in bot_gateway_clients:
                    del bot_gateway_clients[sid]
                ws = create_bot_connection(sid)
        except Exception:
            if sid in bot_gateway_clients:
                del bot_gateway_clients[sid]

    @socketio.on('disconnect')
    def bot_disconnect():
        sid = request.sid
        if sid in bot_gateway_clients:
            try:
                bot_gateway_clients[sid].close()
            except Exception:
                pass
            del bot_gateway_clients[sid]
