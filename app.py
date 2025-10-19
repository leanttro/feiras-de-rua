import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import traceback
import decimal

# Carrega variáveis de ambiente de um arquivo .env, se existir
load_dotenv()

# Inicializa o aplicativo Flask
# static_folder='.' faz com que o Flask procure arquivos como CSS, JS e HTML na pasta raiz.
app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
CORS(app) # Habilita CORS para todas as rotas

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    conn = None
    try:
        # Pega a URL do banco de dados das variáveis de ambiente do Render
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao banco de dados: {e}")
        raise

def format_db_data(data_dict):
    """Formata datas, horas e decimais de um dicionário para exibição em JSON/HTML."""
    if not isinstance(data_dict, dict):
        return data_dict

    formatted_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, datetime.date):
            formatted_dict[key] = value.strftime('%d/%m/%Y') if value else None
        elif isinstance(value, datetime.time):
            formatted_dict[key] = value.strftime('%H:%M') if value else None
        elif isinstance(value, decimal.Decimal):
            formatted_dict[key] = float(value) # Converte Decimal para float para ser compatível com JSON
        else:
            formatted_dict[key] = value
    return formatted_dict


# --- NOVA ROTA PARA BUSCAR OS TIPOS DE FEIRA DISTINTOS ---
@app.route('/api/feiras/tipos')
def get_tipos_feira():
    """Retorna uma lista JSON com todos os valores únicos de 'tipo_feira'."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Busca todos os valores distintos, ignorando nulos ou vazios, e ordena
        cur.execute("SELECT DISTINCT tipo_feira FROM feiras WHERE tipo_feira IS NOT NULL AND tipo_feira != '' ORDER BY tipo_feira;")
        # Extrai os valores da tupla retornada pelo banco (ex: [('Artesanal',), ('Gastronômica',)])
        tipos = [row[0] for row in cur.fetchall()]
        cur.close()
        return jsonify(tipos)
    except Exception as e:
        print(f"ERRO em /api/feiras/tipos: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro ao buscar tipos de feira'}), 500
    finally:
        if conn: conn.close()


# --- ROTA DE DETALHE ÚNICA PARA FEIRAS ---
# Esta rota agora lida com TODAS as feiras, buscando pelo 'slug' na URL.
# Ex: /feiras/feira-da-liberdade
@app.route('/feiras/<slug>')
def feira_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Busca na tabela única 'feiras' pelo slug
        cur.execute('SELECT * FROM feiras WHERE url LIKE %s;', (f'%/{slug}',))
        feira = cur.fetchone()
        cur.close()

        if feira:
            feira_formatada = format_db_data(dict(feira))
            # Usa o template 'feira-detalhe.html' para renderizar a página
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            print(f"AVISO: Feira com slug '{slug}' não encontrada.")
            return "Feira não encontrada", 404
            
    except Exception as e:
        print(f"ERRO na rota /feiras/{slug}: {e}")
        traceback.print_exc()
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()


# --- ROTAS DE API PARA O FRONTEND ---

# Endpoint principal que agora busca na tabela 'feiras' e pode filtrar por tipo
# Ex: /api/feiras?tipo=gastronomica
@app.route('/api/feiras')
def get_api_feiras():
    conn = None
    try:
        # Pega o parâmetro ?tipo= da URL para filtrar
        tipo_feira_filtro = request.args.get('tipo')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = "SELECT * FROM feiras"
        params = []

        if tipo_feira_filtro:
            # ILIKE faz a busca ser case-insensitive (não diferencia maiúsculas de minúsculas)
            query += " WHERE tipo_feira ILIKE %s"
            params.append(f"%{tipo_feira_filtro}%")

        query += " ORDER BY nome_feira;" # Ordena por nome

        cur.execute(query, tuple(params))
        feiras_raw = cur.fetchall()
        cur.close()

        # Processa os dados para o frontend (formata e adiciona a URL relativa)
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = format_db_data(dict(feira))
            url_relativa = feira_dict.get('url')
            if url_relativa:
                # O frontend receberá o campo 'url' pronto para usar no link
                feira_dict['url'] = url_relativa
                feiras_processadas.append(feira_dict)
            else:
                 print(f"AVISO: Feira ID {feira_dict.get('id')} não possui URL. Omitida da API.")

        return jsonify(feiras_processadas)

    except Exception as e:
        print(f"ERRO no endpoint /api/feiras: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar feiras.'}), 500
    finally:
        if conn: conn.close()
        
# --- ROTAS ANTIGAS PARA COMPATIBILIDADE ---
# Estas rotas agora apenas chamam a nova API com o filtro correto.
# Isso evita que você tenha que mudar o JavaScript do seu site imediatamente.
@app.route('/api/gastronomicas')
def get_gastronomicas_compat():
    return get_api_feiras_filtrado('Gastronômica')

@app.route('/api/artesanais')
def get_artesanais_compat():
    return get_api_feiras_filtrado('Artesanal')

@app.route('/api/outrasfeiras')
def get_outrasfeiras_compat():
    # Exemplo: busca por qualquer coisa que não seja gastronomica ou artesanal
    # (Você pode ajustar esta lógica se precisar)
    return get_api_feiras_filtrado(None, exclude=['Gastronômica', 'Artesanal'])

def get_api_feiras_filtrado(tipo_feira, exclude=None):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = "SELECT * FROM feiras"
        params = []
        
        if tipo_feira:
            query += " WHERE tipo_feira ILIKE %s"
            params.append(f"%{tipo_feira}%")
        elif exclude:
            exclude_conditions = " AND ".join(["tipo_feira NOT ILIKE %s" for _ in exclude])
            query += f" WHERE {exclude_conditions}"
            params.extend([f"%{e}%" for e in exclude])

        query += " ORDER BY nome_feira;"
        cur.execute(query, tuple(params))
        feiras_raw = cur.fetchall()
        cur.close()

        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = format_db_data(dict(feira))
            url_relativa = feira_dict.get('url')
            if url_relativa:
                feira_dict['url'] = url_relativa
                feiras_processadas.append(feira_dict)
        return jsonify(feiras_processadas)
    except Exception as e:
        print(f"ERRO em rota de compatibilidade: {e}")
        return jsonify({'error': 'Erro interno.'}), 500
    finally:
        if conn: conn.close()

# Rota para servir a página principal
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Rota para servir outros arquivos estáticos (HTML, CSS, JS, imagens)
@app.route('/<path:path>')
def serve_static_files(path):
    if os.path.exists(os.path.join('.', path)):
        return send_from_directory('.', path)
    return "Not Found", 404

# Execução do App
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

