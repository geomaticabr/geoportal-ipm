"""Servidor local simples com suporte a HTTP Range (necessário para arquivos .pmtiles).
Uso:  python servidor.py   ->  http://localhost:8000
"""
import os, re, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path.split('?', 1)[0])
        if not rng or not os.path.isfile(path):
            return super().do_GET()
        m = re.match(r'bytes=(\d*)-(\d*)', rng)
        size = os.path.getsize(path)
        start = int(m.group(1)) if m and m.group(1) else 0
        end = int(m.group(2)) if m and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            self.send_error(416)
            return
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        with open(path, 'rb') as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, *a):
        pass


class Srv(ThreadingHTTPServer):
    request_queue_size = 256
    daemon_threads = True
    def handle_error(self, *a):
        import traceback; traceback.print_exc()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f'Geoportal em http://localhost:{PORT}  (Ctrl+C para encerrar)')
    Srv(('127.0.0.1', PORT), Handler).serve_forever()


