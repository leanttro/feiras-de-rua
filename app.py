import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response, url_for
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import traceback
import decimal

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/submit-fair": {"origins": "*"}})

def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao banco de dados: {e}")
        # traceback.print_exc() # Descomente para detalhes completos
        raise

# Mapeamento Bairro -> Região (Adicione mais se precisar)
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
    'M BOI MIRIM': 'Zona Sul', 'GRAJAU': 'Zona Sul', 'INDIANOPOLIS': 'Zona Sul', # Exemplo
    'PIRITUBA': 'Zona Norte', 'FREGUESIA DO O': 'Zona Norte', 'CASA VERDE': 'Zona Norte',
    'LIMAO': 'Zona Norte', 'BRASILANDIA': 'Zona Norte', 'VILA MARIA': 'Zona Norte',
    'TUCURUVI': 'Zona Norte', 'SANTANA': 'Zona Norte', 'VILA GUILHERME': 'Zona Norte',
    'TREMEMBE': 'Zona Norte', 'JAÇANA': 'Zona Norte',
    'LAPA': 'Zona Oeste', 'BUTANTA': 'Zona Oeste', 'PINHEIROS': 'Zona Oeste',
    'PERDIZES': 'Zona Oeste', 'RAPOSO TAVARES': 'Zona Oeste', 'JAGUARA': 'Zona Oeste',
    'BARRA FUNDA': 'Zona Oeste', 'VILA LEOPOLDINA': 'Zona Oeste', 'ITAIM BIBI': 'Zona Oeste', # Exemplo
    'SE': 'Centro', 'BOM RETIRO': 'Centro', 'REPUBLICA': 'Centro', 'CONSOLACAO': 'Centro',
    'LIBERDADE': 'Centro', 'BELA VISTA': 'Centro', 'CAMBUCI': 'Centro', 'ACLIMACAO': 'Centro',
    'CANINDE': 'Centro', 'PARI': 'Centro' # Exemplo
}

def format_db_data(data_dict):
    """Formata datas, horas e decimais para exibição JSON/HTML."""
    if not isinstance(data_dict, dict):
        return data_dict

    formatted_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, datetime.date):
            formatted_dict[key] = value.strftime('%d/%m/%Y') if value else None
        elif isinstance(value, datetime.time):
            formatted_dict[key] = value.strftime('%H:%M') if value else None
        elif isinstance(value, decimal.Decimal):
             formatted_dict[key] = float(value) # Converte Decimal para float para JSON
        else:
            formatted_dict[key] = value
    return formatted_dict


# --- ROTA DO SITEMAP.XML (Atualizada para tabela única 'feiras') ---
@app.route('/sitemap.xml')
def sitemap():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Busca URLs da tabela 'feiras'
        cur.execute('SELECT url FROM feiras WHERE url IS NOT NULL;')
        feiras_urls = cur.fetchall() # Lista de DictRows, cada um com uma chave 'url'

        # Busca slugs da tabela 'blog'
        cur.execute('SELECT slug FROM blog WHERE slug IS NOT NULL;')
        blog_posts = cur.fetchall() # Lista de DictRows, cada um com uma chave 'slug'

        cur.close()
        hoje = datetime.datetime.now().strftime("%Y-%m-%d")

        # Ajuste no template sitemap_template.xml será necessário
        # para iterar sobre feiras_urls e construir a URL completa
        # (O template precisa saber que o URL já está completo ou só tem o slug)
        # Assumindo que o template espera apenas o slug para construir a URL:
        feiras_slugs = [{'slug': f['url'].split('/')[-1]} for f in feiras_urls if f['url']]


        sitemap_xml = render_template(
            'sitemap_template.xml',
            # Passa slugs para compatibilidade ou ajuste o template
            gastronomicas=[fs for fs in feiras_slugs], # Exemplo: passa todos para 'gastronomicas' no template
            artesanais=[], # Ou filtre por tipo_feira se o template precisar
            outrasfeiras=[], # Ou filtre por tipo_feira se o template precisar
            feiras_geral=feiras_slugs, # Passa uma lista geral se o template for ajustado
            blog_posts=blog_posts,
            hoje=hoje,
            base_url="https://www.feirasderua.com.br" # Base URL ainda útil
        )

        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml'
        return response

    except psycopg2.errors.UndefinedTable:
        print(f"ERRO SITEMAP: Tabela 'feiras' ou 'blog' não encontrada.")
        return "Erro ao gerar sitemap (tabela não encontrada)", 500
    except psycopg2.errors.UndefinedColumn:
        print(f"ERRO SITEMAP: Coluna 'url' ou 'slug' não encontrada.")
        return "Erro ao gerar sitemap (coluna não encontrada)", 500
    except Exception as e:
        print(f"ERRO AO GERAR SITEMAP: {e}")
        traceback.print_exc()
        return "Erro ao gerar sitemap", 500
    finally:
        if conn: conn.close()

# --- ROTAS DO BLOG (sem alteração significativa, mas com logs) ---
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
            post_dict = format_db_data(dict(post)) # Formata aqui
            slug = post_dict.get('slug')
            if slug:
                post_dict['url'] = f'/blog/{slug}' # URL relativa para o frontend
            else:
                 post_dict['url'] = '#'
                 print(f"AVISO: Post do blog com ID {post_dict.get('id')} não tem slug.")
            posts_processados.append(post_dict)
        return jsonify(posts_processados)
    except psycopg2.errors.UndefinedTable:
        print(f"ERRO em /api/blog: Tabela 'blog' não encontrada.")
        return jsonify({'error': "Erro interno (tabela 'blog' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/blog: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar posts do blog.'}), 500
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
            post_formatado = format_db_data(dict(post))
            # Você precisa de um template 'post-detalhe.html' na pasta 'templates'
            return render_template('post-detalhe.html', post=post_formatado)
        else:
            return "Post não encontrado", 404
    except psycopg2.errors.UndefinedTable:
        print(f"ERRO em /blog/<slug>: Tabela 'blog' não encontrada.")
        return "Erro interno (tabela 'blog' ausente)", 500
    except Exception as e:
        print(f"ERRO na rota /blog/{slug}: {e}")
        traceback.print_exc()
        return "Erro ao carregar a página do post", 500
    finally:
        if conn: conn.close()

# --- ROTA DE DETALHE ÚNICA PARA FEIRAS ---
@app.route('/feiras/<slug>')
def feira_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Busca na tabela única 'feiras' pelo slug
        cur.execute('SELECT * FROM feiras WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()

        if feira:
            feira_formatada = format_db_data(dict(feira))
            # Usa o mesmo template 'feira-detalhe.html'
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            # Pode verificar em tabelas antigas como fallback se quiser, mas idealmente não
            print(f"Feira com slug '{slug}' não encontrada na tabela 'feiras'.")
            return "Feira não encontrada", 404
    except psycopg2.errors.UndefinedTable:
        print(f"ERRO em /feiras/<slug>: Tabela 'feiras' não encontrada.")
        return "Erro interno (tabela 'feiras' ausente)", 500
    except psycopg2.errors.UndefinedColumn:
        print(f"ERRO em /feiras/<slug>: Coluna 'slug' não encontrada na tabela 'feiras'.")
        return "Erro interno (estrutura da tabela 'feiras' incorreta)", 500
    except Exception as e:
        print(f"ERRO na rota /feiras/{slug}: {e}")
        traceback.print_exc()
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()


# --- ROTAS DE API PARA FEIRAS (Consolidadas) ---

@app.route('/api/feiras/tipos') # Endpoint para listar os tipos de feira disponíveis
def get_tipos_feira():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tipo_feira FROM feiras WHERE tipo_feira IS NOT NULL AND tipo_feira != '' ORDER BY tipo_feira;")
        tipos = [row[0] for row in cur.fetchall()]
        cur.close()
        return jsonify(tipos)
    except Exception as e:
        print(f"ERRO em /api/feiras/tipos: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro ao buscar tipos de feira'}), 500
    finally:
        if conn: conn.close()


@app.route('/api/feiras') # Endpoint principal para buscar feiras, com filtro opcional por tipo
def get_api_feiras():
    conn = None
    try:
        tipo_feira_filtro = request.args.get('tipo') # Pega o parâmetro ?tipo= da URL
        limite = request.args.get('limite', default=None, type=int) # Limite opcional

        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = "SELECT * FROM feiras"
        params = []

        if tipo_feira_filtro:
            query += " WHERE tipo_feira ILIKE %s" # ILIKE para case-insensitive
            params.append(f"%{tipo_feira_filtro}%") # Busca parcial pelo tipo

        query += " ORDER BY id" # Ou outra ordenação desejada

        if limite:
            query += " LIMIT %s"
            params.append(limite)

        cur.execute(query + ";", tuple(params))
        feiras_raw = cur.fetchall()
        cur.close()

        # Processa os dados antes de retornar (formata, adiciona URL relativa)
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = format_db_data(dict(feira))
            slug = feira_dict.get('slug')
            if slug:
                 # URL relativa para o frontend usar
                feira_dict['url'] = f'/feiras/{slug}'
                feiras_processadas.append(feira_dict)
            else:
                 print(f"AVISO: Feira ID {feira_dict.get('id')} não possui slug. Omitida da API /api/feiras.")

        return jsonify(feiras_processadas)

    except psycopg2.errors.UndefinedTable:
        print(f"ERRO em /api/feiras: Tabela 'feiras' não encontrada.")
        return jsonify({'error': "Erro interno (tabela 'feiras' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/feiras: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar feiras.'}), 500
    finally:
        if conn: conn.close()

# --- ROTAS ANTIGAS /api/gastronomicas, /api/artesanais - Removidas ou Redirecionadas ---
# Você pode remover essas rotas ou fazê-las apenas chamar a nova /api/feiras?tipo=...
# Exemplo de remoção (recomendado):
# @app.route('/api/gastronomicas') ... (REMOVER)
# @app.route('/api/artesanais') ... (REMOVER)
# @app.route('/api/outrasfeiras') ... (REMOVER)


# --- ROTA /api/filtros (Mantida, mas usando a tabela 'feiras') ---
@app.route('/api/filtros')
def get_filtros():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Busca bairros distintos da tabela 'feiras'
        cur.execute('SELECT DISTINCT bairro FROM feiras WHERE bairro IS NOT NULL ORDER BY bairro;')
        bairros_db = cur.fetchall()
        cur.close()

        filtros = {}
        for item in bairros_db:
            bairro = item.get('bairro')
            if bairro:
                # Usa o mapeamento para encontrar a região
                regiao = BAIRRO_REGIAO_MAP.get(bairro.strip().upper(), 'Outras')
                if regiao not in filtros:
                    filtros[regiao] = []
                # Adiciona bairro se ainda não estiver na lista da região
                if bairro not in filtros[regiao]:
                     filtros[regiao].append(bairro)

        # Ordena bairros dentro de cada região
        for regiao in filtros:
            filtros[regiao].sort()

        return jsonify(filtros)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/filtros: Tabela 'feiras' não encontrada.")
         return jsonify({'error': "Erro interno (tabela 'feiras' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/filtros: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar filtros.'}), 500
    finally:
        if conn: conn.close()


# --- ROTA DE SUBMISSÃO (Sem alteração, continua usando a tabela 'contato') ---
@app.route('/submit-fair', methods=['POST'])
def handle_submission():
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Nenhum dado recebido.'}), 400

        required_fields = ['nomeFeira', 'enderecoCompleto'] # Adapte se necessário
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({'success': False, 'message': 'Campos obrigatórios ausentes.'}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        # Insere na tabela 'contato' (ou 'submissoes' se você preferir)
        sql = """
            INSERT INTO contato (nome_feira, regiao, endereco, dias_funcionamento, categoria, nome_responsavel, email_contato, whatsapp, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cur.execute(sql, (
            data.get('nomeFeira'), data.get('regiao'), data.get('enderecoCompleto'),
            data.get('diaHorario'), data.get('categoria'), data.get('nomeOrganizador'),
            data.get('emailOrganizador'), data.get('telefone'), data.get('descricao')
        ))
        conn.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Feira submetida com sucesso!'})

    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /submit-fair: Tabela 'contato' não encontrada.")
         if conn: conn.rollback()
         return jsonify({'success': False, 'message': "Erro interno (tabela 'contato' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /submit-fair: {e}")
        traceback.print_exc()
        if conn: conn.rollback()
        return jsonify({'success': False, 'message': 'Erro interno ao processar submissão.'}), 500
    finally:
        if conn: conn.close()

# --- ROTA PARA SERVIR ARQUIVOS ESTÁTICOS E INDEX ---
@app.route('/')
def index():
    # Servir o index.html principal
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static_files(path):
    # Lista de arquivos/pastas permitidos no diretório raiz
    allowed_files_folders = ['index.html', 'anuncie.html','artesanais.html', 'gastronomicas.html', 'feiras-livres.html', 'contato.html', 'assets', 'templates'] # Adicione outros arquivos HTML ou pastas se necessário

    # Extrai a primeira parte do caminho para verificar se é uma pasta permitida
    base_path = path.split('/')[0]

    # Verifica se é um arquivo/pasta permitido ou se está dentro de uma pasta permitida
    if path in allowed_files_folders or base_path in allowed_files_folders:
         # Evita servir o próprio app.py ou arquivos sensíveis
        if path == "app.py" or path.endswith((".env", ".pyc")):
             return "Not Found", 404
        # Tenta servir o arquivo/diretório
        if os.path.exists(os.path.join('.', path)):
             return send_from_directory('.', path)

    # Se não for encontrado ou não for permitido, retorna 404
    return "Not Found", 404


# --- EXECUÇÃO ---
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", 10000))
    # debug=False é crucial para produção no Render.
    app.run(host="0.0.0.0", port=port, debug=False)