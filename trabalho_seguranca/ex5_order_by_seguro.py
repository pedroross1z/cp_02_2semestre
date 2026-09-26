from flask import Flask, request, jsonify
import mysql.connector
from config import MYSQL_CONFIG

app = Flask(__name__)

COLUNAS = {"data": "criado_em", "sev": "severidade", "ip": "ip_origem"}
ORDEM = {"asc": "ASC", "desc": "DESC"}
TAMANHO_PADRAO = 20
TAMANHO_MAXIMO = 100

NOTA_IDENTIFICADOR_VS_DADO = (
    "LIMIT %s funciona porque o driver manda o valor como DADO, fora do texto\n"
    "do SQL, então o banco só vê um número no lugar certo. ORDER BY %s não\n"
    "funciona porque nome de coluna é IDENTIFICADOR, parte da estrutura da\n"
    "query, e por isso a defesa usa uma whitelist fechada, não um placeholder."
)


def conectar():
    return mysql.connector.connect(**MYSQL_CONFIG)


def preparar_tabela():
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DROP TABLE IF EXISTS eventos")
    cursor.execute(
        """
        CREATE TABLE eventos (
            id INT PRIMARY KEY AUTO_INCREMENT,
            severidade VARCHAR(20),
            ip_origem VARCHAR(45),
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    dados = [
        ("baixa", "10.0.0.1"),
        ("critica", "10.0.0.2"),
        ("media", "10.0.0.3"),
        ("alta", "10.0.0.4"),
        ("critica", "10.0.0.5"),
        ("baixa", "10.0.0.6"),
    ]
    cursor.executemany("INSERT INTO eventos (severidade, ip_origem) VALUES (%s, %s)", dados)
    conexao.commit()
    conexao.close()


@app.route("/api/eventos")
def listar_eventos():
    coluna_pedida = request.args.get("ordenar_por", "data")
    ordem_pedida = request.args.get("ordem", "asc")
    tamanho_pedido = request.args.get("tamanho", str(TAMANHO_PADRAO))

    coluna_sql = COLUNAS.get(coluna_pedida)
    if coluna_sql is None:
        return jsonify({"erro": "campo de ordenação inválido"}), 400

    ordem_sql = ORDEM.get(ordem_pedida)
    if ordem_sql is None:
        return jsonify({"erro": "ordem inválida"}), 400

    if not tamanho_pedido.isdigit():
        return jsonify({"erro": "tamanho deve ser inteiro"}), 400
    tamanho_sql = min(int(tamanho_pedido), TAMANHO_MAXIMO)

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    consulta = f"SELECT * FROM eventos ORDER BY {coluna_sql} {ordem_sql} LIMIT %s"
    cursor.execute(consulta, (tamanho_sql,))
    resultado = cursor.fetchall()
    conexao.close()
    return jsonify(resultado), 200


if __name__ == "__main__":
    preparar_tabela()
    app.run(port=5001)
