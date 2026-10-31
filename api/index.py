from flask import Flask, request, Response
import urllib.request
import urllib.error
import json
import os

app = Flask(__name__)

# FIX: домен фронтенда для CORS. Задаётся через env-переменную на Vercel.
# Если фронт и бэк на одном домене — CORS вообще не нужен, но оставим
# на случай локальной разработки (front на :5500, back на :5000).
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "")

# FIX: реальный контакт — Shikimori банит приложения с фейковым UA.
# Поставь свой email/telegram в env-переменную на Vercel.
USER_AGENT = os.environ.get(
    "SHIKI_USER_AGENT",
    "ShikimoriFinderApp/2.0 (set SHIKI_USER_AGENT env var with real contact)"
)

# FIX: whitelist допустимых путей. Только корень API и graphql.
ALLOWED_SUBPATHS = {"", "graphql"}


def _cors_headers():
    """FIX: единая точка установки CORS-заголовков."""
    if ALLOWED_ORIGIN:
        return {"Access-Control-Allow-Origin": ALLOWED_ORIGIN}
    return {}


@app.after_request
def add_cors(response):
    # FIX: централизованно, вместо дублирования в каждом return.
    response.headers.update(_cors_headers())
    return response


@app.route('/api/shiki/<path:subpath>', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/shiki', defaults={'subpath': ''}, methods=['GET', 'POST', 'OPTIONS'])
def proxy(subpath):
    # FIX: OPTIONS — preflight. Отдаём только разрешённые методы/заголовки.
    if request.method == 'OPTIONS':
        response = Response(status=204)
        if ALLOWED_ORIGIN:
            response.headers['Access-Control-Allow-Origin'] = ALLOWED_ORIGIN
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            response.headers['Access-Control-Max-Age'] = '86400'
        return response

    # FIX: whitelist путей — иначе открытый релей на произвольные ручки Shikimori.
    if subpath not in ALLOWED_SUBPATHS:
        return Response(
            json.dumps({'error': 'Forbidden subpath'}),
            status=403,
            mimetype='application/json'
        )

    if subpath == 'graphql':
        target_url = 'https://shikimori.io/api/graphql'
    else:
        target_url = 'https://shikimori.io/api'

    data = None
    if request.method == 'POST':
        data = request.get_data()
        # FIX: ограничим размер тела (защита от мусорных POST).
        if data and len(data) > 64 * 1024:
            return Response(
                json.dumps({'error': 'Payload too large'}),
                status=413,
                mimetype='application/json'
            )

    req = urllib.request.Request(target_url, data=data, method=request.method)
    req.add_header('User-Agent', USER_AGENT)
    if request.method == 'POST':
        req.add_header('Content-Type', 'application/json')

    try:
        # FIX: таймаут 8с — укладываемся в лимит Vercel Hobby (10с).
        with urllib.request.urlopen(req, timeout=8) as r:
            res_data = r.read()
            return Response(res_data, status=200, mimetype='application/json')
    except urllib.error.HTTPError as e:
        return Response(
            json.dumps({'error': f'HTTP Error {e.code}: {e.reason}'}),
            status=e.code,
            mimetype='application/json'
        )
    except urllib.error.URLError as e:
        # FIX: отдельно ловим таймауты/сетевые ошибки — 504.
        return Response(
            json.dumps({'error': f'Upstream unavailable: {e.reason}'}),
            status=504,
            mimetype='application/json'
        )
    except Exception as e:
        return Response(
            json.dumps({'error': str(e)}),
            status=500,
            mimetype='application/json'
        )


if __name__ == '__main__':
    app.run(debug=True)
