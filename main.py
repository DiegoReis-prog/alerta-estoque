from flask import Flask, request, jsonify
from flask_cors import CORS
import httpx
import os

app = Flask(__name__)
CORS(app)

ZAPI_INSTANCE = "bc1qmz00uvzyxx0evgw6q06sc2qqy05t6jjqu5t3sd"
ZAPI_TOKEN    = "4C4B08C5DA31D00158D185CD"
ZAPI_CLIENT   = "Fd14d44db1a34418ab7ca7685ae613278S"

@app.route("/alerta", methods=["POST"])
def alerta():
    dados = request.json
    telefone = dados.get("telefone")
    produto  = dados.get("produto")
    quantidade = dados.get("quantidade")
    minimo   = dados.get("minimo")
    unidade  = dados.get("unidade")

    emoji  = "🚨" if quantidade == 0 else "⚠️"
    status = "ZERADO" if quantidade == 0 else "ABAIXO DO MÍNIMO"
    msg = (
        f"{emoji} *ALERTA DE ESTOQUE {status}*\n\n"
        f"📦 Produto: *{produto}*\n"
        f"📉 Atual: *{quantidade} {unidade}*\n"
        f"📊 Mínimo: {minimo} {unidade}\n\n"
        f"Providencie a reposição!"
    )

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"
    r = httpx.post(url, json={"phone": telefone, "message": msg},
                   headers={"Client-Token": ZAPI_CLIENT})

    return jsonify({"ok": r.status_code == 200, "detalhe": r.text})

@app.route("/")
def index():
    return "Servidor de alertas ok!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
