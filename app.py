import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import os
import time

# --- Configuração Inicial ---
st.set_page_config(
    page_title="Portal Formação SMED",
    page_icon="🎓",
    layout="wide"
)

# --- CSS para Interface Moderna e Minimalista ---
st.markdown("""
    <style>
    .main {
        background-color: #f9fafb; /* Fundo levemente cinza */
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #1e3a8a; /* Azul escuro corporativo */
    }
    h1, h2, h3 {
        color: #1f2937;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #fff;
        border-radius: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff;
        color: #1d4ed8;
        border-bottom: 2px solid #1d4ed8;
    }
    </style>
""", unsafe_allow_html=True)

# --- Gerenciamento de Banco de Dados ---
def init_db():
    conn = sqlite3.connect('smed_data.db')
    c = conn.cursor()
    # Adicionada coluna 'categoria' para classificação via IA
    c.execute('''
        CREATE TABLE IF NOT EXISTS formacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            escola TEXT,
            evento TEXT,
            categoria TEXT,
            horas REAL,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_batch(data_list):
    conn = sqlite3.connect('smed_data.db')
    c = conn.cursor()
    c.executemany('''
        INSERT INTO formacoes (nome, escola, evento, categoria, horas)
        VALUES (?, ?, ?, ?, ?)
    ''', data_list)
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect('smed_data.db')
    try:
        df = pd.read_sql("SELECT * FROM formacoes", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def clear_db():
    conn = sqlite3.connect('smed_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM formacoes")
    conn.commit()
    conn.close()

# --- IA Generativa (Classificação Automática) ---
def classify_event_with_ai(event_name):
    """Usa o Gemini para categorizar o evento baseado no nome."""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        return "Geral" # Fallback se sem chave

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
        Classifique o evento de formação de professores "{event_name}" em APENAS UMA das seguintes categorias:
        - Tecnologia
        - Pedagógica
        - Administrativa
        - Inclusão
        - Linguagens
        - Outros
        
        Responda apenas com a palavra da categoria.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Geral"

# --- Interface Principal ---
def main():
    init_db()
    
    # Cabeçalho Limpo
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        # Placeholder de logo simples
        st.markdown("### 🎓 SMED") 
    with col_title:
        st.title("Portal de Formação Continuada")
        st.markdown("Gestão inteligente de horas e indicadores.")

    # Navegação por Abas (Mais limpo)
    tab_dash, tab_upload, tab_reports, tab_config = st.tabs([
        "📊 Dashboard Geral", 
        "📂 Novo Registro (Upload)", 
        "📑 Relatórios Dinâmicos",
        "⚙️ Configurações"
    ])

    df = load_data()

    # --- ABA 1: DASHBOARD ---
    with tab_dash:
        if df.empty:
            st.info("👋 Bem-vindo! O sistema está vazio. Vá para a aba 'Novo Registro' para começar.")
        else:
            # Métricas Topo
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total de Horas", f"{df['horas'].sum():.0f}h")
            m2.metric("Professores", df['nome'].nunique())
            m3.metric("Escolas", df['escola'].nunique())
            m4.metric("Eventos", df['evento'].nunique())
            
            st.markdown("---")
            
            # Gráficos Lado a Lado
            g1, g2 = st.columns(2)
            
            with g1:
                st.subheader("Distribuição por Categoria (IA)")
                # Gráfico de rosca simples usando Streamlit nativo ou Altair
                if 'categoria' in df.columns:
                    cat_counts = df['categoria'].value_counts()
                    st.bar_chart(cat_counts, color="#1e3a8a")
                else:
                    st.warning("Dados de categoria não disponíveis.")

            with g2:
                st.subheader("Top 5 Escolas com Mais Horas")
                top_schools = df.groupby('escola')['horas'].sum().sort_values(ascending=False).head(5)
                st.bar_chart(top_schools, color="#3b82f6")

    # --- ABA 2: UPLOAD INTELIGENTE ---
    with tab_upload:
        st.markdown("#### 1. Detalhes do Evento")
        
        with st.container(border=True):
            col_evt, col_date = st.columns([3, 1])
            event_name = col_evt.text_input("Nome do Evento de Formação", placeholder="Ex: Curso de Alfabetização Digital")
            event_hours = col_date.number_input("Carga Horária (por participante)", min_value=1.0, step=0.5, value=4.0)
            
            st.info("💡 A Inteligência Artificial irá classificar este evento automaticamente ao salvar.")

        st.markdown("#### 2. Lista de Presença")
        uploaded_file = st.file_uploader("Carregar planilha (Excel)", type=['xlsx', 'xls'], label_visibility="collapsed")

        if uploaded_file and event_name:
            try:
                df_upload = pd.read_excel(uploaded_file)
                st.success("Planilha carregada!")
                
                with st.expander("👀 Visualizar e Mapear Colunas", expanded=True):
                    st.dataframe(df_upload.head(3), use_container_width=True)
                    
                    st.markdown("**Selecione as colunas correspondentes na sua planilha:**")
                    c1, c2 = st.columns(2)
                    col_nome_map = c1.selectbox("Coluna com Nome do Professor", df_upload.columns)
                    col_escola_map = c2.selectbox("Coluna com Nome da Escola", df_upload.columns)
                
                if st.button("🚀 Processar e Salvar Dados", type="primary"):
                    with st.status("Processando...", expanded=True) as status:
                        st.write("🔍 Analisando evento com IA...")
                        ai_category = classify_event_with_ai(event_name)
                        st.write(f"✅ Evento classificado como: **{ai_category}**")
                        
                        st.write("💾 Formatando dados...")
                        # Preparar lista de tuplas para inserção eficiente
                        data_to_insert = []
                        for _, row in df_upload.iterrows():
                            # Tratamento básico de nulos
                            nome = str(row[col_nome_map]).strip()
                            escola = str(row[col_escola_map]).strip()
                            
                            if nome and escola and nome.lower() != 'nan':
                                data_to_insert.append((
                                    nome, 
                                    escola, 
                                    event_name, 
                                    ai_category, 
                                    float(event_hours)
                                ))
                        
                        if data_to_insert:
                            save_batch(data_to_insert)
                            status.update(label="Concluído!", state="complete", expanded=False)
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Nenhum dado válido encontrado nas colunas selecionadas.")
                            
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
        elif uploaded_file and not event_name:
            st.warning("⚠️ Por favor, preencha o Nome do Evento antes de processar.")

    # --- ABA 3: RELATÓRIOS DINÂMICOS ---
    with tab_reports:
        if df.empty:
            st.warning("Sem dados para gerar relatórios.")
        else:
            st.markdown("#### 🔍 Explorador de Dados")
            
            # Filtros Inteligentes
            c_filter1, c_filter2 = st.columns(2)
            group_by_col = c_filter1.selectbox("Agrupar dados por:", ["escola", "nome", "categoria", "evento"], format_func=lambda x: x.capitalize())
            
            # Tabela Dinâmica
            pivot_df = df.groupby(group_by_col)['horas'].sum().reset_index().sort_values('horas', ascending=False)
            pivot_df.columns = [group_by_col.capitalize(), "Total de Horas"]
            
            st.dataframe(
                pivot_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Total de Horas": st.column_config.ProgressColumn(
                        "Total de Horas",
                        format="%.1f h",
                        min_value=0,
                        max_value=float(pivot_df["Total de Horas"].max()),
                    )
                }
            )
            
            # Exportação
            csv = pivot_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Baixar Relatório (CSV)",
                data=csv,
                file_name=f"relatorio_por_{group_by_col}.csv",
                mime="text/csv"
            )

    # --- ABA 4: CONFIGURAÇÕES ---
    with tab_config:
        st.markdown("### Zona de Perigo")
        st.warning("Ações aqui são irreversíveis.")
        
        if st.button("🗑️ Limpar TODO o Banco de Dados"):
            clear_db()
            st.success("Banco de dados resetado.")
            time.sleep(1)
            st.rerun()

if __name__ == "__main__":
    main()
