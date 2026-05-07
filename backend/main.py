# app.py
import os
import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 1. CONFIGURAÇÃO DO LOGGING
# Define o formato de como os logs vão aparecer no seu terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "260405")
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_DB = os.getenv("MYSQL_DB", "unimed")

ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()
]

DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    "?charset=utf8mb4"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# 2. TESTE DE CONEXÃO AO INICIAR (EARLY FAIL)
# Verifica se o banco está respondendo no momento em que a aplicação sobe
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        logging.info("✅ Conexão com o banco de dados estabelecida com sucesso!")
except Exception as e:
    logging.critical(f"❌ FALHA CRÍTICA: Não foi possível conectar ao banco de dados. Erro original: {e}")

app = FastAPI(title="Credenciamento API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- MODELOS ----------
StatusType = Literal["Em análise", "Aprovado", "Reprovado"]

class SubmissionIn(BaseModel):
    razao_social: constr(strip_whitespace=True, min_length=2)
    cnpj: constr(strip_whitespace=True, min_length=14, max_length=18)
    status: Optional[StatusType] = "Em análise"  # default

class SubmissionOut(BaseModel):
    id: int
    protocolo: str
    razao_social: str
    cnpj: str
    status: StatusType


# --------- ENDPOINTS ----------
@app.post("/submit", response_model=SubmissionOut)
def create_submission(data: SubmissionIn):
    """
    Cria a submissão, gera PROT-YYYYMMDD-######, salva no banco e devolve o protocolo.
    """
    try:
        with engine.begin() as conn:
            # 1) cria o registro sem protocolo, usa status validado pelo Pydantic
            result = conn.execute(
                text("""
                    INSERT INTO submissions (razao_social, cnpj, status)
                    VALUES (:razao_social, :cnpj, :status)
                """),
                {"razao_social": data.razao_social, "cnpj": data.cnpj, "status": data.status},
            )
            new_id = result.lastrowid

            # 2) gera protocolo e atualiza
            protocolo = f"PROT-{datetime.utcnow():%Y%m%d}-{new_id:06d}"
            conn.execute(
                text("UPDATE submissions SET protocolo = :p WHERE id = :id"),
                {"p": protocolo, "id": new_id},
            )

            # 3) retorna payload ao front
            row = conn.execute(
                text("SELECT id, protocolo, razao_social, cnpj, status FROM submissions WHERE id=:id"),
                {"id": new_id},
            ).mappings().one()

        return SubmissionOut(**row)
    except SQLAlchemyError as e:
        # 3. LOGGING DO ERRO DE INSERT (Fim do erro silencioso)
        logging.error(f"Erro ao salvar submissão no banco de dados. Detalhes técnicos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao salvar submissão. Verifique os logs do servidor.")


@app.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(status: Optional[StatusType] = None):
    """
    Lista submissões (opcionalmente filtrando por status).
    Útil para o seu frontend com filtro de status.
    """
    try:
        with engine.begin() as conn:
            if status:
                rs = conn.execute(
                    text("SELECT id, protocolo, razao_social, cnpj, status FROM submissions WHERE status=:s ORDER BY id DESC"),
                    {"s": status},
                )
            else:
                rs = conn.execute(
                    text("SELECT id, protocolo, razao_social, cnpj, status FROM submissions ORDER BY id DESC")
                )
            return [SubmissionOut(**row) for row in rs.mappings().all()]
    except SQLAlchemyError as e:
        # 4. LOGGING DO ERRO DE SELECT
        logging.error(f"Erro ao consultar submissões no banco de dados. Detalhes técnicos: {e}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar submissões. Verifique os logs.")