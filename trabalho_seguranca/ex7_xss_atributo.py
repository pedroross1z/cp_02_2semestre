from flask import Flask, render_template_string
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB_NAME

app = Flask(__name__)

TEMPLATE_SEGURO = """
<!doctype html>
<title>Dashboard seguro</title>
<table>
{% for incidente in incidentes %}
  <tr>
    <td>{{ incidente.titulo }}</td>
    <td><img src="/icone.png" alt="{{ incidente.ativo }}"></td>
  </tr>
{% endfor %}
</table>
"""

NOTA_SAFE_MAL_COLOCADO = (
    "Um |safe mal colocado devolve o texto ao autoescape desligado: o valor "
    "deixa de ser tratado como dado e volta a ser interpretado como HTML, "
    "reabrindo o mesmo XSS que o escape por padrão do Jinja2 fecha."
)


@app.after_request
def aplicar_csp(resposta):
    resposta.headers["Content-Security-Policy"] = "default-src 'self'"
    return resposta


def colecao_incidentes():
    return MongoClient(MONGO_URI)[MONGO_DB_NAME].incidentes_dashboard


def preparar_incidentes():
    colecao = colecao_incidentes()
    colecao.delete_many({})
    colecao.insert_many(
        [
            {"titulo": "<script>alert('xss1')</script>", "ativo": "SRV-WEB01"},
            {"titulo": "Tentativa de acesso", "ativo": "x\" onerror=\"alert('xss2')"},
        ]
    )
    return colecao


@app.route("/dashboard")
def dashboard():
    incidentes = list(colecao_incidentes().find({}, {"_id": 0}))
    return render_template_string(TEMPLATE_SEGURO, incidentes=incidentes)


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    incidentes = list(colecao_incidentes().find({}, {"_id": 0}))
    linhas = ""
    for incidente in incidentes:
        linhas += (
            f"<tr><td>{incidente['titulo']}</td>"
            f"<td><img src=\"/icone.png\" alt=\"{incidente['ativo']}\"></td></tr>"
        )
    return f"<!doctype html><title>Dashboard INSEGURO (apenas comparação)</title><table>{linhas}</table>"


if __name__ == "__main__":
    preparar_incidentes()
    app.run(port=5003)
