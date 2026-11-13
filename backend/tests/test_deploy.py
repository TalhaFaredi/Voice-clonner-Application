import http.client
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from flask import Flask, request
from waitress.server import create_server

from app.serving import server_options

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from backup import backup  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def seen_ip(environ, forwarded):
    app = Flask(__name__)
    app.add_url_rule('/', 'ip', lambda: request.remote_addr)
    options = server_options({**environ, 'PORT': str(free_port())})
    server = create_server(app, **options)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        conn = http.client.HTTPConnection('127.0.0.1', options['port'])
        conn.request('GET', '/', headers={'X-Forwarded-For': forwarded})
        return conn.getresponse().read().decode()
    finally:
        server.close()


class ProxyTests(unittest.TestCase):
    def test_forwarded_header_ignored_without_trusted_proxy(self):
        # A client connecting directly must not be able to spoof its address.
        self.assertEqual(seen_ip({}, '9.9.9.9'), '127.0.0.1')

    def test_real_client_address_used_behind_one_proxy(self):
        self.assertEqual(seen_ip({'TRUSTED_PROXY_COUNT': '1'}, '203.0.113.7'), '203.0.113.7')

    def test_spoofed_extra_hop_is_not_trusted(self):
        # Client sent "1.1.1.1"; the proxy appended the real peer. Only the last hop counts.
        self.assertEqual(seen_ip({'TRUSTED_PROXY_COUNT': '1'}, '1.1.1.1, 203.0.113.7'), '203.0.113.7')


class BackupTests(unittest.TestCase):
    def test_backup_copies_database_and_audio_and_prunes(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = Path(tmp) / 'storage'
            (storage / 'users' / '1').mkdir(parents=True)
            (storage / 'users' / '1' / 'a.wav').write_bytes(b'audio')
            db = sqlite3.connect(storage / 'saas.sqlite3')
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE t(x)')
            db.execute('INSERT INTO t VALUES(42)')
            db.commit()  # still open: data may live only in the WAL
            dest = Path(tmp) / 'out'
            for _ in range(3):
                target = backup(dest, keep=2, storage=storage)
            db.close()
            restored = sqlite3.connect(target / 'saas.sqlite3')
            try:
                self.assertEqual(restored.execute('SELECT x FROM t').fetchone()[0], 42)
            finally:
                restored.close()
            self.assertEqual((target / 'users' / '1' / 'a.wav').read_bytes(), b'audio')
            self.assertEqual(len(list(dest.glob('backup-*'))), 2)


if __name__ == '__main__':
    unittest.main()
