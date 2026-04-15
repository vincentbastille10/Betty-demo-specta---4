from flask import Flask, request, jsonify
import yaml, os, requests, traceback, re

app = Flask(__name__)

PACK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "pack", "betty_spectra.yaml"
)
LEAD_EMAIL = "spectramediabots@gmail.com"

def load_pack():
    with open(PACK_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def extract_lead(text):
    """Détecte le marqueur CAPTURE: name=[...] email=[...] phone=[...]"""
    match = re.search(
        r'CAPTURE:\s*name=\[([^\]]*)\]\s*email=\[([^\]]*)\]\s*phone=\[([^\]]*)\]',
        text, re.IGNORECASE
    )
    if match:
        return {
            "name":  match.group(1).strip(),
            "email": match.group(2).strip(),
            "phone": match.group(3).strip()
        }
    return None

def send_lead_email(lead):
    """Envoie le lead par email via Mailjet."""
    mj_public  = os.environ.get("MJ_APIKEY_PUBLIC", "")
    mj_private = os.environ.get("MJ_APIKEY_PRIVATE", "")
    if not mj_public or not mj_private:
        return False, "clés Mailjet manquantes"

    body = (
        f"🎯 Nouveau lead capté par Betty Demo\n\n"
        f"Prénom   : {lead.get('name')  or '-'}\n"
        f"Email    : {lead.get('email') or '-'}\n"
        f"Téléphone: {lead.get('phone') or '-'}\n\n"
        f"---\nCapté via betty-demo-specta-4.vercel.app"
    )
    try:
        resp = requests.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(mj_public, mj_private),
            json={
                "Messages": [{
                    "From": {"Email": LEAD_EMAIL, "Name": "Betty Demo"},
                    "To":   [{"Email": LEAD_EMAIL, "Name": "Spectra Media"}],
                    "Subject": f"🎯 Lead Betty : {lead.get('name') or 'Nouveau contact'}",
                    "TextPart": body
                }]
            },
            timeout=10
        )
        return resp.ok, resp.text
    except Exception as e:
        return False, str(e)


@app.route("/api/test")
def test():
    return jsonify({"ok": True})


@app.route("/api/debug")
def debug():
    return jsonify({
        "pack_exists": os.path.exists(PACK_PATH),
        "api_key_set": bool(os.environ.get("TOGETHER_API_KEY")),
        "mj_set":      bool(os.environ.get("MJ_APIKEY_PUBLIC")),
        "model":       os.environ.get("LLM_MODEL", "(non défini)"),
        "max_tokens":  os.environ.get("LLM_MAX_TOKENS", "(non défini)"),
    })


@app.route("/api/chat-test")
def chat_test():
    try:
        pack = load_pack()
        system_prompt = pack.get("prompt", "")[:100]
    except Exception as e:
        return jsonify({"step": "load_pack", "error": str(e)}), 500

    api_key    = os.environ.get("TOGETHER_API_KEY", "")
    model      = os.environ.get("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "200"))

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
                    {"role": "user", "content": "Dis juste OK pour confirmer."}
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
        history = data.get("history", [])   # [{role, content}, ...]

        if not message:
            return jsonify({"error": "message requis"}), 400

        # --- chargement prompt système ---
        try:
            pack          = load_pack()
            system_prompt = pack.get("prompt", "")
        except Exception as e:
            return jsonify({"error": "Impossible de lire le pack YAML", "detail": str(e)}), 500

        api_key    = os.environ.get("TOGETHER_API_KEY", "")
        model      = os.environ.get("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "200"))

        if not api_key:
            return jsonify({"error": "TOGETHER_API_KEY manquante"}), 500

        # --- construction des messages avec historique ---
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-12:]:   # max 12 messages d'historique
            role    = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

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
                    "messages":   messages
                },
                timeout=25
            )
        except requests.exceptions.Timeout:
            return jsonify({"error": "Timeout Together AI (>25s)"}), 504
        except Exception as e:
            return jsonify({"error": "Erreur réseau", "detail": str(e)}), 500

        if not resp.ok:
            return jsonify({
                "error":  "Together AI a retourné une erreur",
                "status": resp.status_code,
                "detail": resp.text
            }), 502

        # --- parsing réponse ---
        try:
            result     = resp.json()
            raw_reply  = result["choices"][0]["message"]["content"]
        except Exception as e:
            return jsonify({"error": "Impossible de parser la réponse", "detail": str(e)}), 500

        # --- détection lead + envoi email ---
        lead          = extract_lead(raw_reply)
        clean_reply   = re.sub(r'\nCAPTURE:.*', '', raw_reply, flags=re.IGNORECASE | re.DOTALL).strip()
        lead_captured = False

        if lead and (lead.get("email") or lead.get("phone")):
            ok, _ = send_lead_email(lead)
            lead_captured = ok

        return jsonify({
            "response":      clean_reply,
            "lead_captured": lead_captured
        })

    except Exception as e:
        return jsonify({
            "error":     "Erreur interne",
            "detail":    str(e),
            "traceback": traceback.format_exc()
        }), 500
