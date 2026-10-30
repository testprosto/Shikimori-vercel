from flask import Flask, request, Response, jsonify
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import re
import html

app = Flask(__name__)

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "")
USER_AGENT = os.environ.get(
    "SHIKI_USER_AGENT",
    "ShikimoriFinderApp/2.1 (set SHIKI_USER_AGENT env var with real contact)"
)
ALLOWED_SUBPATHS = {"", "graphql"}

def cors_headers():
    headers = {}
    if ALLOWED_ORIGIN:
        headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        headers["Vary"] = "Origin"
    return headers

@app.after_request
def add_cors(response):
    response.headers.update(cors_headers())
    return response

def fetch_json(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers=headers or {})
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))

@app.route("/api/shiki", defaults={"subpath": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/api/shiki/<path:subpath>", methods=["GET", "POST", "OPTIONS"])
def shikimori_proxy(subpath):
    if request.method == "OPTIONS":
        response = Response(status=204)
        response.headers.update(cors_headers())
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    if subpath not in ALLOWED_SUBPATHS:
        return jsonify({"error": "Forbidden subpath"}), 403

    target_url = "https://shikimori.io/api/graphql" if subpath == "graphql" else "https://shikimori.io/api"
    data = None
    if request.method == "POST":
        data = request.get_data()
        if len(data) > 64 * 1024:
            return jsonify({"error": "Payload too large"}), 413

    req = urllib.request.Request(target_url, data=data, method=request.method)
    req.add_header("User-Agent", USER_AGENT)
    if request.method == "POST":
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=12) as upstream:
            return Response(upstream.read(), status=upstream.status, mimetype="application/json")
    except urllib.error.HTTPError as exc:
        return jsonify({"error": f"Shikimori HTTP {exc.code}: {exc.reason}"}), exc.code
    except urllib.error.URLError as exc:
        return jsonify({"error": f"Shikimori unavailable: {exc.reason}"}), 504
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

def clean_search_name(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^\w\s-]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()[:100]

@app.route("/api/refs", methods=["GET", "OPTIONS"])
def character_references():
    if request.method == "OPTIONS":
        response = Response(status=204)
        response.headers.update(cors_headers())
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    character = clean_search_name(request.args.get("character", ""))
    anime = clean_search_name(request.args.get("anime", ""))
    if not character:
        return jsonify({"items": [], "sources": [], "error": "Character name is required"}), 400

    items, sources, seen = [], [], set()

    # Safebooru is an anime-image source. Restrict to safe-rated posts.
    tags = [character.replace(" ", "_"), "rating:safe"]
    if anime:
        tags.append(anime.replace(" ", "_"))
    safe_url = "https://safebooru.org/index.php?" + urllib.parse.urlencode({
        "page": "dapi", "s": "post", "q": "index", "json": "1",
        "limit": "30", "tags": " ".join(tags)
    })
    try:
        payload = fetch_json(safe_url, headers={"Accept": "application/json"}, timeout=10)
        if isinstance(payload, list):
            for post in payload:
                file_url = post.get("file_url") or post.get("sample_url") or ""
                if not file_url or file_url in seen:
                    continue
                # Safety guard: only explicitly safe posts are accepted.
                if str(post.get("rating", "")).lower() != "s":
                    continue
                seen.add(file_url)
                items.append({
                    "url": file_url,
                    "thumb": post.get("preview_url") or post.get("sample_url") or file_url,
                    "source": "Safebooru",
                    "sourceUrl": "https://safebooru.org/index.php?page=post&s=view&id=" + str(post.get("id", "")),
                    "width": post.get("width"),
                    "height": post.get("height")
                })
        sources.append({"name": "Safebooru", "ok": True, "count": len(items)})
    except Exception as exc:
        sources.append({"name": "Safebooru", "ok": False, "error": str(exc)[:140]})

    # Wikimedia Commons provides another independent source.
    commons_query = " ".join(x for x in [character, anime, "anime"] if x)
    commons_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": commons_query,
        "gsrnamespace": "6", "gsrlimit": "15", "prop": "imageinfo",
        "iiprop": "url", "iiurlwidth": "360", "format": "json"
    })
    try:
        payload = fetch_json(commons_url, headers={"Accept": "application/json"}, timeout=10)
        pages = (payload.get("query") or {}).get("pages") or {}
        count_before = len(items)
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            file_url = info.get("url") or ""
            if not file_url or file_url in seen:
                continue
            if not re.search(r"\.(jpg|jpeg|png|webp)(?:$|\?)", file_url, re.I):
                continue
            seen.add(file_url)
            items.append({
                "url": file_url,
                "thumb": info.get("thumburl") or file_url,
                "source": "Wikimedia Commons",
                "sourceUrl": info.get("descriptionurl") or "https://commons.wikimedia.org/",
                "width": info.get("width"),
                "height": info.get("height")
            })
        sources.append({"name": "Wikimedia Commons", "ok": True, "count": len(items) - count_before})
    except Exception as exc:
        sources.append({"name": "Wikimedia Commons", "ok": False, "error": str(exc)[:140]})

    return jsonify({
        "items": items[:40],
        "sources": sources,
        "query": {"character": character, "anime": anime}
    })

if __name__ == "__main__":
    app.run(debug=True)
