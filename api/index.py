from flask import Flask, request, jsonify

app = Flask(__name__)

sessions = {}

def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = {
            "step": 0
        }
    return sessions[user_id]


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()

    user_id = request.remote_addr
    s = get_session(user_id)

    if s["step"] == 0:
        s["step"] = 1
        return jsonify({"response": "Bonjour 🙂 Vous êtes dans quel domaine ?"})

    if s["step"] == 1:
        s["step"] = 2
        return jsonify({"response": "Vous avez déjà un site web ?"})

    if s["step"] == 2:
        s["step"] = 3
        return jsonify({"response": "Combien de visiteurs par jour ?"})

    return jsonify({
        "response": "👉 Activez votre Betty : https://mybetty.online/inscription"
    })
