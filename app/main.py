# app/main.py
import os
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.auth import clerk_auth_guard, get_clerk_config

import logging
import uuid
from pathlib import Path
import aiofiles
from typing import Dict, Any, Optional, List
import io
import re
import pandas as pd

# ------------------------------------------------------------------
# Diretórios e logger
# ------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "backend.log"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("ml-intelligence")
logger.setLevel(logging.INFO)

# garante um handler para o arquivo de log
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(LOG_FILE) for h in logger.handlers):
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)

# ------------------------------------------------------------------
# App & CORS (auth já carrega dotenv)
# ------------------------------------------------------------------
# Em produção: defina ALLOWED_ORIGINS no Railway (ex: https://seu-app.railway.app)
_CORS_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
_CORS_LIST = [o.strip() for o in _CORS_ORIGINS.split(",") if o.strip()] if _CORS_ORIGINS != "*" else ["*"]

app = FastAPI(title="ML Intelligence Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Import dos serviços (suas funções)
# ------------------------------------------------------------------
# *Se der ImportError, colocar os módulos no PYTHONPATH ou ajustar import relativo*
from app.services.sheets_reader import read_sheet
from app.services.normalizer import normalize_concorrentes
from app.services.ai_agent import analyze_market, analyze_uploaded_sheet
from app.services.prompts import market_prompt
from app.services.llm_service import run_market_analysis
from app.services.sheet_processor import process_sheet

# ------------------------------------------------------------------
# STORE de jobs (em memória)
# ------------------------------------------------------------------
JOB_STORE: Dict[str, Dict[str, Any]] = {}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def process_job(job_id: str, file_path: str):
    """Processa a planilha em background e atualiza JOB_STORE."""
    logger.info(f"Job {job_id} - iniciando processamento do arquivo {file_path}")
    JOB_STORE[job_id]["status"] = "processing"
    try:
        records = process_sheet(file_path)
        if isinstance(records, dict) and records.get("error"):
            JOB_STORE[job_id] = {"status": "error", "error": records.get("error")}
            logger.error(f"Job {job_id} - erro no processamento: {records.get('error')}")
            return

        analysis = analyze_uploaded_sheet(records)
        JOB_STORE[job_id] = {"status": "done", "result": analysis}
        logger.info(f"Job {job_id} - finalizado com sucesso")
    except Exception as e:
        JOB_STORE[job_id] = {"status": "error", "error": str(e)}
        logger.exception(f"Job {job_id} - falhou: {e}")

# ------------------------------------------------------------------
# Schemas (Pydantic)
# ------------------------------------------------------------------
class ProfitInput(BaseModel):
    custo_produto: float
    preco_venda: float
    frete: float = 20.0
    taxa_percentual: float = 11.0
    imposto_percentual: float = 5.0


# ------------------------------------------------------------------
# Helpers - Painel financeiro
# ------------------------------------------------------------------
def _normalize_columns(columns: List[str]) -> List[str]:
    normalized = []
    for col in columns:
        col_norm = str(col).strip().lower()
        col_norm = col_norm.replace(" ", "_").replace(".", "").replace("-", "_")
        normalized.append(col_norm)
    return normalized


def _parse_percent(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None


def _parse_ml_sheet(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(file_bytes))

    # Busca coluna ITEM_ID (ou equivalente em portugues)
    item_col = None
    for c in df.columns:
        cnorm = str(c).upper().replace(" ", "").replace(".", "")
        if "ITEMID" in cnorm or "CODIGODOANUNCIO" in cnorm or "CODIGOANUNCIO" in cnorm:
            item_col = c
            break
    if item_col is None and "ITEM_ID" in df.columns:
        item_col = "ITEM_ID"
    if item_col is None:
        raise ValueError("Coluna ITEM_ID (ou Código do anúncio) não encontrada na planilha do ML.")

    # Mantem apenas linhas de anuncios reais (ITEM_ID com prefixo MLB)
    s = df[item_col].astype(str).str.strip().str.upper()
    df = df[s.str.match(r"^MLB[0-9]+", na=False)].copy()
    df["ITEM_ID"] = df[item_col]
    return df


def _parse_currency(val: Any) -> float:
    """Converte 'R$ 16,20' ou '16,20' em 16.20."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return float("nan")
    s = str(val).strip().upper().replace("R$", "").replace(" ", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return float("nan")


def _parse_costs_sheet(file_bytes: bytes, filename: str) -> Dict[str, float]:
    ext = (filename or "").lower()
    if ext.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = [s.lower() for s in xl.sheet_names]
        sheet = "custos" if "custos" in sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet)

    df = df.dropna(how="all")

    # Arquivo sem cabecalho: primeira linha vira header, gerando nomes como FR00041 e R$ 16,20
    # Usa sempre col 0 = SKU, col 1 = custo
    if len(df.columns) < 2:
        raise ValueError("Planilha de custos precisa ter ao menos 2 colunas: SKU (A) e Valor unitario (B).")

    sku_col = df.columns[0]
    cost_col = df.columns[1]

    df = df[[sku_col, cost_col]].copy()
    df[sku_col] = df[sku_col].astype(str).str.strip()
    df[cost_col] = df[cost_col].apply(_parse_currency)

    # Remove linhas com SKU vazio, "nan", ou custo invalido
    df = df[
        (df[sku_col] != "")
        & (df[sku_col].str.lower() != "nan")
        & df[cost_col].notna()
        & (df[cost_col] >= 0)
    ]

    return dict(zip(df[sku_col], df[cost_col].astype(float)))


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@app.get("/")
def root():
    """Redireciona para a landing page."""
    return RedirectResponse(url="/frontend/index.html", status_code=302)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/clerk-config")
def clerk_config():
    """Retorna publishableKey e frontendApi para o frontend inicializar o Clerk."""
    return get_clerk_config()


@app.post("/api/calculate-profit")
def calculate_profit_endpoint(
    data: ProfitInput,
    _auth=Depends(clerk_auth_guard),
):
    """Calcula lucro e margem a partir de custo, preço e despesas."""
    taxa = data.preco_venda * (data.taxa_percentual / 100)
    imposto = data.preco_venda * (data.imposto_percentual / 100)
    lucro = data.preco_venda - data.custo_produto - taxa - imposto - data.frete
    margem = (lucro / data.preco_venda) * 100 if data.preco_venda else 0
    return {
        "lucro_unitario": round(lucro, 2),
        "margem_percentual": round(margem, 2),
        "total_despesas": round(taxa + imposto + data.frete, 2),
    }


@app.post("/api/financial-dashboard")
async def financial_dashboard(
    file: UploadFile = File(...),
    costs_file: Optional[UploadFile] = File(None),
    embalagem: float = Form(1.0),
    frete: float = Form(0.0),
    _auth=Depends(clerk_auth_guard),
):
    """Gera indicadores financeiros a partir da planilha do ML e custos opcionais."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo principal inválido.")

    ml_bytes = await file.read()

    try:
        df = _parse_ml_sheet(ml_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    cost_map: Dict[str, float] = {}
    if costs_file and costs_file.filename:
        try:
            cost_bytes = await costs_file.read()
            cost_map = _parse_costs_sheet(cost_bytes, costs_file.filename)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    df["PRICE_NUM"] = pd.to_numeric(df.get("PRICE"), errors="coerce")
    df["FEE_PCT"] = df.get("FEE_PER_SALE").apply(_parse_percent)
    df["FEE_AMOUNT"] = df["PRICE_NUM"] * (df["FEE_PCT"] / 100)

    df["SKU_STR"] = df.get("SKU").astype(str).str.strip()
    df["COST"] = df["SKU_STR"].map(cost_map) if cost_map else pd.NA

    df["COST_TOTAL"] = df["COST"] + df["FEE_AMOUNT"] + embalagem + frete
    df["PROFIT"] = df["PRICE_NUM"] - df["COST_TOTAL"]
    df["MARGIN_PCT"] = (df["PROFIT"] / df["PRICE_NUM"]) * 100

    total_listings = int(len(df))
    active_listings = int(df.get("STATUS").astype(str).str.contains("Ativo", case=False, na=False).sum())
    total_stock = int(pd.to_numeric(df.get("QUANTITY"), errors="coerce").fillna(0).sum())

    avg_price = float(df["PRICE_NUM"].mean()) if total_listings else 0.0
    avg_fee_pct = float(df["FEE_PCT"].mean()) if total_listings else 0.0

    profit_mean = float(df["PROFIT"].mean()) if df["PROFIT"].notna().any() else 0.0
    margin_mean = float(df["MARGIN_PCT"].mean()) if df["MARGIN_PCT"].notna().any() else 0.0
    profit_total = float(df["PROFIT"].sum()) if df["PROFIT"].notna().any() else 0.0
    fee_total = float(df["FEE_AMOUNT"].sum()) if df["FEE_AMOUNT"].notna().any() else 0.0

    missing_cost = int(df["COST"].isna().sum())

    top_profit = (
        df[["ITEM_ID", "SKU_STR", "TITLE", "PRICE_NUM", "COST", "PROFIT", "MARGIN_PCT"]]
        .dropna(subset=["PROFIT"])
        .sort_values("PROFIT", ascending=False)
        .head(10)
        .fillna("")
        .to_dict(orient="records")
    )

    return {
        "metrics": {
            "total_listings": total_listings,
            "active_listings": active_listings,
            "total_stock": total_stock,
            "avg_price": round(avg_price, 2),
            "avg_fee_pct": round(avg_fee_pct, 2),
            "profit_mean": round(profit_mean, 2),
            "margin_mean": round(margin_mean, 2),
            "profit_total": round(profit_total, 2),
            "fee_total": round(fee_total, 2),
            "missing_cost": missing_cost,
        },
        "top_profit": top_profit,
    }


@app.get("/sheets/test")
def test_sheets():
    return read_sheet()


@app.get("/analysis/base")
def base_analysis():
    data = read_sheet()
    concorrentes = normalize_concorrentes(data.get("concorrentes", []))
    return {"produto": data.get("produto", []), "concorrentes": concorrentes}


@app.get("/analysis/market")
def market_analysis():
    data = read_sheet()
    return analyze_market(produto=data.get("produto", []), concorrentes=data.get("concorrentes", []))


@app.get("/analysis/market/ai")
def market_analysis_ai():
    data = read_sheet()
    prompt = market_prompt(produto=data.get("produto", []), concorrentes=data.get("concorrentes", []))
    return run_market_analysis(prompt)


@app.post("/upload-planilha")
async def upload_planilha(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _auth=Depends(clerk_auth_guard),
):
    """Recebe arquivo, grava temporário e dispara processamento em background (retorna job_id)."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo inválido")

    job_id = str(uuid.uuid4())
    tmp_dir = Path("tmp")
    tmp_dir.mkdir(exist_ok=True)

    # salva com prefixo do job para evitar conflito de nomes
    safe_name = f"{job_id}_{file.filename}"
    file_path = tmp_dir / safe_name

    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        logger.exception(f"Erro ao salvar arquivo: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar arquivo")

    # registra job e dispara background
    JOB_STORE[job_id] = {"status": "pending", "filename": file.filename}
    background_tasks.add_task(process_job, job_id, str(file_path))

    logger.info(f"Job {job_id} enfileirado para {file.filename} ({file_path})")
    return JSONResponse({"job_id": job_id, "status": "pending"})


@app.get("/jobs")
def list_jobs(_auth=Depends(clerk_auth_guard)):
    """Retorna todos os jobs (id -> status)."""
    return JOB_STORE


@app.get("/jobs/{job_id}")
def get_job(job_id: str, _auth=Depends(clerk_auth_guard)):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job não encontrado")
    return job


@app.get("/logs")
def get_logs():
    if not LOG_FILE.exists():
        return PlainTextResponse("Arquivo de log ainda não criado.")
    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.exception(f"Erro ao ler log: {e}")
        return PlainTextResponse(f"Erro ao ler logs: {e}")
    return PlainTextResponse(text, media_type="text/plain")

# ------------------------------------------------------------------
# Frontend estático (caminho absoluto para funcionar de qualquer pasta)
# ------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
