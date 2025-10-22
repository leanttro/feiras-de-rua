import os
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, request, send_from_directory, render_template, make_response
from dotenv import load_dotenv
from flask_cors import CORS
import datetime
import traceback
import decimal

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
        # Mesmo com o erro, o app Flask continua, mas a rota /api/chat vai falhar.
    else:
        genai.configure(api_key=api_key)
        print("API Key do Gemini configurada com sucesso.")
except Exception as e:
    print(f"Erro ao configurar a API do Gemini: {e}")
# --- FIM DA SEÇÃO DO CHATBOT ---


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
            # Converte Decimal para float para ser compatível com JSON, tratando None/NaN
            try:
                formatted_dict[key] = float(value)
            except (TypeError, ValueError):
                formatted_dict[key] = None
        else:
            formatted_dict[key] = value
    return formatted_dict


# --- INÍCIO DA SEÇÃO DO CHATBOT ---

# Define o "Prompt de Sistema" (personalidade) do chatbot
SYSTEM_PROMPT = """
Você é o "Feirinha - Chatbot", o assistente virtual amigável do site feirasderua.com.br.
Sua missão é ajudar os usuários a encontrar informações sobre feiras em São Paulo.
REGRAS ESTRITAS:
1.  **Seja Amigável e prestativo:** Use emojis leves (como ☀️, 🧺, 🍓) quando apropriado.
2.  **Seja Conciso:** Responda em no máximo 3 frases.
3.  **Foco Total:** Responda *APENAS* sobre feiras de rua em São Paulo (livres, gastronômicas, artesanais), eventos relacionados ou sobre o próprio site feirasderua.com.br.
4.  **Recuse outros assuntos:** Se o usuário perguntar sobre qualquer outro tópico (como política, esportes, receitas, como fazer um bolo, quem descobriu o Brasil, etc.), recuse educadamente e redirecione o foco.
    * Exemplo de recusa: "Desculpe, eu sou o 'Feirinha' e meu foco é só te ajudar com as feiras de São Paulo! 🧺 Posso te ajudar a encontrar uma feira?"
"""

# Inicializa o modelo
try:
    # ############ CORREÇÃO APLICADA AQUI ############
    # O modelo 'gemini-pro' foi descontinuado ou movido.
    # Usando 'gemini-1.5-flash-latest' que é o modelo mais recente e rápido.
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    # Inicia um chat com o histórico (incluindo o prompt do sistema)
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [SYSTEM_PROMPT]
            },
            {
                "role": "model",
                "parts": ["Entendido! Eu sou o Feirinha - Chatbot. Estou pronto para ajudar apenas com informações sobre as feiras de rua de São Paulo e o site feirasderua.com.br."]
            }
        ]
    )
except Exception as e:
    print(f"ERRO CRÍTICO: Não foi possível inicializar o GenerativeModel. {e}")
    model = None
    chat_session = None

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    if not model or not chat_session:
        print("Erro: A sessão do chat com o Gemini não foi inicializada.")
        return jsonify({'error': 'Serviço de chat indisponível.'}), 503

    try:
        data = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'Mensagem não pode ser vazia.'}), 400

        # Envia a mensagem para o Gemini (o histórico é mantido no 'chat_session')
        response = chat_session.send_message(user_message)

        # Retorna a resposta do modelo para o front-end
        return jsonify({'reply': response.text})

    except Exception as e:
        # Se der um erro (ex: 404 do log, ou outro erro da API)
        print(f"Erro ao chamar a API do Gemini: {e}")
        traceback.print_exc()
        # Retorna um erro 503 (Serviço Indisponível) para o front-end
        return jsonify({'error': 'Ocorreu um erro ao processar sua mensagem.'}), 503

# --- FIM DA SEÇÃO DO CHATBOT ---


# --- NOVA ROTA PARA FEIRAS LIVRES ---
@app.route('/api/feiras_livres')
def get_api_feiras_livres():
    """Retorna uma lista JSON de todas as feiras livres da tabela 'feiras_livres'."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Seleciona todas as colunas
        query = """
        SELECT id, nome_da_feira, dia_da_feira, categoria, qnt_feirantes, 
               endereco, bairro, latitude, longitude
        FROM feiras_livres
        ORDER BY dia_da_feira, nome_da_feira;
        """
        
        cur.execute(query)
        feiras_raw = cur.fetchall()
        cur.close()

        # Processa os dados
        feiras_processadas = [format_db_data(dict(feira)) for feira in feiras_raw]

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
        
        # Busca todos os campos da tabela 'blog'
        query = "SELECT * FROM blog ORDER BY data_publicacao DESC, id DESC;"
        
        cur.execute(query)
        posts_raw = cur.fetchall()
        cur.close()

        # Processa os dados (formatação de datas, etc.)
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

# --- ROTA PARA RENDERIZAR UMA PÁGINA DE POST DO BLOG ---
# ############ CORREÇÃO FINAL APLICADA AQUI ############
# Ex: /blog/onde-encontrar-feiras-livres-em-santana (sem .html)
@app.route('/blog/<slug>')
def blog_post_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Busca na tabela 'blog' pelo slug exato
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
        

# --- ROTA PARA BUSCAR OS TIPOS DE FEIRA DISTINTOS ---
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


# --- ROTA DE DETALHE ÚNICA PARA FEIRAS ---
# Ex: /feiras/feira-da-liberdade
@app.route('/feiras/<slug>')
def feira_detalhe(slug):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM feiras WHERE url LIKE %s;', (f'%/{slug}',))
        feira = cur.fetchone()
        cur.close()

        if feira:
            feira_formatada = format_db_data(dict(feira))
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


# --- ROTA DE API PRINCIPAL PARA FEIRAS ---
@app.route('/api/feiras')
def get_api_feiras():
    conn = None
    try:
        tipo_feira_filtro = request.args.get('tipo')
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = "SELECT * FROM feiras"
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
            url_relativa = feira_dict.get('url')
            if url_relativa:
                feira_dict['url'] = url_relativa
                feiras_processadas.append(feira_dict)
            else:
                 feira_dict['url'] = f'/feiras/{feira_dict.get("slug", feira_dict.get("id"))}'
                 feiras_processadas.append(feira_dict)


        return jsonify(feiras_processadas)

    except Exception as e:
        print(f"ERRO no endpoint /api/feiras: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Erro interno ao buscar feiras.'}), 500
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
    # Esta função é para manter compatibilidade, a nova abordagem usa /api/feiras?tipo=...
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        query = "SELECT * FROM feiras WHERE tipo_feira ILIKE %s ORDER BY nome_feira;"
        cur.execute(query, (f"%{tipo_feira}%",))
        feiras_raw = cur.fetchall()
        cur.close()
        feiras_processadas = [format_db_data(dict(f)) for f in feiras_raw]
        return jsonify(feiras_processadas)
    except Exception as e:
        print(f"ERRO em rota de compatibilidade: {e}")
        return jsonify({'error': 'Erro interno.'}), 500
    finally:
        if conn: conn.close()

# --- ROTAS PARA SERVIR ARQUIVOS ---

# Rota para a página principal
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Rota para servir arquivos estáticos de pastas (assets, etc.)
# Esta rota lida com qualquer caminho que pareça um arquivo com extensão
@app.route('/<path:path>')
def serve_static_files(path):
    # Impede que capture as rotas de slug como /feiras/feira-da-liberdade
    # Apenas serve o arquivo se ele tiver uma extensão (ex: .css, .js, .png, .html)
    if '.' in os.path.basename(path):
        return send_from_directory('.', path)
    # Se não tiver extensão, não é um arquivo estático, e as rotas de slug já foram checadas
    return "Not Found", 404

# Execução do App
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)

