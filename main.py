import gzip
import json

from flask import Flask, request, render_template, make_response
import lcp_gutenberg

app = Flask(__name__)

GALLERY_DATA_PATH = "gallery_data.json"

_titles_json_cache = None
_titles_json_gzip_cache = None

@app.route("/titles.json")
def titles_json():
    # Autocomplete data (~7MB) is fetched separately from the initial page
    # so it doesn't block first render; cached (both the list and its
    # serialized/gzipped forms) since the catalog doesn't change at runtime.
    # Gzipped since JSON text compresses ~5-10x and gunicorn/Cloud Run don't
    # compress responses on their own.
    global _titles_json_cache, _titles_json_gzip_cache
    if _titles_json_cache is None:
        _titles_json_cache = json.dumps(lcp_gutenberg.retrieve_titles())
        _titles_json_gzip_cache = gzip.compress(_titles_json_cache.encode("utf-8"))
    if "gzip" in request.headers.get("Accept-Encoding", ""):
        response = make_response(_titles_json_gzip_cache)
        response.headers["Content-Encoding"] = "gzip"
    else:
        response = make_response(_titles_json_cache)
    response.headers["Content-Type"] = "application/json"
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Vary"] = "Accept-Encoding"
    return response

@app.route("/", methods =["POST","GET"])
def index():
    lcp_gutenberg.update_cache_settings() # Set cache to a temp dir
    user_selections = {}
    if request.method == "GET":
        return render_template("index.html",
                               selections = user_selections)
    if request.method == "POST":
        user_selections = request.form
        a_title = user_selections['text 1']
        b_title=user_selections['text 2']
        subseq, a_leading_context, a_trailing_context, b_leading_context, b_trailing_context = lcp_gutenberg.get_lcs(
            a_title=a_title,
            b_title=b_title)
        a_id = lcp_gutenberg.get_ID(a_title)
        b_id = lcp_gutenberg.get_ID(b_title)
        a_author = lcp_gutenberg.get_author(a_title)
        b_author = lcp_gutenberg.get_author(b_title)
        return render_template("index.html",
            subseq = subseq,
            a_leading_context = a_leading_context,
            a_trailing_context = a_trailing_context,
            b_leading_context = b_leading_context,
            b_trailing_context = b_trailing_context,
            a_title = a_title,
            b_title = b_title,
            a_id = a_id,
            b_id = b_id,
            a_author = a_author,
            b_author = b_author)

@app.route("/gallery")
def gallery():
    with open(GALLERY_DATA_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return render_template("gallery.html", entries=entries)

# Start the dev server when the script is executed from the command line
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)