from datetime import datetime
import mysql.connector
from pymongo import MongoClient
from config import MYSQL_CONFIG, MONGO_URI, MONGO_DB_NAME

USUARIOS = [(1, "ana", "ana@x.com", 5), (2, "bruno", "bruno@x.com", 2), (3, "caio", "caio@x.com", 1)]


def preparar_mysql():
    conexao = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conexao.cursor()
    cursor.execute("DROP TABLE IF EXISTS usuarios")
    cursor.execute(
        """
        CREATE TABLE usuarios (
            id INT PRIMARY KEY,
            nome VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL,
            nivel_acesso INT NOT NULL
        )
        """
    )
    cursor.executemany(
        "INSERT INTO usuarios (id, nome, email, nivel_acesso) VALUES (%s, %s, %s, %s)", USUARIOS
    )
    conexao.commit()
    return conexao


def buscar_nivel(cursor, usuario_id):
    cursor.execute("SELECT nivel_acesso FROM usuarios WHERE id = %s", (usuario_id,))
    linha = cursor.fetchone()
    return linha[0] if linha else None


def registrar_auditoria(colecao, quem, alvo, nivel_anterior, nivel_novo, resultado):
    colecao.insert_one(
        {
            "quem": quem,
            "alvo": alvo,
            "nivel_anterior": nivel_anterior,
            "nivel_novo": nivel_novo,
            "resultado": resultado,
            "timestamp": datetime.now(),
        }
    )


def alterar_nivel(conexao, colecao, admin_id, alvo_id, novo_nivel):
    cursor = conexao.cursor()
    conexao.start_transaction()

    nivel_alvo_atual = buscar_nivel(cursor, alvo_id)

    if admin_id == alvo_id:
        conexao.rollback()
        registrar_auditoria(colecao, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "RECUSADO")
        return False, "auto-promoção não é permitida"

    nivel_admin = buscar_nivel(cursor, admin_id)
    if nivel_admin is None or nivel_admin < 5:
        conexao.rollback()
        registrar_auditoria(colecao, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "RECUSADO")
        return False, "admin sem privilégio suficiente"

    if nivel_alvo_atual is None:
        conexao.rollback()
        registrar_auditoria(colecao, admin_id, alvo_id, None, novo_nivel, "RECUSADO")
        return False, "alvo inexistente"

    cursor.execute("UPDATE usuarios SET nivel_acesso = %s WHERE id = %s", (novo_nivel, alvo_id))
    conexao.commit()
    registrar_auditoria(colecao, admin_id, alvo_id, nivel_alvo_atual, novo_nivel, "ACEITO")
    return True, "alteração aplicada"


def executar():
    conexao = preparar_mysql()
    colecao = MongoClient(MONGO_URI)[MONGO_DB_NAME].auditoria
    colecao.delete_many({})

    testes = [(1, 2, 4), (2, 3, 5), (1, 1, 9), (1, 99, 3)]
    for admin_id, alvo_id, novo_nivel in testes:
        sucesso, motivo = alterar_nivel(conexao, colecao, admin_id, alvo_id, novo_nivel)
        estado = "OK" if sucesso else "RECUSADO"
        print(f"alterar_nivel({admin_id}, {alvo_id}, {novo_nivel}) -> {estado} ({motivo})")

    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, nivel_acesso FROM usuarios ORDER BY id")
    for linha in cursor.fetchall():
        print(linha)

    total = colecao.count_documents({})
    recusados = colecao.count_documents({"resultado": "RECUSADO"})
    print(f"Trilha de auditoria ao final: {total} documentos")
    print(f"db.auditoria.count_documents({{'resultado':'RECUSADO'}}) -> {recusados}")

    conexao.close()


if __name__ == "__main__":
    executar()
