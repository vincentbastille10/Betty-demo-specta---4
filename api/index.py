from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/api/test")
def test():
    return jsonify({"ok": True})
