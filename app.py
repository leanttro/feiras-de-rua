import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response, url_for
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import traceback # Importar para logar erros detalhados
import decimal # Adicionado para converter tipos de dados do banco

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
CORS(app, resources={r"/api/*": {"origins": "*"}, r"/submit-fair": {"origins": "*"}})

def get_db_connection():
    conn = None
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        return conn
    except Exception as e:
        # Loga o erro de conexão no console do Render
        print(f"ERRO CRÍTICO: Não foi possível conectar ao banco de dados: {e}")
        # traceback.print_exc() # Descomente para detalhes completos do erro de conexão
        raise # Re-levanta a exceção para que o Flask retorne um erro 500 claro

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
    'LIBERDADE': 'Centro', 'BELA VISTA': 'Centro', 'CAMBUCI': 'Centro', 'ACLIMACAO': 'Centro',
    # Adicionando bairro faltante da feira de exemplo
    'CANINDE': 'Centro'
}


# --- ROTA DO SITEMAP.XML (ATUALIZADA com try-except) ---
@app.route('/sitemap.xml')
def sitemap():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Usando .get() para segurança caso a coluna 'slug' não exista
        cur.execute('SELECT slug FROM gastronomicas WHERE slug IS NOT NULL;')
        gastronomicas = cur.fetchall()

        cur.execute('SELECT slug FROM artesanais WHERE slug IS NOT NULL;')
        artesanais = cur.fetchall()

        cur.execute('SELECT slug FROM blog WHERE slug IS NOT NULL;')
        blog_posts = cur.fetchall()

        cur.close()
        hoje = datetime.datetime.now().strftime("%Y-%m-%d")

        sitemap_xml = render_template(
            'sitemap_template.xml',
            gastronomicas=gastronomicas,
            artesanais=artesanais,
            blog_posts=blog_posts,
            hoje=hoje,
            base_url="https://www.feirasderua.com.br"
        )

        response = make_response(sitemap_xml)
        response.headers['Content-Type'] = 'application/xml'

        return response

    except Exception as e:
        print(f"ERRO AO GERAR SITEMAP: {e}")
        traceback.print_exc() # Log detalhado no Render
        return "Erro ao gerar sitemap", 500
    finally:
        if conn: conn.close()
# --- FIM DA ATUALIZAÇÃO SITEMAP ---


# --- ROTAS DO BLOG (ATUALIZADAS com try-except) ---
@app.route('/api/blog')
def get_blog_posts():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Assumindo que a tabela blog e a coluna slug existem
        cur.execute('SELECT id, titulo, subtitulo, imagem_url, slug FROM blog ORDER BY data_publicacao DESC, id DESC LIMIT 6;')
        posts_raw = cur.fetchall()
        cur.close()

        posts_processados = []
        for post in posts_raw:
            post_dict = dict(post)
            slug = post_dict.get('slug') # Usar .get() para segurança
            if slug:
                post_dict['url'] = f'/blog/{slug}'
            else:
                 post_dict['url'] = '#' # Ou alguma URL padrão/erro
                 print(f"AVISO: Post do blog com ID {post_dict.get('id')} não tem slug.")
            posts_processados.append(post_dict)
        return jsonify(posts_processados)
    except Exception as e:
        print(f"ERRO no endpoint /api/blog: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar posts do blog.'}), 500
    finally:
        if conn: conn.close()

@app.route('/blog/<slug>')
def blog_post_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Assumindo que a tabela blog e a coluna slug existem
        cur.execute('SELECT * FROM blog WHERE slug = %s;', (slug,))
        post = cur.fetchone()
        cur.close()

        if post:
            post_formatado = format_feira_data(dict(post)) # Reutiliza a função de formatação
            return render_template('post-detalhe.html', post=post_formatado)
        else:
            return "Post não encontrado", 404
    except Exception as e:
        print(f"ERRO na rota /blog/{slug}: {e}")
        traceback.print_exc() # Log detalhado no Render
        return "Erro ao carregar a página do post", 500
    finally:
        if conn: conn.close()
# --- FIM DAS ROTAS DO BLOG ---

@app.route('/')
def index():
    # O Flask já serve o index.html por padrão se static_folder='.'
    return send_from_directory('.', 'index.html')


def format_feira_data(data_dict):
    """Formata datas e horas para exibição no HTML (DD/MM/YYYY e HH:MM)."""
    if not isinstance(data_dict, dict):
        return data_dict # Retorna se não for um dicionário

    formatted_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, datetime.date):
            formatted_dict[key] = value.strftime('%d/%m/%Y') if value else None
        elif isinstance(value, datetime.time):
            formatted_dict[key] = value.strftime('%H:%M') if value else None
        else:
            formatted_dict[key] = value
    return formatted_dict

# --- ROTAS DE DETALHE (ATUALIZADAS com try-except) ---
@app.route('/gastronomicas/<slug>')
def feira_gastronomica_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Assumindo que a tabela gastronomicas e a coluna slug existem
        cur.execute('SELECT * FROM gastronomicas WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()
        if feira:
            feira_formatada = format_feira_data(dict(feira))
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            return "Feira gastronômica não encontrada", 404
    except Exception as e:
        print(f"ERRO na rota /gastronomicas/{slug}: {e}")
        traceback.print_exc() # Log detalhado no Render
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()

@app.route('/artesanais/<slug>')
def feira_artesanal_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Assumindo que a tabela artesanais e a coluna slug existem
        cur.execute('SELECT * FROM artesanais WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()
        if feira:
            feira_formatada = format_feira_data(dict(feira))
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            return "Feira artesanal não encontrada", 404
    except Exception as e:
        print(f"ERRO na rota /artesanais/{slug}: {e}")
        traceback.print_exc() # Log detalhado no Render
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()

# --- NOVA ROTA DE DETALHE PARA OUTRASFEIRAS ---
@app.route('/outrasfeiras/<slug>')
def feira_outras_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM outrasfeiras WHERE slug = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()
        if feira:
            feira_formatada = format_feira_data(dict(feira))
            # Reutiliza o mesmo template
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            return "Feira não encontrada", 404
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO: A tabela 'outrasfeiras' não foi encontrada no banco de dados.")
         return "Erro: Categoria de feira não encontrada.", 500
    except psycopg2.errors.UndefinedColumn:
         print(f"ERRO: A coluna 'slug' não foi encontrada na tabela 'outrasfeiras'.")
         return "Erro: Estrutura da tabela de feiras incorreta.", 500
    except Exception as e:
        print(f"ERRO na rota /outrasfeiras/{slug}: {e}")
        traceback.print_exc() # Log detalhado no Render
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()

# --- ROTAS API (ATUALIZADAS COM MAIS TRY-EXCEPT E LOGS) ---

@app.route('/api/filtros')
def get_filtros():
    conn = None # Definir conn como None inicialmente
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Usando a tabela 'feiras' original para filtros, assumindo que ela ainda existe
        cur.execute('SELECT DISTINCT bairro FROM feiras ORDER BY bairro;')
        bairros_db = cur.fetchall()
        cur.close()

        filtros = {}
        for item in bairros_db:
            bairro = item.get('bairro') # Usar .get()
            if bairro: # Ignorar bairros nulos ou vazios
                regiao = BAIRRO_REGIAO_MAP.get(bairro.strip().upper(), 'Outras') # Normalizar bairro
                if regiao not in filtros:
                    filtros[regiao] = []
                if bairro not in filtros[regiao]: # Evitar duplicados se houver casing diferente
                     filtros[regiao].append(bairro)

        # Ordenar os bairros dentro de cada região
        for regiao in filtros:
            filtros[regiao].sort()

        return jsonify(filtros)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/filtros: A tabela 'feiras' não foi encontrada no banco.")
         return jsonify({'error': "Erro interno ao buscar filtros (tabela 'feiras' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/filtros: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar filtros.'}), 500
    finally:
        if conn: conn.close()


@app.route('/api/feiras')
def get_feiras():
    conn = None # Definir conn como None inicialmente
    try:
        limite_query = request.args.get('limite', default=1000, type=int)
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute('SELECT * FROM feiras ORDER BY id LIMIT %s;', (limite_query,))
        feiras = cur.fetchall()
        cur.close()
        # Formata datas/horas antes de enviar JSON (se houver colunas de data/hora)
        feiras_processadas = [format_feira_data(dict(f)) for f in feiras]
        return jsonify(feiras_processadas)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/feiras: A tabela 'feiras' não foi encontrada no banco.")
         return jsonify({'error': "Erro interno ao buscar feiras livres (tabela 'feiras' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/feiras: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar feiras livres.'}), 500
    finally:
        if conn: conn.close()

# --- FUNÇÃO HELPER PARA PROCESSAR FEIRAS COM SLUG ---
def process_feiras_com_slug(feiras_raw, tipo_rota):
    feiras_processadas = []
    for feira in feiras_raw:
        feira_dict = dict(feira)
        # Formata datas/horas para ISO e converte Decimals para float
        for key, value in feira_dict.items():
            if isinstance(value, (datetime.date, datetime.time)):
                feira_dict[key] = value.isoformat() if value else None
            elif isinstance(value, decimal.Decimal):
                feira_dict[key] = float(value)

        # Tenta pegar o slug, se não existir, loga um aviso
        slug = feira_dict.get('slug')
        if slug:
            feira_dict['url'] = f'/{tipo_rota}/{slug}'
            feiras_processadas.append(feira_dict)
        else:
            print(f"AVISO: Feira ID {feira_dict.get('id')} na tabela '{tipo_rota}' não possui um 'slug'. Não será incluída na API.")
            
    return feiras_processadas

@app.route('/api/gastronomicas')
def get_gastronomicas():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # CORREÇÃO: Alterado de SELECT explícito para SELECT * para evitar erro se a coluna 'slug' não existir.
        cur.execute('SELECT * FROM gastronomicas ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = process_feiras_com_slug(feiras_raw, 'gastronomicas')
        return jsonify(feiras_processadas)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/gastronomicas: A tabela 'gastronomicas' não foi encontrada.")
         return jsonify({'error': "Erro interno ao buscar feiras (tabela 'gastronomicas' ausente)."}), 500
    except psycopg2.errors.UndefinedColumn as e:
         print(f"ERRO em /api/gastronomicas: Coluna não encontrada - {e}")
         traceback.print_exc() # Log detalhado no Render
         return jsonify({'error': "Erro interno: Estrutura da tabela 'gastronomicas' incorreta."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/gastronomicas: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar feiras gastronômicas.'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/artesanais')
def get_artesanais():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # CORREÇÃO: Alterado de SELECT explícito para SELECT * para evitar erro se a coluna 'slug' não existir.
        cur.execute('SELECT * FROM artesanais ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = process_feiras_com_slug(feiras_raw, 'artesanais')
        return jsonify(feiras_processadas)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/artesanais: A tabela 'artesanais' não foi encontrada.")
         return jsonify({'error': "Erro interno ao buscar feiras (tabela 'artesanais' ausente)."}), 500
    except psycopg2.errors.UndefinedColumn as e:
         print(f"ERRO em /api/artesanais: Coluna não encontrada - {e}")
         traceback.print_exc() # Log detalhado no Render
         return jsonify({'error': "Erro interno: Estrutura da tabela 'artesanais' incorreta."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/artesanais: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar feiras artesanais.'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/outrasfeiras')
def get_outrasfeiras():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # CORREÇÃO: Alterado de SELECT explícito para SELECT * para evitar erro se a coluna 'slug' não existir.
        cur.execute('SELECT * FROM outrasfeiras ORDER BY id;')
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = process_feiras_com_slug(feiras_raw, 'outrasfeiras')
        return jsonify(feiras_processadas)
    except psycopg2.errors.UndefinedTable:
         print(f"ERRO em /api/outrasfeiras: A tabela 'outrasfeiras' não foi encontrada.")
         return jsonify({'error': "Erro interno ao buscar feiras (tabela 'outrasfeiras' ausente)."}), 500
    except psycopg2.errors.UndefinedColumn as e:
         print(f"ERRO em /api/outrasfeiras: Coluna não encontrada - {e}")
         traceback.print_exc() # Log detalhado no Render
         return jsonify({'error': "Erro interno: Estrutura da tabela 'outrasfeiras' incorreta."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/outrasfeiras: {e}")
        traceback.print_exc() # Log detalhado no Render
        return jsonify({'error': 'Erro interno ao buscar outras feiras.'}), 500
    finally:
        if conn: conn.close()

# --- ROTA DE SUBMISSÃO (ATUALIZADA com try-except) ---
@app.route('/submit-fair', methods=['POST'])
def handle_submission():
    conn = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Nenhum dado recebido.'}), 400

        # Validação simples
        required_fields = ['nomeFeira', 'enderecoCompleto']
        if not all(field in data and data[field] for field in required_fields):
            return jsonify({'success': False, 'message': 'Campos obrigatórios ausentes.'}), 400

        conn = get_db_connection()
        cur = conn.cursor()
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
         print(f"ERRO em /submit-fair: A tabela 'contato' não foi encontrada.")
         if conn: conn.rollback()
         return jsonify({'success': False, 'message': "Erro interno ao processar submissão (tabela 'contato' ausente)."}), 500
    except Exception as e:
        print(f"ERRO no endpoint /submit-fair: {e}")
        traceback.print_exc() # Log detalhado no Render
        if conn: conn.rollback()
        return jsonify({'success': False, 'message': 'Erro interno ao processar submissão.'}), 500
    finally:
        if conn: conn.close()

# --- ROTA CORINGA E EXECUÇÃO (SEM ALTERAÇÃO) ---
# A ROTA CORINGA FOI REMOVIDA PARA RESTAURAR O COMPORTAMENTO PADRÃO DO FLASK
# E CORRIGIR O PROBLEMA DE ROTEAMENTO.


# O Flask, por padrão, já serve os arquivos da pasta definida em 'static_folder'.
# Como definimos static_folder='.', ele automaticamente servirá 'gastronomicas.html',
# 'artesanais.html', etc., quando o navegador solicitar.
# As rotas específicas como '/gastronomicas/<slug>' continuarão funcionando normalmente.

@app.route('/<path:path>')
def serve_static_files(path):
    # Evita servir o próprio app.py ou arquivos .env
    if path == "app.py" or path.endswith(".env"):
        return "Not Found", 404
    # Se o caminho solicitado for um arquivo que existe, sirva-o
    if os.path.isfile(os.path.join('.', path)):
        return send_from_directory('.', path)
    # Se não for um arquivo, retorna 404
    return "Not Found", 404

if __name__ == '__main__':
    # Configura o log para ser mais detalhado
    import logging
    logging.basicConfig(level=logging.INFO)
    # Usa a porta definida pelo Render ou 10000 para desenvolvimento local se compatível
    port = int(os.environ.get("PORT", 10000))
    # debug=False é crucial para produção no Render. Use True só localmente.
    app.run(host="0.0.0.0", port=port, debug=False)

