# app.py — Dashboard com atualização de status + FILTRO POR STATUS EXISTENTES
import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="Unimed Dashboard", page_icon="📊", layout="wide")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "260405")
DB_NAME = os.getenv("DB_NAME", "unimed")
TABLE_NAME = os.getenv("TABLE_NAME", "submissions")

ALLOWED_STATUS = ["Em análise", "Aprovado", "Reprovado"]

@st.cache_resource(show_spinner=False)
def get_engine() -> Engine:
    return create_engine(
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4",
        pool_pre_ping=True
    )

# NOVO: lista de status que existem na tabela
@st.cache_data(ttl=120, show_spinner=False)
def get_distinct_statuses():
    with get_engine().connect() as con:
        rs = con.execute(text(f"SELECT DISTINCT status FROM {TABLE_NAME} WHERE status IS NOT NULL ORDER BY status"))
        return [r[0] for r in rs if r[0] is not None]

# get_data agora aceita filtro
@st.cache_data(ttl=60, show_spinner=False)
def get_data(filter_statuses: list[str] | None = None):
    base_sql = f"SELECT id, protocolo, razao_social, cnpj, status FROM {TABLE_NAME}"
    params = {}
    if filter_statuses:
        ph = ", ".join([f":s{i}" for i, _ in enumerate(filter_statuses)])
        base_sql += f" WHERE status IN ({ph})"
        params.update({f"s{i}": s for i, s in enumerate(filter_statuses)})
    base_sql += " ORDER BY id DESC"

    with get_engine().connect() as con:
        df = pd.read_sql(text(base_sql), con, params=params)

    if not df.empty:
        df.insert(0, "Selecionar", False)
    return df

def update_status(ids, new_status: str):
    if not ids:
        return 0
    placeholders = ", ".join([f":id{i}" for i, _ in enumerate(ids)])
    params = {f"id{i}": int(v) for i, v in enumerate(ids)}
    params["new_status"] = new_status
    with get_engine().begin() as con:
        result = con.execute(
            text(f"UPDATE {TABLE_NAME} SET status = :new_status WHERE id IN ({placeholders})"),
            params
        )
        return result.rowcount

def refresh_cache():
    get_data.clear()
    get_distinct_statuses.clear()

# ---------------- UI ----------------
st.image("unimedlog.jpg", width=100)
st.title("Dashboard de Homologações")

st.divider()

# FILTRO POR STATUS EXISTENTES
existing_statuses = get_distinct_statuses()
if not existing_statuses:
    st.info("Não há status cadastrados ainda. Exibindo todos os registros.")
selected_statuses = st.multiselect(
    "Filtrar por status",
    options=existing_statuses or ALLOWED_STATUS,
    default=existing_statuses or ALLOWED_STATUS,
    placeholder="Selecione um ou mais status"
)

df = get_data(selected_statuses)

if df.empty:
    st.warning("Nenhum registro para o filtro atual.")
    st.stop()

# Métricas
c1, c2, c3 = st.columns(3)
c1.metric("Total", len(df))
c2.metric("Aprovados", len(df[df["status"] == "Aprovado"]))
c3.metric("Em análise", len(df[df["status"] == "Em análise"]))

st.subheader("Registros")

edited = st.data_editor(
    df,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    column_config={
        "Selecionar": st.column_config.CheckboxColumn(help="Marque para atualizar o status."),
        "status": st.column_config.TextColumn(disabled=True),
        "id": st.column_config.NumberColumn(disabled=True),
        "protocolo": st.column_config.TextColumn(disabled=True),
        "razao_social": st.column_config.TextColumn(disabled=True),
        "cnpj": st.column_config.TextColumn(disabled=True),
        "setor": st.column_config.TextColumn(disabled=True),
    },
    key="editor",
)

selected_ids = edited.loc[edited["Selecionar"] == True, "id"].tolist()
st.caption(f"{len(selected_ids)} registro(s) selecionado(s).")

col1, col2 = st.columns([1, 3])
with col1:
    new_status = st.selectbox("Novo status", ALLOWED_STATUS, index=0)
with col2:
    st.write("")
    apply_btn = st.button("✅ Aplicar aos selecionados", disabled=len(selected_ids) == 0)

if apply_btn:
    changed = update_status(selected_ids, new_status)
    refresh_cache()
    st.success(f"Status alterado para **{new_status}** em {changed} registro(s).")
    st.rerun()
