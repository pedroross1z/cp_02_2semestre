# Como rodar

1. Suba os bancos (Docker, conforme a apostila):
   ```
   docker run -d --name mongo-lab -p 27017:27017 mongo:7
   docker run -d --name mysql-lab -p 3306:3306 -e MYSQL_ROOT_PASSWORD=sua_senha -e MYSQL_DATABASE=seguranca mysql:8.0
   ```
2. Instale as dependências:
   ```
   pip install pymongo mysql-connector-python scikit-learn numpy flask requests
   ```
3. Copie `.env.example` para `.env` (ou exporte as variáveis direto no shell) e ajuste a senha:
   ```
   export MYSQL_HOST=localhost
   export MYSQL_USER=root
   export MYSQL_PASSWORD=sua_senha
   export MYSQL_DATABASE=seguranca
   export MONGO_URI=mongodb://localhost:27017
   export MONGO_DB_NAME=seguranca
   ```
4. Rode cada exercício:
   ```
   python3 ex1_recomendar.py
   python3 ex2_migracao.py
   python3 ex3_ttl_janela.py
   python3 ex4_transacao_auditoria.py
   python3 ex5_order_by_seguro.py      # servidor Flask, testar com curl/requests
   python3 ex6_controle_acesso.py      # servidor Flask
   python3 ex7_xss_atributo.py         # servidor Flask
   python3 ex8_modelo_ml.py            # servidor Flask
   python3 ex9_rate_limiting.py        # servidor Flask
   ```
5. Exercício 10 (pasta `ex10/`): rode `app_vulneravel.py`, execute `python3 exploit.py http://localhost:5010`
   (6 de 6 ataques bem-sucedidos), depois rode `app_seguro.py` na porta 5011 e execute
   `python3 exploit.py http://localhost:5011` (0 de 6). Precisa de uma tabela `usuarios`:
   ```sql
   CREATE TABLE usuarios (
       id INT PRIMARY KEY AUTO_INCREMENT,
       nome VARCHAR(50) NOT NULL,
       senha VARCHAR(100) NOT NULL,
       nivel INT NOT NULL DEFAULT 1,
       api_key VARCHAR(50) UNIQUE
   );
   INSERT INTO usuarios (nome, senha, nivel, api_key) VALUES
   ('ana', 'hash-ana', 5, 'key-ana-001'),
   ('bruno', 'hash-bruno', 1, 'key-bruno-002');
   ```
   `app_vulneravel.py` mantém a senha do banco hardcoded (`"senha"`) de propósito — é a
   própria falha nº 7 do exercício — então ajuste temporariamente a senha do seu `root`
   do MySQL para `senha` só para rodar essa demonstração, ou edite a constante `db()`
   se preferir usar outra credencial.

Nota sobre este ambiente de desenvolvimento: aqui o Docker Hub estava bloqueado pela
política de rede, então validei os exercícios 2, 3, 4, 7, 8 e 9 com `mongomock`
(biblioteca que implementa a mesma API do pymongo em memória) e um MySQL local via apt,
mantendo o código de produção idêntico ao que roda contra o MongoDB real do `mongo-lab`.
Rode com o Docker do enunciado para o resultado final.
