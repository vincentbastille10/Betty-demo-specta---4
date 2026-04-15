from flask import Flask, request, jsonify
from flask import send_file

app = Flask(__name__)

# ===== PETITE MÉMO SESSION (léger mais efficace) =====
sessions = {}

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {
            "step": 0,
            "prenom": None,
            "email": None
        }
    return sessions[user_id]


# ===== ROUTE PRINCIPALE =====
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    msg = message.lower()

    user_id = request.remote_addr
    s = get_session(user_id)

    # ===== STEP 0 → ACCROCHE =====
    if s["step"] == 0:
        s["step"] = 1
        return jsonify({
            "response": "Bonjour 🙂 Je suis Betty.\n\nJe peux vous ramener des clients automatiquement.\n\nVous êtes dans quel domaine ?"
        })

    # ===== STEP 1 → CONTEXTE BUSINESS =====
    if s["step"] == 1:
        s["business"] = message
        s["step"] = 2
        return jsonify({
            "response": f"Parfait 👍\n\nBetty peut répondre à vos visiteurs et récupérer leurs coordonnées.\n\nVous avez déjà un site web ?"
        })

    # ===== STEP 2 → QUALIF =====
    if s["step"] == 2:
        s["site"] = message
        s["step"] = 3
        return jsonify({
            "response": "Très bien.\n\nEn général, combien de visiteurs avez-vous par jour ? (même approximatif)"
        })

    # ===== STEP 3 → PROJECTION =====
    if s["step"] == 3:
        s["traffic"] = message
        s["step"] = 4
        return jsonify({
            "response": "Ok 👍\n\nAvec Betty, une partie de ces visiteurs devient des prospects qualifiés automatiquement.\n\nVous voulez essayer gratuitement ?"
        })

    # ===== STEP 4 → CLOSE =====
    if s["step"] == 4:
        s["step"] = 5
        return jsonify({
            "response": "👉 Activez votre Betty ici :\nhttps://mybetty.online/inscription\n\n(7 jours gratuits, sans carte)"
        })

    # ===== RÉPONSES INTELLIGENTES SIMPLES =====

    # intention forte
    if any(word in msg for word in ["client", "lead", "prospect", "business", "argent", "vente"]):
        return jsonify({
            "response": "Betty capte automatiquement les visiteurs intéressés et vous envoie leurs coordonnées.\n\n👉 Essayez ici : https://mybetty.online/inscription"
        })

    # prix
    if any(word in msg for word in ["prix", "tarif", "combien"]):
        return jsonify({
            "response": "Vous pouvez tester gratuitement pendant 7 jours.\n\n👉 Activez ici : https://mybetty.online/inscription"
        })

    # fonctionnement
    if any(word in msg for word in ["comment", "fonctionne", "marche"]):
        return jsonify({
            "response": "Betty discute avec vos visiteurs, récupère leurs infos et vous envoie des leads prêts à être rappelés.\n\n👉 Testez ici : https://mybetty.online/inscription"
        })

    # fallback
    return jsonify({
        "response": "Betty transforme vos visiteurs en clients automatiquement.\n\n👉 Essayez gratuitement : https://mybetty.online/inscription"
    })



@app.route("/")
def serve_ui():
    return send_file("chat.html")

