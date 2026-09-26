from datetime import datetime
import numpy as np
from flask import Flask, request, jsonify
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from config import MONGO_URI, MONGO_DB_NAME

app = Flask(__name__)

AVISO_ACURACIA = (
    "acurácia foi omitida de propósito: com classes desbalanceadas ela esconde "
    "falso negativo, que aqui é o pior erro possível (deixar risco alto passar como baixo)"
)


def gerar_dados_sinteticos(quantidade=400, seed=42):
    rng = np.random.default_rng(seed)
    entradas, rotulos = [], []
    for _ in range(quantidade):
        if rng.random() < 0.5:
            falhas = rng.integers(5, 20)
            portas = rng.integers(5, 15)
            bytes_saida = rng.integers(50000, 200000)
            hora = rng.integers(0, 6)
            rotulo = 1
        else:
            falhas = rng.integers(0, 3)
            portas = rng.integers(0, 3)
            bytes_saida = rng.integers(500, 5000)
            hora = rng.integers(8, 20)
            rotulo = 0
        entradas.append([falhas, portas, bytes_saida, hora])
        rotulos.append(rotulo)
    return np.array(entradas), np.array(rotulos)


ENTRADAS, ROTULOS = gerar_dados_sinteticos()
X_TREINO, X_TESTE, Y_TREINO, Y_TESTE = train_test_split(
    ENTRADAS, ROTULOS, test_size=0.25, random_state=42
)
MODELO = RandomForestClassifier(n_estimators=100, random_state=42)
MODELO.fit(X_TREINO, Y_TREINO)


def validar_features(corpo):
    if not corpo or "features" not in corpo:
        return None, "corpo deve conter 'features'"
    features = corpo["features"]
    if not isinstance(features, list) or len(features) != 4:
        recebidas = len(features) if isinstance(features, list) else 0
        return None, f"esperadas 4 features, recebidas {recebidas}"
    numericas = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in features)
    if not numericas:
        return None, "features devem ser numéricas"
    return features, None


@app.route("/api/triagem", methods=["POST"])
def triagem():
    corpo = request.get_json(silent=True)
    features, erro = validar_features(corpo)
    if erro:
        return jsonify({"erro": erro}), 400

    entrada = np.array([features])
    predicao = int(MODELO.predict(entrada)[0])
    confianca = float(MODELO.predict_proba(entrada)[0][predicao])
    risco = "alto" if predicao == 1 else "baixo"

    MongoClient(MONGO_URI)[MONGO_DB_NAME].previsoes.insert_one(
        {
            "entrada": features,
            "saida": risco,
            "confianca": confianca,
            "timestamp": datetime.now(),
        }
    )

    return jsonify({"risco": risco, "confianca": round(confianca, 2)}), 200


@app.route("/api/modelo/metricas")
def metricas():
    predicoes = MODELO.predict(X_TESTE)
    matriz = confusion_matrix(Y_TESTE, predicoes).tolist()
    return (
        jsonify(
            {
                "precisao": round(float(precision_score(Y_TESTE, predicoes)), 2),
                "recall": round(float(recall_score(Y_TESTE, predicoes)), 2),
                "f1": round(float(f1_score(Y_TESTE, predicoes)), 2),
                "matriz": matriz,
                "aviso": AVISO_ACURACIA,
            }
        ),
        200,
    )


if __name__ == "__main__":
    app.run(port=5004)
