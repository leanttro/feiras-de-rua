import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response, redirect
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import traceback
import decimal
import json

# --- INÍCIO DA SEÇÃO DO CHATBOT ---
import google.generativeai as genai
# --- FIM DA SEÇÃO DO CHATBOT ---


# Carrega variáveis de ambiente de um arquivo .env, se existir
load_dotenv()

# --- INÍCIO DA SEÇÃO DO CHATBOT ---
# Configura a API Key do Gemini a partir das variáveis de ambiente
try:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("ERRO CRÍTICO: Variável de ambiente GEMINI_API_KEY não encontrada.")
    else:
        genai.configure(api_key=api_key)
        print("API Key do Gemini configurada com sucesso.")
except Exception as e:
    print(f"Erro ao configurar a API do Gemini: {e}")
# --- FIM DA SEÇÃO DO CHATBOT ---


# Inicializa o aplicativo Flask
app = Flask(__name__, static_folder='.', static_url_path='', template_folder='templates')
CORS(app)

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    conn = None
    try:
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
            try:
                formatted_dict[key] = float(value)
            except (TypeError, ValueError):
                formatted_dict[key] = None
        else:
            formatted_dict[key] = value
    return formatted_dict


# --- INÍCIO DA SEÇÃO DO CHATBOT ---

def get_all_data_for_bot():
    """
    Busca dados das tabelas 'feiras' e 'feiras_livres' para alimentar o chatbot.
    """
    all_data = {}
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT id, nome_feira, tipo_feira, dia_semana, horario_inicio, horario_fim, 
                   rua, regiao, bairro, descricao, latitude, longitude 
            FROM feiras ORDER BY nome_feira
        """)
        feiras_raw = cur.fetchall()
        all_data['feiras_especiais'] = [format_db_data(dict(f)) for f in feiras_raw]
        
        cur.execute("""
            SELECT id, nome_da_feira, dia_da_feira, endereco, bairro, latitude, longitude
            FROM feiras_livres ORDER BY nome_da_feira
        """)
        feiras_livres_raw = cur.fetchall()
        all_data['feiras_livres'] = [format_db_data(dict(f)) for f in feiras_livres_raw]
        
        cur.close()
        print(f"Dados do Bot carregados: {len(all_data['feiras_especiais'])} feiras especiais, {len(all_data['feiras_livres'])} feiras livres.")
        return all_data
    except Exception as e:
        print(f"ERRO CRÍTICO ao buscar dados para o bot: {e}")
        traceback.print_exc()
        return None
    finally:
        if conn: conn.close()


print("Buscando dados das feiras no DB para inicializar o bot...")
bot_data = get_all_data_for_bot()

model = None
chat_session = None

if bot_data:
    feiras_especiais_json = json.dumps(bot_data['feiras_especiais'], separators=(',', ':'))
    feiras_livres_json = json.dumps(bot_data['feiras_livres'], separators=(',', ':'))
    
    SYSTEM_PROMPT = f"""
Você é o "Feirinha - Chatbot", o assistente virtual especialista do site feirasderua.com.br.
Sua missão é ajudar os usuários a encontrar feiras em São Paulo USANDO APENAS A BASE DE DADOS FORNECIDA.

REGRAS ESTRITAS:
1.  **NÃO ALUCINE:** Você NUNCA deve inventar uma feira, endereço ou dia. Se a informação não estiver nas listas JSON abaixo, diga que não encontrou.
2.  **USE OS DADOS:** Baseie 100% das suas respostas nos dados JSON fornecidos. Ao citar uma feira, use o nome, dia, endereço/rua e bairro EXATOS da lista.
3.  **SEJA UM ESPECIALISTA:** Aja como um especialista que conhece o banco de dados. Seja direto ao ponto.
4.  **FOCO TOTAL:** Responda apenas sobre feiras. Recuse educadamente outros assuntos. ("Desculpe, meu foco é só te ajudar com as feiras de São Paulo! 🧺 Posso te ajudar a encontrar uma?")
5.  **AMIGÁVEL E CONCISO:** Mantenha o tom amigável (use ☀️, 🧺, 🍓) e responda em no máximo 3-4 frases.

6.  **LIDANDO COM "QUASE ACERTOS" (LOCAL CERTO, DIA ERRADO):**
    * Se o usuário pedir uma feira em um local E dia específico (ex: "feira na Vila Santa Catarina no Domingo"), e você encontrar a feira nesse LOCAL, mas ela acontece em OUTRO DIA:
        * **Informe o usuário:** "Ótima escolha! Encontrei [Nome da Feira] exatamente na [Localização], mas ela acontece aos [Dia Correto da Feira]."
        * **Ofereça opções CLARAS:** "Você prefere que eu procure opções de [Dia que o usuário pediu] em bairros vizinhos ou quer mais detalhes sobre essa feira de [Dia Correto da Feira]?"
    * **NÃO liste feiras aleatórias de outros dias ou locais distantes sem perguntar antes.** Priorize a intenção do usuário (dia ou local).

--- BASE DE DADOS (JSON) ---
Use estas duas listas para TODAS as suas respostas. Compare o pedido do usuário com os campos 'nome_feira'/'nome_da_feira', 'bairro', 'rua'/'endereco', 'dia_semana'/'dia_da_feira'.

LISTA 1: Feiras Especiais (Gastronômicas, Artesanais, etc. Tabela 'feiras')
{feiras_especiais_json}

LISTA 2: Feiras Livres (Tradicionais. Tabela 'feiras_livres')
{feiras_livres_json}
--- FIM DA BASE DE DADOS ---
"""
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest') 
        
        chat_session = model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [SYSTEM_PROMPT]
                },
                {
                    "role": "model",
                    "parts": ["Entendido! Sou o Feirinha - Chatbot. Meu conhecimento vem 100% das listas de feiras fornecidas. Estou pronto para ajudar a encontrar feiras cadastradas! 🧺🍓"]
                }
            ]
        )
        print("Modelo 'gemini-flash-latest' inicializado com SUCESSO e alimentado com os dados do DB.")

    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível inicializar o GenerativeModel. {e}")
        traceback.print_exc()
else:
    print("ERRO CRÍTICO: Não foi possível buscar dados do DB para o bot. O chat não vai funcionar.")
    model = None
    chat_session = None


@app.route('/api/chat', methods=['POST'])
def handle_chat():
    if not model or not chat_session:
        print("Erro: A sessão do chat com o Gemini não foi inicializada.")
        return jsonify({'error': 'Serviço de chat indisponível no momento.'}), 503

    try:
        data = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'Mensagem não pode ser vazia.'}), 400

        response = chat_session.send_message(
            user_message,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7 
            ),
            safety_settings={
                 'HATE': 'BLOCK_NONE',
                 'HARASSMENT': 'BLOCK_NONE',
                 'SEXUAL' : 'BLOCK_NONE',
                 'DANGEROUS' : 'BLOCK_NONE'
            }
        )

        return jsonify({'reply': response.text})

    except genai.types.generation_types.StopCandidateException as stop_ex:
        print(f"API BLOQUEOU a resposta por segurança: {stop_ex}")
        return jsonify({'reply': "Desculpe, não posso gerar uma resposta para essa solicitação específica. Posso ajudar com informações sobre feiras?"})
    
    except Exception as e:
        print(f"Erro ao chamar a API do Gemini: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Ocorreu um erro ao processar sua mensagem.'}), 503

# --- FIM DA SEÇÃO DO CHATBOT ---


# ─────────────────────────────────────────
#  HELPER: BUSCAR ANÚNCIO ATIVO
# ─────────────────────────────────────────
def _get_anuncio_feiras(posicao, bairro=None):
    """
    Busca um anúncio ativo da tabela 'anuncios' com rotação por RANDOM().

    Args:
        posicao: 'topo' ou 'meio'
        bairro: nome do bairro (opcional) - prioriza anúncios do bairro

    Lógica:
    1. Se bairro é informado: primeiro busca anúncios específicos do bairro
    2. Se não achou ou bairro é None: busca anúncios "Global" (bairro=None)
    3. Usa RANDOM() para rotação de anúncios
    4. Respeita data_inicio e data_fim
    """
    conn = None
    try:
        from datetime import date
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        hoje = date.today()
        
        # Primeiro: tenta buscar anúncio específico do bairro
        if bairro:
            cur.execute("""
                SELECT id, titulo, foto_url, link, posicao, data_inicio, data_fim, ativo, bairro
                FROM anuncios
                WHERE 
                    posicao = %s 
                    AND ativo = true
                    AND LOWER(bairro) = LOWER(%s)
                    AND (data_inicio IS NULL OR data_inicio <= %s)
                    AND (data_fim IS NULL OR data_fim >= %s)
                ORDER BY RANDOM()
                LIMIT 1
            """, (posicao, bairro, hoje, hoje))
            
            row = cur.fetchone()
            if row:
                cur.close()
                return format_db_data(dict(row))
        
        # Se não achou bairro-específico, busca anúncios "Global" com rotação
        cur.execute("""
            SELECT id, titulo, foto_url, link, posicao, data_inicio, data_fim, ativo, bairro
            FROM anuncios
            WHERE 
                posicao = %s 
                AND ativo = true
                AND (bairro IS NULL OR bairro = '')
                AND (data_inicio IS NULL OR data_inicio <= %s)
                AND (data_fim IS NULL OR data_fim >= %s)
            ORDER BY RANDOM()
            LIMIT 1
        """, (posicao, hoje, hoje))
        
        row = cur.fetchone()
        cur.close()
        
        if row:
            return format_db_data(dict(row))
        return None
        
    except Exception as e:
        print(f"ERRO em _get_anuncio_feiras('{posicao}', bairro='{bairro}'): {e}")
        return None
    finally:
        if conn: conn.close()

@app.route('/index.html')
def index_html_route():
    # Rota explícita para /index.html — necessária pois o arquivo está em /templates/
    return render_template('index.html', 
                          anuncio_topo=_get_anuncio_feiras('topo'),
                          anuncio_meio=_get_anuncio_feiras('meio'))
# --- NOVA ROTA PARA FEIRAS LIVRES ---
@app.route('/api/feiras_livres')
def get_api_feiras_livres():
    """Retorna uma lista JSON de todas as feiras livres da tabela 'feiras_livres'."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = """
        SELECT id, nome_da_feira, dia_da_feira, categoria, qnt_feirantes, 
               endereco, bairro, latitude, longitude
        FROM feiras_livres
        ORDER BY dia_da_feira, nome_da_feira;
        """
        
        cur.execute(query)
        feiras_raw = cur.fetchall()
        cur.close()

        feiras_processadas = [format_db_data(dict(feira)) for feira in feiras_raw]

        import re, unicodedata
        def to_slug(s):
            if not s: return ''
            s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
            return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
        for f in feiras_processadas:
            f['slug'] = to_slug(f.get('bairro', '')) or str(f.get('id', ''))

        return jsonify(feiras_processadas)
        
    except psycopg2.errors.UndefinedTable:
        print("ERRO: A tabela 'feiras_livres' não foi encontrada no banco de dados.")
        return jsonify({'error': 'Tabela feiras_livres não encontrada.'}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/feiras_livres: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar feiras livres.'}), 500
    finally:
        if conn: conn.close()


# --- ROTA PARA BUSCAR POSTS DO BLOG (API) ---
@app.route('/api/blog')
def get_api_blog():
    """Retorna uma lista JSON de todos os posts da tabela 'blog'."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        query = "SELECT * FROM blog ORDER BY data_publicacao DESC, id DESC;"
        
        cur.execute(query)
        posts_raw = cur.fetchall()
        cur.close()

        posts_processados = [format_db_data(dict(post)) for post in posts_raw]

        return jsonify(posts_processados)
        
    except psycopg2.errors.UndefinedTable:
        print("ERRO: A tabela 'blog' não foi encontrada no banco de dados.")
        return jsonify({'error': 'Tabela blog não encontrada.'}), 500
    except Exception as e:
        print(f"ERRO no endpoint /api/blog: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar posts do blog.'}), 500
    finally:
        if conn: conn.close()

# --- ROTAS DE DETALHE DE CONTEÚDO (DEVE VIR ANTES DA ROTA ESTÁTICA) ---

# ROTA PARA RENDERIZAR UMA PÁGINA DE POST DO BLOG
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
            return render_template('post-detalhe.html', post=post_formatado)
        else:
            print(f"AVISO: Post do blog com slug '{slug}' não encontrado.")
            return "Post não encontrado", 404
            
    except Exception as e:
        print(f"ERRO na rota /blog/{slug}: {e}")
        traceback.print_exc()
        return "Erro ao carregar a página do post", 500
    finally:
        if conn: conn.close()
        
# ROTA DE DETALHE ÚNICA PARA FEIRAS
@app.route('/feiras/<path:slug>') 
def feira_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # ✅ SEO: Se o slug for numérico (ID antigo), redireciona 301 para a URL com slug correto
        if slug.isdigit():
            cur.execute('SELECT url FROM feiras WHERE CAST(id AS VARCHAR) = %s AND url IS NOT NULL AND url != \'\';', (slug,))
            row = cur.fetchone()
            cur.close()
            if row and row['url']:
                print(f"SEO 301: Redirecionando /feiras/{slug} → /feiras/{row['url']}")
                return redirect(f"/feiras/{row['url']}", code=301)
            else:
                # ID sem slug cadastrado — renderiza normalmente pelo ID
                conn2 = get_db_connection()
                cur2 = conn2.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur2.execute('SELECT * FROM feiras WHERE CAST(id AS VARCHAR) = %s;', (slug,))
                feira = cur2.fetchone()
                cur2.close()
                conn2.close()
                if feira:
                    feira_formatada = format_db_data(dict(feira))
                    return render_template('feira-detalhe.html', feira=feira_formatada)
                else:
                    return "Feira não encontrada", 404

        # Busca pelo campo 'url' (slug)
        cur.execute('SELECT * FROM feiras WHERE url = %s;', (slug,))
        feira = cur.fetchone()
        cur.close()

        if feira:
            feira_formatada = format_db_data(dict(feira))
            return render_template('feira-detalhe.html', feira=feira_formatada)
        else:
            print(f"AVISO: Feira com slug/url '{slug}' não encontrada.")
            return "Feira não encontrada", 404
            
    except Exception as e:
        print(f"ERRO na rota /feiras/{slug}: {e}")
        traceback.print_exc()
        return "Erro ao carregar a página da feira", 500
    finally:
        if conn: conn.close()


# --- ROTAS DE API ---

@app.route('/api/feiras/tipos')
def get_tipos_feira():
    """Retorna uma lista JSON com todos os valores únicos de 'tipo_feira'."""
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


@app.route('/api/feiras')
def get_api_feiras():
    conn = None
    try:
        tipo_feira_filtro = request.args.get('tipo')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = "SELECT *, CAST(id AS VARCHAR) as effective_slug FROM feiras"
        params = []

        if tipo_feira_filtro:
            query += " WHERE tipo_feira ILIKE %s"
            params.append(f"%{tipo_feira_filtro}%")

        query += " ORDER BY nome_feira;"

        cur.execute(query, tuple(params))
        feiras_raw = cur.fetchall()
        cur.close()

        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = format_db_data(dict(feira))
            feira_slug = feira_dict.get('url') if feira_dict.get('url') else feira_dict.get('id')
            feira_dict['url'] = f'/feiras/{feira_slug}'
            feira_dict['effective_slug'] = feira_dict['id']
            feiras_processadas.append(feira_dict)

        return jsonify(feiras_processadas)

    except Exception as e:
        print(f"ERRO no endpoint /api/feiras: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar feiras.'}), 500
    finally:
        if conn: conn.close()
        
@app.route('/feira-livre/<slug>')
def feira_livre_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Busca todas e filtra pelo slug em Python (sem UNACCENT)
        cur.execute("SELECT * FROM feiras_livres")
        todas = cur.fetchall()
        cur.close()

        import re, unicodedata
        def to_slug(s):
            if not s: return ''
            s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
            return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

        feira = None
        for row in todas:
            row = dict(row)
            if to_slug(row.get('bairro', '')) == slug:
                feira = row
                break

        # fallback por id
        if not feira:
            for row in todas:
                row = dict(row)
                if str(row.get('id', '')) == slug:
                    feira = row
                    break

        if not feira:
            return "Feira não encontrada", 404

        # Passa bairro para priorizar anúncios desse bairro
        bairro = feira.get('bairro')

        return render_template('feira-livre-detalhe.html', 
                              feira=feira,
                              anuncio_topo=_get_anuncio_feiras('topo', bairro=bairro), 
                              anuncio_meio=_get_anuncio_feiras('meio', bairro=bairro))
    except Exception as e:
        print(f"ERRO em /feira-livre/{slug}: {e}")
        return "Erro interno", 500
    finally:
        if conn: conn.close()


# --- ROTAS DE COMPATIBILIDADE ---
@app.route('/api/gastronomicas')
def get_gastronomicas_compat():
    return get_api_feiras_filtrado('Gastronômica')

@app.route('/api/artesanais')
def get_artesanais_compat():
    return get_api_feiras_filtrado('Artesanal')

def get_api_feiras_filtrado(tipo_feira):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = "SELECT *, CAST(id AS VARCHAR) as effective_slug FROM feiras WHERE tipo_feira ILIKE %s ORDER BY nome_feira;"
        cur.execute(query, (f"%{tipo_feira}%",))
        feiras_raw = cur.fetchall()
        cur.close()
        
        feiras_processadas = []
        for feira in feiras_raw:
            feira_dict = format_db_data(dict(feira))
            feira_slug = feira_dict.get('url') if feira_dict.get('url') else feira_dict.get('id')
            feira_dict['url'] = f'/feiras/{feira_slug}'
            feiras_processadas.append(feira_dict)
        return jsonify(feiras_processadas)

    except Exception as e:
        print(f"ERRO em rota de compatibilidade: {e}")
        return jsonify({'error': 'Erro interno.'}), 500
    finally:
        if conn: conn.close()


@app.route('/feiras-livres.html')
def feiras_livres_page():
    return render_template('feiras-livres.html', 
                          anuncio_topo=_get_anuncio_feiras('topo'), 
                          anuncio_meio=_get_anuncio_feiras('meio'))


# --- ROTAS PARA SERVIR ARQUIVOS ESTÁTICOS ---

@app.route('/')
def index_route():
    return render_template('index.html', 
                          anuncio_topo=_get_anuncio_feiras('topo'), 
                          anuncio_meio=_get_anuncio_feiras('meio'))

@app.route('/<path:path>')
def serve_static_files(path):
    basename = os.path.basename(path)
    if '.' not in basename:
        print(f"AVISO: Tentativa de acesso a um slug não encontrado (sem ponto no basename): {path}")
        return "Not Found", 404
        
    if os.path.exists(os.path.join('.', path)):
        return send_from_directory('.', path)
    else:
        print(f"AVISO: Arquivo estático não encontrado: {path}")
        return "Not Found", 404


# --- ROTA DO ADS.TXT ---
@app.route('/ads.txt')
def ads_txt():
    return "google.com, pub-7617881885143728, DIRECT, f08c47fec0942fa0", 200, {'Content-Type': 'text/plain'}
# --- FIM DA ROTA DO ADS.TXT ---


# --- ROTA DO SITEMAP ---
@app.route('/sitemap.xml')
def sitemap():
    conn = None
    hoje = datetime.date.today().isoformat()  # ✅ Data atual para o lastmod

    # Páginas estáticas com prioridade alta
    paginas_estaticas = [
        ('https://www.feirasderua.com.br/', '1.0', 'daily'),
        ('https://www.feirasderua.com.br/gastronomicas.html', '0.9', 'weekly'),
        ('https://www.feirasderua.com.br/artesanais.html', '0.9', 'weekly'),
        ('https://www.feirasderua.com.br/feiras-livres.html', '0.9', 'weekly'),
        ('https://www.feirasderua.com.br/contato.html', '0.5', 'monthly'),
        ('https://www.feirasderua.com.br/anuncie.html', '0.5', 'monthly'),
    ]

    # Páginas dinâmicas (feiras e blog)
    paginas_dinamicas = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ✅ SEO: Só inclui feiras que têm slug (url) preenchido — evita duplicatas com IDs
        cur.execute("SELECT url FROM feiras WHERE url IS NOT NULL AND url != '';")
        for row in cur.fetchall():
            paginas_dinamicas.append((f'https://www.feirasderua.com.br/feiras/{row[0]}', '0.8', 'weekly'))

        cur.execute("SELECT slug FROM blog WHERE slug IS NOT NULL AND slug != '';")
        for row in cur.fetchall():
            paginas_dinamicas.append((f'https://www.feirasderua.com.br/blog/{row[0]}', '0.7', 'weekly'))

        # Páginas de detalhe de feiras livres
        import re, unicodedata
        def to_slug(s):
            if not s: return ''
            s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()
            return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

        cur.execute("SELECT bairro FROM feiras_livres WHERE bairro IS NOT NULL AND bairro != '';")
        for row in cur.fetchall():
            slug = to_slug(row[0])
            if slug:
                paginas_dinamicas.append((f'https://www.feirasderua.com.br/feira-livre/{slug}', '0.7', 'weekly'))

        cur.close()
    except Exception as e:
        print(f"AVISO: Erro ao buscar URLs dinâmicas para o sitemap: {e}")
    finally:
        if conn: conn.close()

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for url, priority, changefreq in paginas_estaticas:
        xml += (
            f'  <url>'
            f'<loc>{url}</loc>'
            f'<lastmod>{hoje}</lastmod>'          # ✅ lastmod adicionado
            f'<changefreq>{changefreq}</changefreq>'
            f'<priority>{priority}</priority>'
            f'</url>\n'
        )

    for url, priority, changefreq in paginas_dinamicas:
        xml += (
            f'  <url>'
            f'<loc>{url}</loc>'
            f'<lastmod>{hoje}</lastmod>'          # ✅ lastmod adicionado
            f'<changefreq>{changefreq}</changefreq>'
            f'<priority>{priority}</priority>'
            f'</url>\n'
        )

    xml += '</urlset>'
    return make_response(xml, 200, {'Content-Type': 'application/xml'})
# --- FIM DA ROTA DO SITEMAP ---


# Execução do App
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
