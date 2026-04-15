from flask import Flask, request, jsonify
import yaml, os, requests, traceback

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
    return jsonify({
        "pack_path":   PACK_PATH,
        "pack_exists": os.path.exists(PACK_PATH),
        "api_key_set": bool(os.environ.get("TOGETHER_API_KEY", "")),
        "model":       os.environ.get("LLM_MODEL", "(non défini)"),
        "max_tokens":  os.environ.get("LLM_MAX_TOKENS", "(non défini)"),
        "cwd":         os.getcwd(),
        "file":        os.path.abspath(__file__)
    })

@app.route("/api/chat-test")
def chat_test():
    """Route GET pour tester l'API directement depuis le navigateur."""
    try:
        pack          = load_pack()
        system_prompt = pack.get("prompt", "")[:100]  # 100 premiers chars pour debug
    except Exception as e:
        return jsonify({"step": "load_pack", "error": str(e)}), 500

    api_key    = os.environ.get("TOGETHER_API_KEY", "")
    model      = os.environ.get("LLM_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "512"))

    if not api_key:
        return jsonify({"step": "api_key", "error": "TOGETHER_API_KEY manquante"}), 500

    try:
        resp = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": "Dis juste 'OK' pour confirmer que tu fonctionnes."}
                ]
            },
            timeout=25
        )
    except Exception as e:
        return jsonify({"step": "http_call", "error": str(e)}), 500

    if not resp.ok:
        return jsonify({"step": "together_error", "status": resp.status_code, "detail": resp.text}), 502

    try:
        result = resp.json()
        reply  = result["choices"][0]["message"]["content"]
        return jsonify({"ok": True, "reply": reply, "model": model})
    except Exception as e:
        return jsonify({"step": "parse", "error": str(e), "raw": resp.text[:500]}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data    = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "message requis"}), 400

        # --- chargement du prompt système ---
        try:
            pack          = load_pack()
            system_prompt = pack.get("prompt", "")
        except Exception as e:
            return jsonify({"error": "Impossible de lire le pack YAML", "detail": str(e)}), 500

        # --- config ---
        api_key    = os.environ.get("TOGETHER_API_KEY", "")
        model      = os.environ.get("LLM_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1")
        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "512"))

        if not api_key:
            return jsonify({"error": "TOGETHER_API_KEY manquante"}), 500

        # --- appel Together AI ---
        try:
            resp = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json"
                },
                json={
                    "model":      model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": message}
                    ]
                },
                timeout=25
            )
        except requests.exceptions.Timeout:
            return jsonify({"error": "Timeout Together AI (>25s)"}), 504
        except Exception as e:
            return jsonify({"error": "Erreur réseau Together AI", "detail": str(e)}), 500

        # --- réponse Together AI en erreur ---
        if not resp.ok:
            return jsonify({
                "error":  "Together AI a retourné une erreur",
                "status": resp.status_code,
                "detail": resp.text
            }), 502

        # --- parsing ---
        try:
            result = resp.json()
            reply  = result["choices"][0]["message"]["content"]
        except Exception as e:
            return jsonify({
                "error":  "Impossible de parser la réponse Together AI",
                "detail": str(e),
                "raw":    resp.text[:500]
            }), 500

        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({
            "error":     "Erreur interne inattendue",
            "detail":    str(e),
            "traceback": traceback.format_exc()
        }), 500
