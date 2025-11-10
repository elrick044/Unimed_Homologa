# app.py
import os
from datetime import datetime
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "oliv10")
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
        # logue se quiser: print(str(e))
        raise HTTPException(status_code=500, detail="Erro ao salvar submissão.")


@app.get("/submissions", response_model=list[SubmissionOut])
def list_submissions(status: Optional[StatusType] = None):
    """
    Lista submissões (opcionalmente filtrando por status).
    Útil para o seu frontend com filtro de status.
    """
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
