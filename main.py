from flask import Flask, request, jsonify, send_from_directory
import httpx
import os

# Serve a pasta "static" como raiz do site
app = Flask(__name__, static_folder='static', static_url_path='')

# ============================
# CREDENCIAIS EVOLUTION API
# ============================
EVOLUTION_URL      = "https://evolution-api-production-a969.up.railway.app"
EVOLUTION_INSTANCE = "estoque-restaurante"
EVOLUTION_TOKEN    = "405A05D5B63D-4EAC-A4BD-41CD53884251"
TELEFONE_DONO      = "5562996778334"


@app.route('/')
def index():
    """Mostra a tela de controle de estoque."""
    return send_from_directory('static', 'index.html')


@app.route('/alerta', methods=['POST'])
def alerta():
    """Recebe os dados do produto e envia o alerta no WhatsApp via Evolution API."""
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

    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"

    try:
        resposta = httpx.post(
            url,
            json={"number": telefone, "text": mensagem},
            headers={
                "Content-Type": "application/json",
                "apikey": EVOLUTION_TOKEN
            },
            timeout=10.0
        )
        return jsonify({
            "ok": resposta.status_code in (200, 201),
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
