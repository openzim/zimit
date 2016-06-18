from socketio import namespace, socketio_manage


class LogsNamespace(namespace.BaseNamespace):
    def on_read(self, filename):
        self.emit('chat', "yeah")


def socketio_service(request):
    socketio_manage(request.environ, {'/logs': LogsNamespace},
                    request)
    return "out"
