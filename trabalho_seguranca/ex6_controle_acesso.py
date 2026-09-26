from flask import Flask, request, jsonify
import mysql.connector
from config import MYSQL_CONFIG

app = Flask(__name__)

NIVEL_MINIMO_PARA_APAGAR_QUALQUER = 5


def conectar():
    return mysql.connector.connect(**MYSQL_CONFIG)


def preparar_tabelas():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DROP TABLE IF EXISTS incidentes")
    cursor.execute("DROP TABLE IF EXISTS analistas")
    cursor.execute(
        """
        CREATE TABLE analistas (
            id INT PRIMARY KEY,
            nome VARCHAR(50) NOT NULL,
            api_key VARCHAR(50) UNIQUE NOT NULL,
            nivel INT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE incidentes (
            id INT PRIMARY KEY,
            dono_id INT NOT NULL,
            titulo VARCHAR(100) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'aberto',
            FOREIGN KEY (dono_id) REFERENCES analistas(id)
        )
        """
    )
    cursor.executemany(
        "INSERT INTO analistas (id, nome, api_key, nivel) VALUES (%s, %s, %s, %s)",
        [(1, "ana", "key-ana-001", 5), (2, "bruno", "key-bruno-002", 2)],
    )
    cursor.executemany(
        "INSERT INTO incidentes (id, dono_id, titulo, severidade) VALUES (%s, %s, %s, %s)",
        [(1, 1, "Brute force SSH", "critica"), (2, 2, "Phishing no RH", "media")],
    )
    conexao.commit()
    conexao.close()


def autenticar():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT id, nome, nivel FROM analistas WHERE api_key = %s", (api_key,))
    analista = cursor.fetchone()
    conexao.close()
    return analista


@app.route("/api/incidentes")
def listar():
    analista = autenticar()
    if analista is None:
        return jsonify({"erro": "não autenticado"}), 401

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    if analista["nivel"] >= NIVEL_MINIMO_PARA_APAGAR_QUALQUER:
        cursor.execute("SELECT * FROM incidentes")
    else:
        cursor.execute("SELECT * FROM incidentes WHERE dono_id = %s", (analista["id"],))
    resultado = cursor.fetchall()
    conexao.close()
    return jsonify(resultado), 200


@app.route("/api/incidentes/<int:incidente_id>")
def obter(incidente_id):
    analista = autenticar()
    if analista is None:
        return jsonify({"erro": "não autenticado"}), 401

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM incidentes WHERE id = %s", (incidente_id,))
    incidente = cursor.fetchone()
    conexao.close()

    if incidente is None:
        return jsonify({"erro": "não encontrado"}), 404
    pode_ver_qualquer = analista["nivel"] >= NIVEL_MINIMO_PARA_APAGAR_QUALQUER
    if not pode_ver_qualquer and incidente["dono_id"] != analista["id"]:
        return jsonify({"erro": "acesso não permitido"}), 403
    return jsonify(incidente), 200


@app.route("/api/incidentes/<int:incidente_id>", methods=["DELETE"])
def remover(incidente_id):
    analista = autenticar()
    if analista is None:
        return jsonify({"erro": "não autenticado"}), 401
    if analista["nivel"] < NIVEL_MINIMO_PARA_APAGAR_QUALQUER:
        return jsonify({"erro": "acesso não permitido"}), 403

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT id FROM incidentes WHERE id = %s", (incidente_id,))
    incidente = cursor.fetchone()
    if incidente is None:
        conexao.close()
        return jsonify({"erro": "não encontrado"}), 404

    cursor.execute("DELETE FROM incidentes WHERE id = %s", (incidente_id,))
    conexao.commit()
    conexao.close()
    return jsonify({"removido": incidente_id}), 200


if __name__ == "__main__":
    preparar_tabelas()
    app.run(port=5002)
