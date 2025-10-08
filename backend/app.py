import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request # <<< --- ADICIONE 'request' ---
from dotenv import load_dotenv
from flask_cors import CORS


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a instância da aplicação Flask
app = Flask(__name__)
CORS(app) # Habilita o CORS para permitir que seu frontend acesse a API

# Função para obter a conexão com o banco de dados
def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# --- INÍCIO DO CÓDIGO ADICIONADO ---

# 1. Mapeamento de Bairros para Regiões (pode ser expandido)
BAIRRO_REGIAO_MAP = {
    'VL FORMOSA': 'Zona Leste', 'CIDADE AE CARVALHO': 'Zona Leste', 'ITAQUERA': 'Zona Leste',
    'SAO MIGUEL PAULISTA': 'Zona Leste', 'VILA PRUDENTE': 'Zona Leste', 'MOOCA': 'Zona Leste',
    'SAPOPEMBA': 'Zona Leste', 'GUAIANASES': 'Zona Leste', 'VILA MATILDE': 'Zona Leste',
    'PENHA': 'Zona Leste', 'VILA CARRAO': 'Zona Leste', 'TATUAPE': 'Zona Leste',
    'SAO MATEUS': 'Zona Leste', 'AGUA RASA': 'Zona Leste', 'ERMELINO MATARAZZO': 'Zona Leste',
    'ARTUR ALVIM': 'Zona Leste', 'ITAIM PAULISTA': 'Zona Leste',
    'CAPAO REDONDO': 'Zona Sul', 'CAMPO LIMPO': 'Zona Sul', 'SACOMA': 'Zona Sul',
    'IPIRANGA': 'Zona Sul', 'SAUDE': 'Zona Sul', 'JABAQUARA': 'Zona Sul',
    'VILA MARIANA': 'Zona Sul', 'CIDADE ADEMAR': 'Zona Sul', 'CURSINO': 'Zona Sul',
    'SOCORRO': 'Zona Sul', 'CAMPO BELO': 'Zona Sul', 'SANTO AMARO': 'Zona Sul',
    'M BOI MIRIM': 'Zona Sul', 'GRAJAU': 'Zona Sul',
    'PIRITUBA': 'Zona Norte', 'FREGUESIA DO O': 'Zona Norte', 'CASA VERDE': 'Zona Norte',
    'LIMAO': 'Zona Norte', 'BRASILANDIA': 'Zona Norte', 'VILA MARIA': 'Zona Norte',
    'TUCURUVI': 'Zona Norte', 'SANTANA': 'Zona Norte', 'VILA GUILHERME': 'Zona Norte',
    'TREMEMBE': 'Zona Norte', 'JAÇANA': 'Zona Norte',
    'LAPA': 'Zona Oeste', 'BUTANTA': 'Zona Oeste', 'PINHEIROS': 'Zona Oeste',
    'PERDIZES': 'Zona Oeste', 'RAPOSO TAVARES': 'Zona Oeste', 'JAGUARA': 'Zona Oeste',
    'BARRA FUNDA': 'Zona Oeste', 'VILA LEOPOLDINA': 'Zona Oeste',
    'SE': 'Centro', 'BOM RETIRO': 'Centro', 'REPUBLICA': 'Centro', 'CONSOLACAO': 'Centro',
    'LIBERDADE': 'Centro', 'BELA VISTA': 'Centro', 'CAMBUCI': 'Centro', 'ACLIMACAO': 'Centro'
}

# 2. Novo Endpoint para Filtros
@app.route('/api/filtros')
def get_filtros():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT DISTINCT bairro FROM feiras ORDER BY bairro;')
        bairros_db = cur.fetchall()
        cur.close()
        conn.close()

        filtros = {}
        for item in bairros_db:
            bairro = item['bairro']
            # Usa 'get' para evitar erro se um bairro não estiver no mapa
            regiao = BAIRRO_REGIAO_MAP.get(bairro, 'Outras')
            if regiao not in filtros:
                filtros[regiao] = []
            filtros[regiao].append(bairro)

        return jsonify(filtros)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- FIM DO CÓDIGO ADICIONADO ---


# Endpoint principal - apenas para saber que a API está no ar
@app.route("/")
def hello_world():
    return "<p>Olá! O cérebro da aplicação está no ar e pronto para receber requisições!</p>"

# --- NOSSO PRIMEIRO ENDPOINT DE VERDADE ---
# Este endpoint vai buscar e retornar os dados das feiras
@app.route('/api/feiras')
def get_feiras():
    try:
        # --- INÍCIO DO CÓDIGO ADICIONADO ---
        bairro_query = request.args.get('bairro')
        # --- FIM DO CÓDIGO ADICIONADO ---

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # --- INÍCIO DO CÓDIGO MODIFICADO ---
        if bairro_query:
            # Se um bairro foi passado, filtra a busca
            cur.execute('SELECT * FROM feiras WHERE bairro = %s ORDER BY id;', (bairro_query,))
        else:
            # Senão, busca todos (com o limite)
            cur.execute('SELECT * FROM feiras ORDER BY id LIMIT 100;')
        # --- FIM DO CÓDIGO MODIFICADO ---
            
        feiras = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(feiras)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
