from datetime import datetime, timedelta
import numpy as np
from flask import Flask, request, jsonify
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest
from config import MONGO_URI, MONGO_DB_NAME

app = Flask(__name__)
BLOQUEADOS = {}

NOTA_RISCO_ANOMALIA = (
    "Bloquear por anomalia em vez de regra fixa arrisca falso positivo: um\n"
    "usuário legítimo com pico de uso normal (ex.: recarregando várias abas)\n"
    "pode ser confundido com ataque e perder acesso sem ter feito nada de errado."
)


def identificar_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def colecao_acessos():
    return MongoClient(MONGO_URI)[MONGO_DB_NAME].acessos


@app.before_request
def registrar_inicio():
    ip = identificar_ip()
    bloqueio_ate = BLOQUEADOS.get(ip)
    if bloqueio_ate and datetime.now() < bloqueio_ate:
        resposta = jsonify({"erro": "muitas requisições"})
        resposta.status_code = 429
        resposta.headers["Retry-After"] = "60"
        return resposta

    request._registro_id = colecao_acessos().insert_one(
        {"ip": ip, "rota": request.path, "metodo": request.method, "timestamp": datetime.now()}
    ).inserted_id


@app.after_request
def completar_registro(resposta):
    registro_id = getattr(request, "_registro_id", None)
    if registro_id is not None:
        colecao_acessos().update_one({"_id": registro_id}, {"$set": {"status": resposta.status_code}})
    return resposta


@app.route("/api/dados")
def dados():
    return jsonify({"ok": True}), 200


def extrair_features_por_ip(janela_segundos=60):
    limite = datetime.now() - timedelta(seconds=janela_segundos)
    pipeline = [
        {"$match": {"timestamp": {"$gte": limite}}},
        {
            "$group": {
                "_id": "$ip",
                "total": {"$sum": 1},
                "erros": {"$sum": {"$cond": [{"$gte": ["$status", 400]}, 1, 0]}},
                "rotas": {"$addToSet": "$rota"},
            }
        },
    ]
    resultado = list(colecao_acessos().aggregate(pipeline))
    ips, features = [], []
    for item in resultado:
        req_por_minuto = item["total"] * (60 / janela_segundos)
        taxa_4xx = item["erros"] / item["total"] if item["total"] else 0
        rotas_distintas = len(item["rotas"])
        ips.append(item["_id"])
        features.append([req_por_minuto, taxa_4xx, rotas_distintas])
    return ips, features


def detectar_e_bloquear_anomalos(janela_segundos=60):
    ips, features = extrair_features_por_ip(janela_segundos)
    if len(features) < 2:
        return {}

    modelo = IsolationForest(contamination=0.2, random_state=42)
    rotulos = modelo.fit_predict(np.array(features))

    resultado = {}
    for ip, feats, rotulo in zip(ips, features, rotulos):
        anomalo = rotulo == -1
        resultado[ip] = {"features": feats, "anomalo": anomalo}
        if anomalo:
            BLOQUEADOS[ip] = datetime.now() + timedelta(seconds=60)
    return resultado


if __name__ == "__main__":
    app.run(port=5005)
