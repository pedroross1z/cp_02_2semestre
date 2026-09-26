REGRAS_DECISAO = [
    {
        "nome": "acid_e_sensivel",
        "condicao": lambda p: p["precisa_acid"] and p["dado_sensivel"],
        "banco": "MySQL",
        "cap": "CP",
        "risco_owasp": "A07:2021 - Identification and Authentication Failures",
        "justificativa": "autenticar ou autorizar alguém errado é pior do que recusar a operação e ficar fora do ar",
    },
    {
        "nome": "auditoria_sensivel_sem_acid",
        "condicao": lambda p: p["dado_sensivel"] and not p["precisa_acid"] and not p["tolera_atraso_de_consistencia"],
        "banco": "MongoDB",
        "cap": "CP",
        "risco_owasp": "A08:2021 - Software and Data Integrity Failures",
        "justificativa": "uma trilha que diverge do que realmente aconteceu não vale como prova em uma investigação",
    },
    {
        "nome": "acid_sem_sensivel",
        "condicao": lambda p: p["precisa_acid"] and not p["dado_sensivel"],
        "banco": "MySQL",
        "cap": "CP",
        "justificativa": "cobrar duas vezes ou perder um item por falta de atomicidade quebra a regra de negócio",
        "risco_owasp": "A04:2021 - Insecure Design",
    },
    {
        "nome": "escala_com_atraso_tolerado",
        "condicao": lambda p: p["escala_horizontal"] and p["tolera_atraso_de_consistencia"] and not p["dado_sensivel"],
        "banco": "MongoDB",
        "cap": "AP",
        "risco_owasp": "A09:2021 - Security Logging and Monitoring Failures",
        "justificativa": "perder alguns segundos de um dado não sensível é aceitável; parar de aceitar o dado não é",
    },
    {
        "nome": "cache_sensivel_com_disponibilidade",
        "condicao": lambda p: p["escala_horizontal"] and p["tolera_atraso_de_consistencia"] and p["dado_sensivel"] and not p["precisa_acid"],
        "banco": "MongoDB",
        "cap": "AP",
        "risco_owasp": "A02:2021 - Cryptographic Failures",
        "justificativa": "cache indisponível derruba todos os logins; dado sensível em cache exige TTL curto e criptografia em repouso, não consistência forte",
    },
]

REGRA_PADRAO = {
    "banco": "MongoDB",
    "cap": "AP",
    "risco_owasp": "A04:2021 - Insecure Design",
    "justificativa": "perfil fora dos padrões conhecidos; prioriza-se disponibilidade até revisão manual do caso",
}


def recomendar(perfil):
    for regra in REGRAS_DECISAO:
        if regra["condicao"](perfil):
            return {
                "banco": regra["banco"],
                "cap": regra["cap"],
                "justificativa": regra["justificativa"],
                "risco_owasp": regra["risco_owasp"],
            }
    return dict(REGRA_PADRAO)


perfis = {
    "credenciais_do_SOC": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "telemetria_de_sensores": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": False},
    "trilha_de_auditoria": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "carrinho_de_licencas": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": False},
    "cache_de_sessoes": {"schema_fixo": True, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": True},
}


if __name__ == "__main__":
    for nome, perfil in perfis.items():
        resultado = recomendar(perfil)
        print(f"{nome:24s} -> {resultado['banco']:8s} | {resultado['cap']} | \"{resultado['justificativa']}\" | {resultado['risco_owasp']}")
