from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import json
import urllib.parse

REST_BASE = 'https://shikimori.io/api'
GRAPHQL_URL = 'https://shikimori.io/api/graphql'

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path

        if path.startswith('/api/shiki/search'):
            # REST-поиск (как раньше)
            qs = path.split('?', 1)[1] if '?' in path else ''
            params = urllib.parse.parse_qs(qs)
            search = params.get('q', [''])[0]
            url = f"{REST_BASE}/animes?search={urllib.parse.quote(search)}&limit=10"
            self._proxy_get(url)

        elif path.startswith('/api/shiki/roles/'):
            # REST-роли (как раньше)
            anime_id = path.replace('/api/shiki/roles/', '')
            url = f"{REST_BASE}/animes/{anime_id}/roles?limit=50&page=1"
            # Пагинацию делает фронтенд, запрашивая ?page=N
            qs = path.split('?', 1)[1] if '?' in path else ''
            if qs:
                url = f"{REST_BASE}/animes/{anime_id}/roles?{qs}"
            self._proxy_get(url)

        elif path.startswith('/api/shiki/posters'):
            # GraphQL — только для картинок
            qs = path.split('?', 1)[1] if '?' in path else ''
            params = urllib.parse.parse_qs(qs)
            ids_str = params.get('ids', [''])[0]
            ids = [i for i in ids_str.split(',') if i]
            if not ids:
                self._send_json(200, {})
                return

            # Формируем GraphQL-запрос для списка персонажей
            gql_query = """
            query Posters($ids: [ID!]!) {
              characters(ids: $ids) {
                id
                poster { originalUrl }
              }
            }
            """
            payload = json.dumps({
                "query": gql_query,
                "variables": {"ids": ids}
            }).encode('utf-8')

            req = urllib.request.Request(GRAPHQL_URL, data=payload, method='POST')
            req.add_header('Content-Type', 'application/json')
            req.add_header('User-Agent', 'MyAnimeApp/1.0 (contact@example.com)')
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    data = r.read()
                    self._send_raw(200, data)
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def _proxy_get(self, url):
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'MyAnimeApp/1.0 (contact@example.com)')
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
                self._send_raw(200, data)
        except urllib.error.HTTPError as e:
            self._send_json(e.code, {'error': str(e)})
        except Exception as e:
            self._send_json(500, {'error': str(e)})

    def _send_raw(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status, obj):
        self._send_raw(status, json.dumps(obj).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
