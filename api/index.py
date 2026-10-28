from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Ожидаем путь вида /api/shiki/animes?search=...
        if not self.path.startswith('/api/shiki'):
            self.send_response(404)
            self.end_headers()
            return

        # Извлекаем оригинальный путь к Shikimori
        target_path = self.path.replace('/api/shiki', '')
        url = 'https://shikimori.one/api' + target_path

        req = urllib.request.Request(url)
        # Обязательный User-Agent для Shikimori API
        req.add_header('User-Agent', 'MyAnimeApp/1.0 (contact@example.com)')

        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())