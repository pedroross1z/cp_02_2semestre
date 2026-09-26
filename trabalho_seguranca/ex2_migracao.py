import mysql.connector
from pymongo import MongoClient
from config import MYSQL_CONFIG, MONGO_URI, MONGO_DB_NAME

ATIVOS = [(1, "SRV-WEB01", "192.168.1.10", "alta"), (2, "PC-RH03", "192.168.1.45", "baixa")]
ALERTAS = [(1, 1, "BRUTE_FORCE", "critica"), (2, 1, "PORT_SCAN", "alta"), (3, 2, "XSS", "media")]

NOTA_MIGRACAO = (
    "Ganha-se leitura sem JOIN: o documento já chega completo para exibir.\n"
    "Perde-se em duplicação: renomear um ativo exige um update_many em todos os alertas dele."
)


def preparar_mysql():
    conexao = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conexao.cursor()
    cursor.execute("DROP TABLE IF EXISTS alertas")
    cursor.execute("DROP TABLE IF EXISTS ativos")
    cursor.execute(
        """
        CREATE TABLE ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            ip VARCHAR(45) UNIQUE NOT NULL,
            criticidade ENUM('baixa', 'media', 'alta') NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
        """
    )
    cursor.executemany("INSERT INTO ativos (id, nome, ip, criticidade) VALUES (%s, %s, %s, %s)", ATIVOS)
    cursor.executemany(
        "INSERT INTO alertas (id, ativo_id, tipo, severidade) VALUES (%s, %s, %s, %s)", ALERTAS
    )
    conexao.commit()
    return conexao


def ler_com_join(conexao):
    cursor = conexao.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT alertas.tipo, alertas.severidade, ativos.nome, ativos.ip, ativos.criticidade
        FROM alertas
        JOIN ativos ON ativos.id = alertas.ativo_id
        """
    )
    return cursor.fetchall()


def montar_documentos(linhas):
    return [
        {
            "tipo": linha["tipo"],
            "severidade": linha["severidade"],
            "ativo": {
                "nome": linha["nome"],
                "ip": linha["ip"],
                "criticidade": linha["criticidade"],
            },
        }
        for linha in linhas
    ]


def migrar():
    conexao = preparar_mysql()
    linhas = ler_com_join(conexao)
    documentos = montar_documentos(linhas)

    cliente = MongoClient(MONGO_URI)
    colecao = cliente[MONGO_DB_NAME].alertas
    colecao.delete_many({})
    colecao.insert_many(documentos)

    cursor = conexao.cursor()
    cursor.execute("SELECT COUNT(*) FROM alertas")
    total_mysql = cursor.fetchone()[0]
    total_mongo = colecao.count_documents({})
    situacao = "MIGRAÇÃO ÍNTEGRA" if total_mysql == total_mongo else "MIGRAÇÃO INCOMPLETA"
    print(f"MySQL: {total_mysql} alertas | MongoDB: {total_mongo} documentos -> {situacao}")

    criticidade_alta = list(colecao.find({"ativo.criticidade": "alta"}))
    print(
        f"Consulta sem JOIN: db.alertas.find({{'ativo.criticidade':'alta'}}) -> "
        f"{len(criticidade_alta)} documentos"
    )

    print(NOTA_MIGRACAO)

    conexao.close()
    return total_mysql, total_mongo


if __name__ == "__main__":
    migrar()
