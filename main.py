from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime
import httpx
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__, static_folder='static', static_url_path='')

# ============================
# BANCO DE DADOS
# ============================
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# O Railway às vezes entrega o endereço como "postgres://"
# mas a biblioteca que usamos exige "postgresql://"
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


def get_db():
    """Abre uma nova conexão com o banco de dados."""
    return psycopg2.connect(DATABASE_URL)


def preparar_banco():
    """
    Cria a tabela de produtos se ela ainda não existir.
    Se a tabela estiver vazia, cadastra os 5 produtos
    que usamos durante os testes.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(200) NOT NULL,
            quantidade REAL NOT NULL DEFAULT 0,
            minimo REAL NOT NULL DEFAULT 0,
            unidade VARCHAR(20) NOT NULL DEFAULT 'un',
            categoria VARCHAR(100) DEFAULT 'Geral'
        )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM produtos")
    total = cur.fetchone()[0]

    if total == 0:
        produtos_iniciais = [
            ("Arroz",        8,  5,  "kg", "Grãos"),
            ("Óleo de soja", 3,  4,  "L",  "Temperos"),
            ("Frango",       12, 10, "kg", "Carnes"),
            ("Feijão",       8,  5,  "kg", "Grãos"),
            ("Sal",          6,  3,  "kg", "Temperos"),
        ]
        cur.executemany(
            """INSERT INTO produtos (nome, quantidade, minimo, unidade, categoria)
               VALUES (%s, %s, %s, %s, %s)""",
            produtos_iniciais
        )
        conn.commit()

    cur.close()
    conn.close()


# Executa ao iniciar o servidor
preparar_banco()


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


# ============================
# PRODUTOS
# ============================

@app.route('/produtos', methods=['GET'])
def listar_produtos():
    """Retorna todos os produtos cadastrados no banco."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, nome, quantidade, minimo, unidade, categoria
        FROM produtos
        ORDER BY id
    """)
    produtos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(produtos)


@app.route('/produtos', methods=['POST'])
def criar_produto():
    """Cadastra um novo produto no banco."""
    dados = request.get_json()

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        INSERT INTO produtos (nome, quantidade, minimo, unidade, categoria)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, nome, quantidade, minimo, unidade, categoria
    """, (
        dados.get('nome'),
        dados.get('quantidade', 0),
        dados.get('minimo', 0),
        dados.get('unidade', 'un'),
        dados.get('categoria', 'Geral'),
    ))
    novo_produto = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(novo_produto), 201


@app.route('/produtos/<int:produto_id>', methods=['PATCH'])
def atualizar_produto(produto_id):
    """Atualiza a quantidade de um produto existente."""
    dados = request.get_json()
    nova_quantidade = dados.get('quantidade')

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE produtos SET quantidade = %s WHERE id = %s",
        (nova_quantidade, produto_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"ok": True})


# ============================
# LISTA DE COMPRAS (WhatsApp)
# ============================

@app.route('/lista-compras', methods=['POST'])
def lista_compras():
    """
    Busca no banco os produtos abaixo do mínimo
    e envia UMA ÚNICA mensagem consolidada no WhatsApp.
    """
    dados = request.get_json(silent=True) or {}
    telefone = dados.get('telefone', TELEFONE_DONO)

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT nome, quantidade, minimo, unidade
        FROM produtos
        WHERE quantidade <= minimo
        ORDER BY nome
    """)
    produtos = cur.fetchall()
    cur.close()
    conn.close()

    if not produtos:
        return jsonify({"ok": False, "detalhe": "Nenhum produto abaixo do mínimo"}), 400

    agora = datetime.now().strftime("%d/%m %H:%M")

    linhas = []
    for p in produtos:
        linhas.append(f"📦 *{p['nome']}* — {p['quantidade']}{p['unidade']} (mín: {p['minimo']}{p['unidade']})")

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
