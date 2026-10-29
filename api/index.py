from flask import Flask, request, Response
import urllib.request
import urllib.error
import json

app = Flask(__name__)

@app.route('/api/shiki/<path:subpath>', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/shiki', defaults={'subpath': ''}, methods=['GET', 'POST', 'OPTIONS'])
def proxy(subpath):
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, '
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    # Проксирование внешних API по параметру ?url=
    external_url = request.args.get('url')
    if external_url:
        target_url = external_url
    else:
        if subpath == 'graphql' or subpath.startswith('graphql'):
            target_url = 'https://shikimori.io/api/graphql'
        else:
            target_url = 'https://shikimori.io/api'
            if subpath:
                target_url += '/' + subpath

    data = None
    if request.method == 'POST':
        data = request.get_data()

    req = urllib.request.Request(target_url, data=data, method=request.method)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
    if request.method == 'POST':
        req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res_data = r.read()
            response = Response(res_data, status=200)
            response.headers['Content-Type'] = 'application/json'
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response
    except urllib.error.HTTPError as e:
        return Response(
            json.dumps({'error': f'HTTP Error {e.code}: {e.reason}'}),
            status=e.code,
            mimetype='application/json',
            headers={'Access-Control-Allow-Origin': '*'}
        )
    except Exception as e:
        return Response(
            json.dumps({'error': str(e)}),
            status=500,
            mimetype='application/json',
            headers={'Access-Control-Allow-Origin': '*'}
        )

if __name__ == '__main__':
    app.run()
