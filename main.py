from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
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
TELEFONE_DONO      = "5562981295911"


@app.route('/')
def index():
    """Mostra a tela de controle de estoque."""
    return send_from_directory('static', 'index.html')


@app.route('/lista-compras', methods=['POST'])
def lista_compras():
    """
    Recebe a lista de produtos abaixo do mínimo e envia
    UMA ÚNICA mensagem consolidada no WhatsApp.
    """
    dados = request.get_json()

    produtos = dados.get('produtos', [])
    telefone = dados.get('telefone', TELEFONE_DONO)

    if not produtos:
        return jsonify({"ok": False, "detalhe": "Nenhum produto para enviar"}), 400

    agora = datetime.now().strftime("%d/%m %H:%M")

    linhas = []
    for p in produtos:
        nome    = p.get('nome', '')
        qtd     = p.get('quantidade', 0)
        minimo  = p.get('minimo', 0)
        unidade = p.get('unidade', '')
        linhas.append(f"📦 *{nome}* — {qtd}{unidade} (mín: {minimo}{unidade})")

    lista_formatada = "\n".join(linhas)

    mensagem = (
        f"🛒 *LISTA DE COMPRAS - REPOSIÇÃO*\n"
        f"🕐 {agora}\n\n"
        f"{lista_formatada}\n\n"
        f"{len(produtos)} produto(s) precisam de reposição. Providencie a compra! 🙏"
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
