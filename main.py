import json

from flask import Flask, request, render_template
import lcp_gutenberg

app = Flask(__name__)

GALLERY_DATA_PATH = "gallery_data.json"

@app.route("/", methods =["POST","GET"])
def index():
    lcp_gutenberg.update_cache_settings() # Set cache to a temp dir
    user_selections = {}
    titles = lcp_gutenberg.retrieve_titles() 
    if request.method == "GET":
        return render_template("index.html", 
                               titles=titles, 
                               selections = user_selections)
    if request.method == "POST":
        user_selections = request.form
        a_title = user_selections['text 1']
        b_title=user_selections['text 2']
        subseq, a_leading_context, a_trailing_context, b_leading_context, b_trailing_context = lcp_gutenberg.get_lcs(
            a_title=a_title, 
            b_title=b_title)
        return render_template("index.html", 
            titles = titles, 
            subseq = subseq,
            a_leading_context = a_leading_context,
            a_trailing_context = a_trailing_context,
            b_leading_context = b_leading_context,
            b_trailing_context = b_trailing_context,
            a_title = a_title,
            b_title = b_title)

@app.route("/gallery")
def gallery():
    with open(GALLERY_DATA_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return render_template("gallery.html", entries=entries)

# Start the dev server when the script is executed from the command line
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)