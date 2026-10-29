from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        if path.startswith('/api/shiki'):
            target_path = path.replace('/api/shiki', '')
        else:
            target_path = path

        url = 'https://shikimori.io/api' + target_path

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'MyAnimeApp/1.0 (contact@example.com)')

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
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
