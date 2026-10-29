from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.error
import json

GRAPHQL_URL = 'https://shikimori.io/api/graphql'

# GraphQL-запрос для поиска аниме
SEARCH_QUERY = """
query SearchAnime($search: String!) {
  animes(search: $search, limit: 10) {
    id
    name
    russian
    url
    kind
    status
    airedOn { year }
    poster { originalUrl }
  }
}
"""

# GraphQL-запрос для получения персонажей с ролями
ROLES_QUERY = """
query AnimeRoles($id: String!) {
  anime(id: $id) {
    id
    name
    russian
    characterRoles {
      id
      rolesEn
      rolesRu
      character {
        id
        name
        russian
        url
        poster { originalUrl }
      }
    }
  }
}
"""

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        
        # Определяем, какой запрос делать
        if path.startswith('/api/shiki/search'):
            # Извлекаем search из query string
            query_string = path.split('?', 1)[1] if '?' in path else ''
            params = {}
            for pair in query_string.split('&'):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    params[k] = v
            search = params.get('q', '')
            
            gql_query = SEARCH_QUERY
            variables = {"search": search}
            
        elif path.startswith('/api/shiki/roles/'):
            anime_id = path.replace('/api/shiki/roles/', '')
            gql_query = ROLES_QUERY
            variables = {"id": anime_id}
        else:
            self.send_response(404)
            self.end_headers()
            return

        payload = json.dumps({
            "query": gql_query,
            "variables": variables
        }).encode('utf-8')

        req = urllib.request.Request(GRAPHQL_URL, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('User-Agent', 'MyAnimeApp/1.0 (contact@example.com)')

        try:
            with urllib.request.urlopen(req, timeout=20) as r:
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
