import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory
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

# --- MAPEAMENTO DE BAIRROS E ENDPOINT DE FILTROS (CÓDIGO EXISTENTE) ---

# Mapeamento de Bairros para Regiões
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

# Endpoint para Filtros
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

# Endpoint principal para servir o frontend
@app.route("/")
def serve_frontend():
    return send_from_directory('.', 'feiras-livres.html')

# Endpoint para buscar e retornar os dados das feiras
@app.route('/api/feiras')
def get_feiras():
    try:
        bairro_query = request.args.get('bairro')
        limite_query = request.args.get('limite', default=1000, type=int) 

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        if bairro_query:
            cur.execute('SELECT * FROM feiras WHERE bairro = %s ORDER BY id;', (bairro_query,))
        else:
            cur.execute('SELECT * FROM feiras ORDER BY id LIMIT %s;', (limite_query,))
            
        feiras = cur.fetchall()

        cur.close()
        conn.close()

        return jsonify(feiras)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- NOVO ENDPOINT PARA RECEBER DADOS DO FORMULÁRIO DE CONTATO ---
@app.route('/submit-fair', methods=['POST'])
def handle_submission():
    try:
        # Pega os dados enviados pelo formulário
        nome_feira = request.form.get('fairName')
        regiao = request.form.get('region')
        endereco = request.form.get('address')
        dias_funcionamento = request.form.get('days')
        categoria = request.form.get('category')
        nome_responsavel = request.form.get('responsibleName')
        email_contato = request.form.get('contactEmail')
        whatsapp = request.form.get('whatsapp')
        descricao = request.form.get('description')

        conn = get_db_connection()
        cur = conn.cursor()

        # Comando SQL para inserir os dados na tabela 'contato'
        sql = """
            INSERT INTO contato (nome_feira, regiao, endereco, dias_funcionamento, categoria, nome_responsavel, email_contato, whatsapp, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        data_tuple = (nome_feira, regiao, endereco, dias_funcionamento, categoria, nome_responsavel, email_contato, whatsapp, descricao)

        cur.execute(sql, data_tuple)
        conn.commit()
        cur.close()

        return jsonify({'message': 'Dados recebidos com sucesso!'}), 200

    except Exception as e:
        # Em caso de erro, desfaz a transação
        if 'conn' in locals() and conn is not None:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        # Garante que a conexão seja sempre fechada
        if 'conn' in locals() and conn is not None:
            conn.close()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
