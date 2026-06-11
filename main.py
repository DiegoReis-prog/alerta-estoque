from flask import Flask, request, jsonify, send_from_directory
import httpx
import os

# Serve a pasta "static" como raiz do site
app = Flask(__name__, static_folder='static', static_url_path='')

# ============================
# CREDENCIAIS Z-API
# ============================
ZAPI_INSTANCE = "bc1qmz00uvzyxx0evgw6q06sc2qqy05t6jjqu5t3sd"
ZAPI_TOKEN    = "4C4B08C5DA31D00158D185CD"
ZAPI_CLIENT   = "Fd14d44db1a34418ab7ca7685ae613278S"
TELEFONE_DONO = "5562981295911"


@app.route('/')
def index():
    """Mostra a tela de controle de estoque."""
    return send_from_directory('static', 'index.html')


@app.route('/alerta', methods=['POST'])
def alerta():
    """Recebe os dados do produto e envia o alerta no WhatsApp."""
    dados = request.get_json()

    produto    = dados.get('produto')
    quantidade = dados.get('quantidade')
    minimo     = dados.get('minimo')
    unidade    = dados.get('unidade')
    telefone   = dados.get('telefone', TELEFONE_DONO)

    emoji  = "🚨" if quantidade == 0 else "⚠️"
    status = "ZERADO" if quantidade == 0 else "ABAIXO DO MÍNIMO"

    mensagem = (
        f"{emoji} *ALERTA DE ESTOQUE {status}*\n\n"
        f"📦 Produto: *{produto}*\n"
        f"📉 Atual: *{quantidade} {unidade}*\n"
        f"📊 Mínimo: {minimo} {unidade}\n\n"
        f"Providencie a reposição!"
    )

    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE}/token/{ZAPI_TOKEN}/send-text"

    try:
        resposta = httpx.post(
            url,
            json={"phone": telefone, "message": mensagem},
            headers={"Client-Token": ZAPI_CLIENT},
            timeout=10.0
        )
        return jsonify({
            "ok": resposta.status_code == 200,
            "detalhe": resposta.text
        })
    except Exception as erro:
        return jsonify({"ok": False, "detalhe": str(erro)}), 500


@app.route('/health')
def health():
    """Rota simples para confirmar que o servidor está no ar."""
    return jsonify({"status": "online"})


if __name__ == '__main__':
    porta = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=porta)
