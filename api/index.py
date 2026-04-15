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
    api_key_set = bool(os.environ.get("TOGETHER_API_KEY", ""))
    return jsonify({
        "pack_path": PACK_PATH,
        "pack_exists": pack_exists,
        "api_key_set": api_key_set,
        "model": os.environ.get("LLM_MODEL", "(non défini)"),
        "max_tokens": os.environ.get("LLM_MAX_TOKENS", "(non défini)"),
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

    api_key   = os.environ.get("TOGETHER_API_KEY", "")
    model     = os.environ.get("LLM_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "512"))

    if not api_key:
        return jsonify({"error": "TOGETHER_API_KEY manquante"}), 500

    try:
        resp = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": message}
                ]
            },
            timeout=20
        )
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout API"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not resp.ok:
        return jsonify({"error": "Erreur Together AI", "detail": resp.text}), 502

    result = resp.json()
    reply = result["choices"][0]["message"]["content"]
    return jsonify({"response": reply})
