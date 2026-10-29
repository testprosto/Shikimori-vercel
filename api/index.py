from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.handle_request(method='GET')

    def do_POST(self):
        self.handle_request(method='POST')

    def handle_request(self, method):
        path = self.path
        if path.startswith('/api/shiki'):
            target_path = path.replace('/api/shiki', '')
        else:
            target_path = path

        if target_path.startswith('/graphql'):
            url = 'https://shikimori.io/api/graphql'
        else:
            url = 'https://shikimori.io/api' + target_path

        body = None
        if method == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)

        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('User-Agent', 'ShikimoriFinderApp/2.0 (contact@example.com)')
        if method == 'POST':
            req.add_header('Content-Type', 'application/json')

        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
