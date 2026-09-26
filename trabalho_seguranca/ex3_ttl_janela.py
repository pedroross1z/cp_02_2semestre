import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

NOTA_TTL = (
    "O TTL é decisão de segurança, não só de disco: log antigo demais some da "
    "janela de detecção de um analista, mas continua exposto para quem quiser "
    "vazá-lo depois; expirar reduz a superfície de ataque do dado retido."
)


def preparar_colecao():
    cliente = MongoClient(MONGO_URI)
    colecao = cliente[MONGO_DB_NAME].eventos
    colecao.delete_many({})
    colecao.create_index("timestamp", expireAfterSeconds=604800)
    return colecao


def gerar_eventos(quantidade=200, agora=None):
    agora = agora or datetime.now()
    eventos = []
    for _ in range(quantidade):
        instante = agora - timedelta(hours=random.uniform(0, 24))
        pico = 2 <= instante.hour <= 3
        chance_falha = 0.75 if pico else 0.12
        status = "falha" if random.random() < chance_falha else "sucesso"
        eventos.append({"timestamp": instante, "status": status})
    return eventos


def falhas_por_hora(colecao):
    pipeline = [
        {"$match": {"status": "falha"}},
        {"$group": {"_id": {"$hour": "$timestamp"}, "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    return list(colecao.aggregate(pipeline))


def eventos_na_janela(colecao, horas=6, agora=None):
    agora = agora or datetime.now()
    limite = agora - timedelta(hours=horas)
    return list(colecao.find({"timestamp": {"$gte": limite}}))


def imprimir_distribuicao(distribuicao):
    print("=== Falhas por hora (últimas 24h) ===")
    if not distribuicao:
        print("Nenhuma falha registrada na janela.")
        return
    pico = max(distribuicao, key=lambda item: item["total"])
    for item in distribuicao:
        hora, total = item["_id"], item["total"]
        barra = "█" * max(1, total // 3)
        marcador = "  <- pico" if item["_id"] == pico["_id"] else ""
        print(f"{hora:02d}h | {barra} {total}{marcador}")
    print(f"Hora de pico: {pico['_id']:02d}h ({pico['total']} falhas)")


def executar():
    colecao = preparar_colecao()
    colecao.insert_many(gerar_eventos(200))

    distribuicao = falhas_por_hora(colecao)
    imprimir_distribuicao(distribuicao)

    print("Índice TTL ativo: eventos com mais de 7 dias serão removidos automaticamente.")
    print(NOTA_TTL)

    janela = eventos_na_janela(colecao, horas=6)
    print(f"Eventos nas últimas 6h: {len(janela)}")


if __name__ == "__main__":
    executar()
