from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import os

SAVE_DIR = os.path.abspath(os.path.dirname(__file__))

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()

    def do_POST(self):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        filename = query.get('filename', ['data.bin'])[0]
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        target_path = os.path.join(SAVE_DIR, filename)
        with open(target_path, 'wb') as f:
            f.write(data)
        print(f"Successfully received {filename}: {len(data)} bytes saved to {target_path}")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8765), Handler)
    print("Receiver listening on http://127.0.0.1:8765...")
    server.serve_forever()
