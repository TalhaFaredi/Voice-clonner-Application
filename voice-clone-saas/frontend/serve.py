"""Standalone local frontend server. No backend code is imported."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import os
from urllib.parse import unquote,urlsplit

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)

    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' http://localhost:8010 http://127.0.0.1:8010; media-src 'self' blob: http://localhost:8010 http://127.0.0.1:8010; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'")
        super().end_headers()

    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if (any(p.startswith('.') for p in path.split('/')) or
                (path not in ('/','/index.html') and not path.startswith(('/src/','/public/')))):
            self.send_error(404)
            return
        super().do_GET()


if __name__=='__main__':
    port = int(os.getenv('FRONTEND_PORT','5173'))
    print(f'Sonora frontend: http://localhost:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
