from flask import Flask, request, Response
import urllib.request
import urllib.error
import json

app = Flask(__name__)

@app.route('/api/shiki/<path:subpath>', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/shiki', defaults={'subpath': ''}, methods=['GET', 'POST', 'OPTIONS'])
def shiki_proxy(subpath):
    if request.method == 'OPTIONS':
        return cors_response()

    if subpath == 'graphql' or subpath.startswith('graphql'):
        target_url = 'https://shikimori.io/api/graphql'
    else:
        target_url = 'https://shikimori.io/api'
        if subpath:
            target_url += '/' + subpath

    return make_proxy_request(target_url, request)

@app.route('/api/proxy_external', methods=['GET', 'OPTIONS'])
def external_proxy():
    if request.method == 'OPTIONS':
        return cors_response()
    
    target_url = request.args.get('url')
    if not target_url:
        return Response(json.dumps({'error': 'Missing url parameter'}), status=400, mimetype='application/json')

    return make_proxy_request(target_url, request, is_external=True)

def make_proxy_request(target_url, req_obj, is_external=False):
    data = req_obj.get_data() if req_obj.method == 'POST' else None
    req = urllib.request.Request(target_url, data=data, method=req_obj.method)
    
    # User-Agent обязателен для боору-сайтов и Shikimori
    req.add_header('User-Agent', 'ShikimoriFinderApp/3.0 (contact@example.com)')
    if req_obj.method == 'POST':
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

def cors_response():
    response = Response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

if __name__ == '__main__':
    app.run()
