import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import os
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(
    page_title="Portal de Formação - SMED POA",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Estilização CSS Personalizada (Minimalista e Cores de POA) ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    h1 {
        color: #2c3e50;
    }
    div[data-testid="stMetricValue"] {
        color: #007bff;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Configuração do Banco de Dados (SQLite) ---
def init_db():
    conn = sqlite3.connect('formacao_smed.db')
    c = conn.cursor()
    # Tabela simples e eficiente para armazenar registros
    c.execute('''
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor TEXT,
            escola TEXT,
            evento TEXT,
            data DATE,
            horas REAL,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(df):
    conn = sqlite3.connect('formacao_smed.db')
    # Assume que o DataFrame já está normalizado
    df.to_sql('registros', conn, if_exists='append', index=False)
    conn.close()

def load_data():
    conn = sqlite3.connect('formacao_smed.db')
    try:
        df = pd.read_sql("SELECT * FROM registros", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# Novas funções para apagar dados
def delete_all_data():
    conn = sqlite3.connect('formacao_smed.db')
    c = conn.cursor()
    c.execute('DELETE FROM registros')
    conn.commit()
    conn.close()

def delete_record(record_id):
    conn = sqlite3.connect('formacao_smed.db')
    c = conn.cursor()
    c.execute('DELETE FROM registros WHERE id=?', (record_id,))
    conn.commit()
    conn.close()

# --- Função de Integração com Gemini ---
def ask_gemini(api_key, query, data_summary):
    if not api_key:
        return "⚠️ Por favor, insira a API Key da Gemini na barra lateral."
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp') # Modelo rápido e eficiente
    
    prompt = f"""
    Você é um assistente especialista em dados da Secretaria de Educação de Porto Alegre.
    Aqui está um resumo dos dados de formação continuada:
    {data_summary}
    
    Pergunta do usuário: {query}
    
    Responda de forma concisa, profissional e em português. Foque em insights pedagógicos ou administrativos.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao consultar Gemini: {e}"

# --- Interface Principal ---

def main():
    init_db()
    
    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Brasao_Porto_Alegre.svg/1200px-Brasao_Porto_Alegre.svg.png", width=80)
    st.sidebar.title("Painel de Controle")
    st.sidebar.markdown("**Secretaria de Educação**\n\nUnidade de Formação Continuada")
    
    # Configuração da API Key (Segurança: input ou variável de ambiente)
    api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Insira sua chave para ativar a IA Analista")
    if not api_key and "GEMINI_API_KEY" in os.environ:
        api_key = os.environ["GEMINI_API_KEY"]

    # Adicionado item "Gerenciar Dados" na navegação
    page = st.sidebar.radio("Navegação", ["Dashboard", "Inserir Planilhas", "Relatórios Detalhados", "Gerenciar Dados", "Assistente IA"])

    # Carregar dados atuais
    df_total = load_data()

    # --- PÁGINA: DASHBOARD ---
    if page == "Dashboard":
        st.title("📊 Visão Geral das Formações")
        
        if df_total.empty:
            st.info("Nenhum dado encontrado. Vá para 'Inserir Planilhas' para começar.")
        else:
            # KPIs
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Horas", f"{df_total['horas'].sum():.1f} h")
            col2.metric("Professores Capacitados", df_total['professor'].nunique())
            col3.metric("Escolas Envolvidas", df_total['escola'].nunique())
            col4.metric("Eventos Realizados", df_total['evento'].nunique())
            
            st.divider()
            
            # Gráficos
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Top 5 Escolas (Horas Totais)")
                top_escolas = df_total.groupby('escola')['horas'].sum().sort_values(ascending=False).head(5)
                st.bar_chart(top_escolas)
                
            with c2:
                st.subheader("Distribuição por Evento")
                top_eventos = df_total['evento'].value_counts().head(5)
                st.bar_chart(top_eventos)

    # --- PÁGINA: UPLOAD ---
    elif page == "Inserir Planilhas":
        st.title("📂 Alimentar Base de Dados")
        st.markdown("Faça upload das listas de presença (Excel). O sistema irá unificar automaticamente.")
        
        uploaded_file = st.file_uploader("Arraste seu arquivo Excel aqui", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                # Ler Excel
                df_upload = pd.read_excel(uploaded_file)
                
                st.write("Prévia dos dados carregados:")
                st.dataframe(df_upload.head())
                
                # Mapeamento de Colunas (Para garantir padronização)
                st.subheader("🔧 Mapear Colunas")
                st.info("Selecione qual coluna do seu Excel corresponde aos campos do sistema.")
                
                cols = df_upload.columns.tolist()
                
                col_prof = st.selectbox("Coluna: Nome do Professor", cols, index=0)
                col_escola = st.selectbox("Coluna: Escola", cols, index=1 if len(cols)>1 else 0)
                col_evento = st.selectbox("Coluna: Nome do Evento", cols, index=2 if len(cols)>2 else 0)
                col_horas = st.selectbox("Coluna: Carga Horária", cols, index=3 if len(cols)>3 else 0)
                
                # Data pode ser input manual ou coluna
                use_date_col = st.checkbox("A data está no arquivo excel?")
                if use_date_col:
                    col_data = st.selectbox("Coluna: Data", cols)
                else:
                    manual_date = st.date_input("Selecione a data do evento")
                
                if st.button("Processar e Salvar no Banco"):
                    # Preparar DataFrame Padronizado
                    df_final = pd.DataFrame()
                    df_final['professor'] = df_upload[col_prof]
                    df_final['escola'] = df_upload[col_escola]
                    df_final['evento'] = df_upload[col_evento]
                    
                    # Tratamento de horas (garantir numérico)
                    df_final['horas'] = pd.to_numeric(df_upload[col_horas], errors='coerce').fillna(0)
                    
                    if use_date_col:
                        df_final['data'] = pd.to_datetime(df_upload[col_data], errors='coerce').dt.date
                    else:
                        df_final['data'] = manual_date
                        
                    save_to_db(df_final)
                    st.success("✅ Dados inseridos com sucesso! O banco de dados foi atualizado.")
                    st.balloons()
                    
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")

    # --- PÁGINA: RELATÓRIOS ---
    elif page == "Relatórios Detalhados":
        st.title("📑 Relatórios Detalhados")
        
        if df_total.empty:
            st.warning("Sem dados.")
        else:
            filter_type = st.selectbox("Filtrar por:", ["Professor", "Escola"])
            
            if filter_type == "Professor":
                prof_list = df_total['professor'].unique()
                selected_prof = st.selectbox("Selecione o Professor", prof_list)
                
                df_filtered = df_total[df_total['professor'] == selected_prof]
                
                st.write(f"**Total de horas de {selected_prof}:** {df_filtered['horas'].sum()}h")
                st.dataframe(df_filtered[['evento', 'data', 'horas', 'escola']])
                
            elif filter_type == "Escola":
                school_list = df_total['escola'].unique()
                selected_school = st.selectbox("Selecione a Escola", school_list)
                
                df_filtered = df_total[df_total['escola'] == selected_school]
                
                st.write(f"**Total de horas da escola {selected_school}:** {df_filtered['horas'].sum()}h")
                
                # Agrupado por professor desta escola
                st.write("Horas por professor nesta escola:")
                st.dataframe(df_filtered.groupby('professor')['horas'].sum().reset_index().sort_values('horas', ascending=False))

    # --- PÁGINA: GERENCIAR DADOS ---
    elif page == "Gerenciar Dados":
        st.title("🗑️ Gerenciar e Apagar Dados")
        
        if df_total.empty:
            st.info("O banco de dados está vazio.")
        else:
            st.markdown("### Visualizar Registros")
            st.dataframe(df_total)
            
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Apagar Registro Específico")
                st.markdown("Use o **ID** da tabela acima para apagar uma linha específica (erro de digitação, duplicidade, etc).")
                record_id_to_delete = st.number_input("Digite o ID do registro:", min_value=0, step=1)
                
                if st.button("Apagar Registro", type="primary"):
                    if record_id_to_delete in df_total['id'].values:
                        delete_record(record_id_to_delete)
                        st.success(f"Registro ID {record_id_to_delete} apagado com sucesso!")
                        st.rerun() # Recarrega a página para atualizar a tabela
                    else:
                        st.error("ID não encontrado no banco de dados.")
            
            with col2:
                st.subheader("Limpar Banco de Dados")
                st.warning("⚠️ Atenção: Esta ação apagará TODOS os registros e não pode ser desfeita.")
                if st.button("Apagar TODOS os Dados"):
                    delete_all_data()
                    st.success("Banco de dados limpo com sucesso!")
                    st.rerun()

    # --- PÁGINA: ASSISTENTE IA ---
    elif page == "Assistente IA":
        st.title("🤖 Assistente de Análise (Gemini)")
        st.markdown("Faça perguntas sobre os dados. Ex: *'Qual escola tem o maior engajamento?'* ou *'Faça um resumo das formações deste mês'*.")
        
        if df_total.empty:
            st.error("Preciso de dados para analisar.")
        else:
            # Preparar resumo para a IA (evita enviar tokens demais se o banco for gigante)
            summary_stats = f"""
            Total de registros: {len(df_total)}
            Total de horas somadas: {df_total['horas'].sum()}
            Top 5 escolas: {df_total.groupby('escola')['horas'].sum().nlargest(5).to_dict()}
            Top 5 eventos: {df_total['evento'].value_counts().head(5).to_dict()}
            Média de horas por evento: {df_total['horas'].mean():.2f}
            """
            
            user_question = st.text_area("Sua pergunta:")
            
            if st.button("Perguntar"):
                with st.spinner("Analisando dados..."):
                    answer = ask_gemini(api_key, user_question, summary_stats)
                    st.markdown("### Resposta:")
                    st.write(answer)

if __name__ == "__main__":
    main()
