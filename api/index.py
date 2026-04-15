from flask import Flask, request, jsonify
import yaml, os, requests

app = Flask(__name__)

PACK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pack", "betty_spectra.yaml"
)

def load_pack():
    with open(PACK_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.route("/api/test")
def test():
    return jsonify({"ok": True})

@app.route("/api/debug")
def debug():
    pack_exists = os.path.exists(PACK_PATH)
    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    return jsonify({
        "pack_path": PACK_PATH,
        "pack_exists": pack_exists,
        "api_key_set": api_key_set,
        "cwd": os.getcwd(),
        "file": os.path.abspath(__file__)
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"error": "message requis"}), 400

    pack = load_pack()
    system_prompt = pack.get("prompt", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY manquante"}), 500

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 512,
                "system": system_prompt,
                "messages": [{"role": "user", "content": message}]
            },
            timeout=20
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout API"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not resp.ok:
        return jsonify({"error": "Erreur API", "detail": resp.text}), 502

    result = resp.json()
    reply = result["content"][0]["text"]
    return jsonify({"response": reply})
