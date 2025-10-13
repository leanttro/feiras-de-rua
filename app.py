import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv
from flask_cors import CORS
import datetime # <-- Adicionado para lidar com datas e horas

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a instância da aplicação Flask
app = Flask(__name__)
# Configuração de CORS para permitir seu site do GitHub Pages
CORS(app, resources={r"/api/*": {"origins": "https://leanttro.github.io"}, r"/submit-fair": {"origins": "https://leanttro.github.io"}})

# Função para obter a conexão com o banco de dados
def get_db_connection():
    # A variável DATABASE_URL será lida do ambiente do Render
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# Mapeamento de Bairros para Regiões (pode ser expandido)
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
            regiao = BAIRRO_REGIAO_MAP.get(bairro, 'Outras')
            if regiao not in filtros:
                filtros[regiao] = []
            filtros[regiao].append(bairro)

        return jsonify(filtros)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/")
def serve_frontend():
    return send_from_directory('.', 'index.html')

@app.route('/api/feiras')
def get_feiras():
    try:
        limite_query = request.args.get('limite', default=1000, type=int) 
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM feiras ORDER BY id LIMIT %s;', (limite_query,))
        feiras = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(feiras)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ENDPOINTS ATUALIZADOS PARA LIDAR COM DATAS E HORAS ---

@app.route('/api/gastronomicas')
def get_gastronomicas():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM gastronomicas ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        conn.close()

        # Converte os dados para um formato que o jsonify entende
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = dict(feira)
            for key, value in feira_dict.items():
                # Converte objetos date e time para string no formato ISO
                if isinstance(value, (datetime.date, datetime.time)):
                    feira_dict[key] = value.isoformat() if value else None
            feiras_processadas.append(feira_dict)
            
        return jsonify(feiras_processadas)
    except Exception as e:
        # Adiciona um print para vermos o erro exato nos logs do Render
        print(f"Erro no endpoint /api/gastronomicas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/artesanais')
def get_artesanais():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM artesanais ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        conn.close()

        # Converte os dados para um formato que o jsonify entende
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = dict(feira)
            for key, value in feira_dict.items():
                # Converte objetos date e time para string no formato ISO
                if isinstance(value, (datetime.date, datetime.time)):
                    feira_dict[key] = value.isoformat() if value else None
            feiras_processadas.append(feira_dict)

        return jsonify(feiras_processadas)
    except Exception as e:
        # Adiciona um print para vermos o erro exato nos logs do Render
        print(f"Erro no endpoint /api/artesanais: {e}")
        return jsonify({'error': str(e)}), 500

# --- FIM DOS ENDPOINTS ATUALIZADOS ---

@app.route('/submit-fair', methods=['POST'])
def handle_submission():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            INSERT INTO contato (nome_feira, regiao, endereco, dias_funcionamento, categoria, nome_responsavel, email_contato, whatsapp, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        data_tuple = (
            request.form.get('fairName'), request.form.get('region'), request.form.get('address'),
            request.form.get('days'), request.form.get('category'), request.form.get('responsibleName'),
            request.form.get('contactEmail'), request.form.get('whatsapp'), request.form.get('description')
        )
        cur.execute(sql, data_tuple)
        conn.commit()
        cur.close()
        return jsonify({'message': 'Dados recebidos com sucesso!'}), 200
    except Exception as e:
        if conn: conn.rollback()
        # Adiciona um print para vermos o erro exato nos logs do Render
        print(f"Erro no endpoint /submit-fair: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

