import os
import glob
import datetime
import pandas as pd
import streamlit as st

# 1. Page Configuration & Title
st.set_page_config(
    page_title="Painel de Carros em Progresso",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling for premium interface
st.markdown("""
<style>
    /* Main layout fonts and background */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Metrics panel card styling */
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Header Styling */
    .main-title {
        font-weight: 700;
        font-size: 2.2rem;
        background: linear-gradient(135deg, #FF4B4B 0%, #FF8533 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    
    .subtitle {
        color: #808495;
        font-size: 1rem;
        margin-bottom: 25px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Main File Path & Directory Scan Section
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_excel_file(folder_path):
    if not os.path.exists(folder_path):
        return None
    # Search for .xls and .xlsx files
    xls_files = glob.glob(os.path.join(folder_path, "*.xls"))
    xlsx_files = glob.glob(os.path.join(folder_path, "*.xlsx"))
    files = xls_files + xlsx_files
    if not files:
        return None
    # Sort files by modification time (most recent first)
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

latest_file = get_latest_excel_file(DATA_DIR)

# Show error if no file is found
if latest_file is None:
    st.markdown('<div class="main-title">Painel de Carros em Progresso 🚗</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Consulta de estoque e classificação de origem de veículos</div>', unsafe_allow_html=True)
    
    st.error(f"⚠️ **Nenhum arquivo Excel encontrado!** Certifique-se de colocar arquivos `.xls` ou `.xlsx` na pasta do projeto: `{DATA_DIR}`")
    st.stop()

# Get file info for the sidebar
file_name = os.path.basename(latest_file)
file_mtime = os.path.getmtime(latest_file)
mtime_str = datetime.datetime.fromtimestamp(file_mtime).strftime('%d/%m/%Y %H:%M:%S')

# Show file info in Sidebar
st.sidebar.markdown("### 📁 Arquivo de Estoque")
st.sidebar.info(
    f"**Arquivo Carregado:**\n`{file_name}`\n\n"
    f"**Última Modificação:**\n`{mtime_str}`"
)

# Load data with caching (caching key includes path and mtime to detect updates)
@st.cache_data
def load_and_prepare_data(filepath, mtime):
    # Read the file using pandas
    df = pd.read_excel(filepath)
    
    # Standardize column headers by stripping whitespace
    df.columns = df.columns.astype(str).str.strip()
    
    # Required columns mapping validation
    required_base = ['Modelo', 'Chassi', 'Ano', 'Cor']
    for col in required_base:
        if col not in df.columns:
            st.error(f"A planilha Excel está sem a coluna obrigatória: **{col}**")
            st.stop()
            
    # Resolve the 'Status' column from 'Situação', 'Estoque' or fallback
    status_col_name = None
    if 'Status' in df.columns:
        status_col_name = 'Status'
    else:
        # Handle unicode variations or common synonyms in the excel sheet
        for possible_col in ['Situação', 'Situaçao', 'Situao', 'Estoque']:
            if possible_col in df.columns:
                # Use it if it has at least some non-null values
                if df[possible_col].count() > 0 or not status_col_name:
                    status_col_name = possible_col
                    
    if status_col_name:
        df['Status'] = df[status_col_name].fillna('N/A').astype(str).str.strip()
    else:
        df['Status'] = 'N/A'
        
    # 3. Apply Business Rules:
    # Check if 'Chassi' (ends with 'm65' ignoring case)
    df['Chassi'] = df['Chassi'].fillna('').astype(str).str.strip()
    df['Origem'] = df['Chassi'].apply(
        lambda x: 'Próprio' if x.lower().endswith('m65') else 'Extra'
    )
    
    # Select only the required columns to show in order
    display_cols = ['Modelo', 'Chassi', 'Ano', 'Cor', 'Status', 'Origem']
    return df[display_cols]

# Load file
try:
    df_raw = load_and_prepare_data(latest_file, file_mtime)
except Exception as e:
    st.error(f"Erro ao ler o arquivo Excel '{latest_file}': {str(e)}")
    st.stop()

# 4. Sidebar Filters Section
st.sidebar.markdown("### 🔍 Filtros de Consulta")

# Helper function to get filter options with 'Todos' as default
def get_options(series):
    return ['Todos'] + sorted(list(series.dropna().unique()))

# Initialize session state keys for interactive filters if not set
for key, val in [('origem', 'Todos'), ('status', 'Todos'), ('modelo', 'Todos'), ('ano', 'Todos'), ('cor', 'Todos'), ('search', '')]:
    if key not in st.session_state:
        st.session_state[key] = val

# Filter Inputs
filter_origem = st.sidebar.selectbox("Origem", ['Todos', 'Próprio', 'Extra'], key='origem')
filter_status = st.sidebar.selectbox("Status", get_options(df_raw['Status']), key='status')
filter_modelo = st.sidebar.selectbox("Modelo", get_options(df_raw['Modelo']), key='modelo')
filter_ano = st.sidebar.selectbox("Ano", get_options(df_raw['Ano'].astype(str)), key='ano')
filter_cor = st.sidebar.selectbox("Cor", get_options(df_raw['Cor']), key='cor')

# Reset Button Function
def reset_filters():
    st.session_state.origem = 'Todos'
    st.session_state.status = 'Todos'
    st.session_state.modelo = 'Todos'
    st.session_state.ano = 'Todos'
    st.session_state.cor = 'Todos'
    st.session_state.search = ''

if st.sidebar.button("Limpar Filtros", width='stretch', on_click=reset_filters):
    st.rerun()

# Apply Filters
df_filtered = df_raw.copy()

if filter_origem != 'Todos':
    df_filtered = df_filtered[df_filtered['Origem'] == filter_origem]

if filter_status != 'Todos':
    df_filtered = df_filtered[df_filtered['Status'] == filter_status]

if filter_modelo != 'Todos':
    df_filtered = df_filtered[df_filtered['Modelo'] == filter_modelo]

if filter_ano != 'Todos':
    df_filtered = df_filtered[df_filtered['Ano'].astype(str) == filter_ano]

if filter_cor != 'Todos':
    df_filtered = df_filtered[df_filtered['Cor'] == filter_cor]

# Main Dashboard Content
st.markdown('<div class="main-title">Painel de Carros em Progresso 🚗</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Consulta de estoque e classificação de origem de veículos</div>', unsafe_allow_html=True)

# Search input
search_query = st.text_input("🔍 Busca Rápida (Modelo ou Chassi):", placeholder="Digite o modelo ou chassi para buscar...", key='search')
if search_query:
    df_filtered = df_filtered[
        df_filtered['Modelo'].str.contains(search_query, case=False, na=False) |
        df_filtered['Chassi'].str.contains(search_query, case=False, na=False)
    ]

# 5. Indicators (st.columns and st.metric)
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric(
        label="Total de Veículos",
        value=len(df_filtered),
        help="Quantidade de carros que atendem aos filtros ativos"
    )

with col_m2:
    proprio_count = len(df_filtered[df_filtered['Origem'] == 'Próprio'])
    proprio_pct = (proprio_count / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric(
        label="Veículos Próprios",
        value=proprio_count,
        delta=f"{proprio_pct:.1f}%" if len(df_filtered) > 0 else "0.0%"
    )

with col_m3:
    extra_count = len(df_filtered[df_filtered['Origem'] == 'Extra'])
    extra_pct = (extra_count / len(df_filtered) * 100) if len(df_filtered) > 0 else 0
    st.metric(
        label="Veículos Extra",
        value=extra_count,
        delta=f"{extra_pct:.1f}%" if len(df_filtered) > 0 else "0.0%",
        delta_color="inverse"
    )

st.write("")

# 6. Main Data Table with pandas styling
st.markdown("### 📊 Progresso de Veículos")

def highlight_extra_rows(row):
    # Subtly color rows where Origem is 'Extra'
    # Soft background red/grey color for clean visualization
    if row['Origem'] == 'Extra':
        return ['background-color: rgba(255, 75, 75, 0.12); font-weight: 500;'] * len(row)
    return [''] * len(row)

if not df_filtered.empty:
    styled_df = df_filtered.style.apply(highlight_extra_rows, axis=1)
    
    st.dataframe(
        styled_df,
        width='stretch',
        hide_index=True,
        column_config={
            "Modelo": st.column_config.TextColumn("Modelo", help="Modelo do veículo"),
            "Chassi": st.column_config.TextColumn("Pedido (Chassi)", help="Número do pedido / Chassi do veículo"),
            "Ano": st.column_config.TextColumn("Ano", help="Ano de fabricação/modelo"),
            "Cor": st.column_config.TextColumn("Cor", help="Cor do veículo"),
            "Status": st.column_config.TextColumn("Status", help="Situação/Estoque do veículo"),
            "Origem": st.column_config.TextColumn("Origem", help="Origem do veículo (Próprio ou Extra)")
        }
    )
    
    # Download actions
    col_dl1, col_dl2 = st.columns([8, 2])
    with col_dl2:
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar para CSV",
            data=csv,
            file_name='estoque_rel_filtrado.csv',
            mime='text/csv',
            width='stretch'
        )
else:
    st.warning("⚠️ Nenhum veículo corresponde aos filtros selecionados. Altere suas opções na barra lateral.")
