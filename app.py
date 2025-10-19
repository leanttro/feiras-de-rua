import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response, url_for
from dotenv import load_dotenv
from flask_cors import CORS
import datetime

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/submit-fair": {"origins": "*"}})

def get_db_connection():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

# Mapeamento de Bairros (sem alteração)
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


# --- ATUALIZAÇÃO IMPORTANTE: ROTA DO SITEMAP.XML ---
@app.route('/sitemap.xml')
def sitemap():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Busca os slugs das feiras gastronômicas
        cur.execute('SELECT slug FROM gastronomicas;')
        gastronomicas = cur.fetchall()

        # Busca os slugs das feiras artesanais
        cur.execute('SELECT slug FROM artesanais;')
        artesanais = cur.fetchall()
        
        # --- NOVO ---
        # Busca os slugs dos posts do blog
        cur.execute('SELECT slug FROM blog;')
        blog_posts = cur.fetchall()
        # --- FIM DA NOVIDADE ---

        cur.close()
        hoje = datetime.datetime.now().strftime("%Y-%m-%d")

        # Renderiza o template do sitemap com TODOS os dados
        sitemap_xml = render_template(
            'sitemap_template.xml',
            gastronomicas=gastronomicas,
            artesanais=artesanais,
            blog_posts=blog_posts, # <-- Adicionado
            hoje=hoje,
            base_url="https://www.feirasderua.com.br"
        )
        
        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml'
        
        return response

    except Exception as e:
        print(f"Erro ao gerar sitemap: {e}")
        return "Erro ao gerar sitemap", 500
    finally:
        if conn: conn.close()
# --- FIM DA ATUALIZAÇÃO ---


# --- ROTAS DO BLOG ---
@app.route('/api/blog')
def get_blog_posts():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT id, titulo, subtitulo, imagem_url, slug FROM blog ORDER BY data_publicacao DESC, id DESC LIMIT 6;')
        posts_raw = cur.fetchall()
        cur.close()
        
        posts_processados = []
        for post in posts_raw:
            post_dict = dict(post)
            post_dict['url'] = f'/blog/{post_dict["slug"]}'
            posts_processados.append(post_dict)
        return jsonify(posts_processados)
    except Exception as e:
        print(f"Erro no endpoint /api/blog: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/blog/<slug>')
def blog_post_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM blog WHERE slug = %s;', (slug,))
        post = cur.fetchone()
        cur.close()
        
        if post:
            post_formatado = format_feira_data(dict(post))
            return render_template('post-detalhe.html', post=post_formatado)
        else:
            return "Post não encontrado", 404
    except Exception as e:
        print(f"Erro na rota /blog/{slug}: {e}")
        return "Erro ao carregar a página", 500
    finally:
        if conn: conn.close()
# --- FIM DAS ROTAS DO BLOG ---

# Rotas de páginas e API (sem alterações, apenas garantindo que estão aqui)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

def format_feira_data(data_dict):
    for key, value in data_dict.items():
        if isinstance(value, datetime.date):
            data_dict[key] = value.strftime('%d/%m/%Y') if value else None
        elif isinstance(value, datetime.time):
            data_dict[key] = value.strftime('%H:%M') if value else None
    return data_dict

@app.route('/gastronomicas/<slug>')
def feira_gastronomica_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM gastronomicas WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()
        if feira:
            feira_formatada = format_feira_data(dict(feira))
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            return "Feira não encontrada", 404
    except Exception as e:
        return "Erro ao carregar a página", 500
    finally:
        if conn: conn.close()

@app.route('/artesanais/<slug>')
def feira_artesanal_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM artesanais WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()
        if feira:
            feira_formatada = format_feira_data(dict(feira))
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            return "Feira não encontrada", 404
    except Exception as e:
        return "Erro ao carregar a página", 500
    finally:
        if conn: conn.close()

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

@app.route('/api/gastronomicas')
def get_gastronomicas():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM gastronomicas ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = dict(feira)
            for key, value in feira_dict.items():
                if isinstance(value, (datetime.date, datetime.time)):
                    feira_dict[key] = value.isoformat() if value else None
            feira_dict['url'] = f'/gastronomicas/{feira_dict["slug"]}'
            feiras_processadas.append(feira_dict)
        return jsonify(feiras_processadas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/artesanais')
def get_artesanais():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM artesanais ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = dict(feira)
            for key, value in feira_dict.items():
                if isinstance(value, (datetime.date, datetime.time)):
                    feira_dict[key] = value.isoformat() if value else None
            feira_dict['url'] = f'/artesanais/{feira_dict["slug"]}'
            feiras_processadas.append(feira_dict)
        return jsonify(feiras_processadas)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/api/outrasfeiras')
def get_outrasfeiras():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Busca na nova tabela 'outrasfeiras'
        cur.execute('SELECT * FROM outrasfeiras ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = dict(feira)
            for key, value in feira_dict.items():
                if isinstance(value, (datetime.date, datetime.time)):
                    feira_dict[key] = value.isoformat() if value else None
            # Assumindo que 'outrasfeiras' também terá uma página de detalhes
            feira_dict['url'] = f'/outrasfeiras/{feira_dict["slug"]}' 
            feiras_processadas.append(feira_dict)
            
        return jsonify(feiras_processadas)
    except Exception as e:
        print(f"Erro no endpoint /api/outrasfeiras: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn: conn.close()

@app.route('/submit-fair', methods=['POST'])
def handle_submission():
    # ... (Seu código original, sem alterações) ...
    pass

# Rota "coringa" (deve ser a última)
@app.route('/<path:path>')
def serve_static_files(path):
    if path == "app.py":
        return "Not Found", 404
    return send_from_directory('.', path)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

