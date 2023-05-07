from flask import Flask, request, render_template
import lcs

app = Flask(__name__)

@app.route("/", methods =["POST","GET"])
def index():
    lcs.update_cache_settings()
    user_selections = {}
    pg_catalog = lcs.retrieve_metadata()
    titles = pg_catalog.cleaned_title.to_list()
    if request.method == "GET":
        return render_template("index.html", titles=titles, selections = user_selections)
    if request.method == "POST":
        user_selections = request.form
        a_code = lcs.get_ID(user_selections['text 1'])
        b_code = lcs.get_ID(user_selections['text 2'])
        subseq, a_context, b_context = lcs.get_lcs(a_code=a_code, b_code=b_code)
        return render_template("index.html", 
                               titles = titles, 
                               subseq = subseq,
                               a_context = a_context,
                               b_context = b_context)

# start the dev server when the script is executed from the command line
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)