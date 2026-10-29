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
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

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
    req.add_header('User-Agent', 'ShikimoriFinderApp/2.0 (contact@example.com)')
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

# Новый эндпоинт для получения артов из Safebooru без CORS проблем
@app.route('/api/booru', methods=['GET'])
def proxy_booru():
    tag = request.args.get('tag', '').lower().replace(' ', '_')
    if not tag:
        return Response(json.dumps([]), mimetype='application/json', headers={'Access-Control-Allow-Origin': '*'})
    
    target_url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=15&tags={tag}"
    req = urllib.request.Request(target_url, headers={'User-Agent': 'ShikimoriFinderApp/2.0'})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            posts = json.loads(r.read().decode('utf-8'))
            images = []
            for p in posts:
                if 'directory' in p and 'image' in p:
                    img_url = f"https://safebooru.org/images/{p['directory']}/{p['image']}"
                    images.append(img_url)
                elif 'file_url' in p:
                    url = p['file_url']
                    if url.startswith('//'):
                        url = 'https:' + url
                    images.append(url)
            return Response(json.dumps(images), mimetype='application/json', headers={'Access-Control-Allow-Origin': '*'})
    except Exception as e:
        return Response(json.dumps([]), mimetype='application/json', headers={'Access-Control-Allow-Origin': '*'})

if __name__ == '__main__':
    app.run()
