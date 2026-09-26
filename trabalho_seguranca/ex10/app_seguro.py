import os
from flask import Flask, request, jsonify, render_template_string
import mysql.connector

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD"),
    "database": os.environ.get("MYSQL_DATABASE", "seguranca"),
}

NIVEL_MINIMO_PARA_APAGAR = 5

TEMPLATE_PERFIL = "<h1>Bem-vindo, {{ usuario }}</h1>"


def db():
    return mysql.connector.connect(**DB_CONFIG)


@app.after_request
def aplicar_headers_seguranca(resposta):
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Content-Security-Policy"] = "default-src 'self'"
    return resposta


def autenticar_admin():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    conexao = db()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT id, nivel FROM usuarios WHERE api_key = %s", (api_key,))
    usuario = cursor.fetchone()
    conexao.close()
    return usuario


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")
    conexao = db()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT id, nome FROM usuarios WHERE nome LIKE %s", (f"%{nome}%",))
    resultado = cursor.fetchall()
    conexao.close()
    return jsonify(resultado)


@app.route("/perfil")
def perfil():
    return render_template_string(TEMPLATE_PERFIL, usuario=request.args.get("u", ""))


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
def remover(uid):
    usuario = autenticar_admin()
    if usuario is None:
        return jsonify({"erro": "não autenticado"}), 401
    if usuario["nivel"] < NIVEL_MINIMO_PARA_APAGAR:
        return jsonify({"erro": "acesso não permitido"}), 403

    conexao = db()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
    conexao.commit()
    conexao.close()
    return jsonify({"removido": uid}), 200


@app.route("/api/relatorio")
def relatorio():
    try:
        conexao = db()
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM tabela_inexistente")
        resultado = cursor.fetchall()
        conexao.close()
        return jsonify(resultado)
    except Exception:
        return jsonify({"erro": "erro interno"}), 500


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.environ.get("PORT", 5011)))
