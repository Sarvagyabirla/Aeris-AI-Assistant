"""Same-user local restore signal; no task arguments accepted over this channel."""
import hashlib
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket


def server_name():
    return 'aeris-desktop-' + hashlib.sha256(str(Path.home()).encode()).hexdigest()[:20]


def request_existing_window():
    app = QCoreApplication.instance() or QCoreApplication([])
    socket = QLocalSocket(app)
    socket.connectToServer(server_name())
    if not socket.waitForConnected(500):
        return False
    socket.write(b'restore')
    socket.waitForBytesWritten(500)
    socket.disconnectFromServer()
    return True


class InstanceServer(QLocalServer):
    def __init__(self, restore, parent=None):
        super().__init__(parent)
        self.restore = restore
        self.setSocketOptions(QLocalServer.UserAccessOption)
        # Caller owns the application's Windows mutex before removing a stale endpoint.
        QLocalServer.removeServer(server_name())
        self.listen(server_name())
        self.newConnection.connect(self.connected)

    def connected(self):
        while self.hasPendingConnections():
            socket = self.nextPendingConnection()
            self.restore()  # Connection itself is only a restore request.
            socket.disconnectFromServer()
            socket.deleteLater()
