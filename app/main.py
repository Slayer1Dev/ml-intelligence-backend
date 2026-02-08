# app/main.py
import os
from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.auth import ADMIN_EMAILS, admin_guard, clerk_auth_guard, get_clerk_config, get_current_user, is_admin

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


@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as e:
        logger.exception(f"Erro ao inicializar banco: {e}")


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
from app.database import SessionLocal, init_db
from app.models import MlToken, Subscription, User
from app.services.sheets_reader import read_sheet
from app.services.normalizer import normalize_concorrentes
from app.services.ai_agent import analyze_market, analyze_uploaded_sheet
from app.services.prompts import market_prompt
from app.services.llm_service import run_market_analysis
from app.services.sheet_processor import process_sheet
from app.services.mercado_pago_service import (
    create_checkout_url,
    handle_preapproval_created,
    handle_preapproval_updated,
    get_preapproval,
)
from app.services.ml_api import (
    exchange_code_for_tokens,
    get_auth_url,
    refresh_access_token,
    get_user_items,
    get_item_details,
    get_item_description,
    get_orders,
    get_order_details,
    get_multiple_items,
)

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
# Guards (dependências para rotas)
# ------------------------------------------------------------------
def paid_guard(user: User = Depends(get_current_user)):
    """Garante que o usuário tem plano pago ou é admin."""
    if user.plan == "active" or is_admin(user.email):
        return user
    raise HTTPException(
        status_code=403,
        detail="Recurso restrito a assinantes. Assine o plano para acessar.",
    )


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


@app.get("/api/me")
def get_me(user: User = Depends(get_current_user)):
    """Retorna dados do usuário logado (plan, email, isAdmin)."""
    return {
        "plan": user.plan,
        "email": user.email,
        "isAdmin": is_admin(user.email),
    }


@app.get("/api/debug-admin")
def debug_admin(user: User = Depends(get_current_user)):
    """Diagnóstico: por que isAdmin pode estar false. Use para conferir ADMIN_EMAILS."""
    email = user.email
    is_admin_result = is_admin(email)
    return {
        "seu_email": email,
        "isAdmin": is_admin_result,
        "admin_emails_quantidade": len(ADMIN_EMAILS),
        "dica": (
            "Seu email está vazio no sistema - verifique se o Clerk JWT envia o claim 'email'."
            if not email
            else (
                "ADMIN_EMAILS vazio no Railway." if not ADMIN_EMAILS else
                ("Email não consta em ADMIN_EMAILS. No Railway, use exatamente: " + repr(email))
                if not is_admin_result else
                "Tudo ok - você é admin."
            )
        ),
    }


@app.get("/api/ml-auth-url")
def ml_auth_url(user: User = Depends(get_current_user)):
    """Retorna URL para redirecionar o usuário ao OAuth do Mercado Livre."""
    url = get_auth_url()
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Mercado Livre não configurado. Defina ML_APP_ID, ML_SECRET e ML_REDIRECT_URI.",
        )
    return {"url": url}


class MlOAuthInput(BaseModel):
    code: str


@app.post("/api/ml-oauth-callback")
def ml_oauth_callback(data: MlOAuthInput, user: User = Depends(get_current_user)):
    """Recebe o code do OAuth e salva os tokens do Mercado Livre."""
    if not data.code or not data.code.strip():
        raise HTTPException(status_code=400, detail="Código OAuth ausente.")
    tokens = exchange_code_for_tokens(data.code.strip())
    if not tokens or "access_token" not in tokens:
        raise HTTPException(status_code=400, detail="Não foi possível obter tokens do Mercado Livre.")
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in")  # segundos
    seller_id = tokens.get("user_id")
    expires_at = None
    if expires_in:
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
    db = SessionLocal()
    try:
        existing = db.query(MlToken).filter(MlToken.user_id == user.id).first()
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.seller_id = str(seller_id) if seller_id else None
            existing.expires_at = expires_at
        else:
            db.add(MlToken(
                user_id=user.id,
                access_token=access_token,
                refresh_token=refresh_token,
                seller_id=str(seller_id) if seller_id else None,
                expires_at=expires_at,
            ))
        db.commit()
        return {"ok": True, "seller_id": seller_id}
    finally:
        db.close()


def get_valid_ml_token(user: User) -> Optional[MlToken]:
    """Retorna token válido do ML para o usuário, renovando se necessário."""
    db = SessionLocal()
    try:
        token = db.query(MlToken).filter(MlToken.user_id == user.id).first()
        if not token:
            return None
        
        # Verifica se o token expirou ou está próximo de expirar (renova com 5min de antecedência)
        from datetime import datetime, timedelta
        if token.expires_at and token.expires_at <= datetime.utcnow() + timedelta(minutes=5):
            # Token expirado ou próximo de expirar - renova
            new_tokens = refresh_access_token(token.refresh_token)
            if new_tokens and "access_token" in new_tokens:
                token.access_token = new_tokens.get("access_token", "")
                if "refresh_token" in new_tokens:
                    token.refresh_token = new_tokens.get("refresh_token", "")
                expires_in = new_tokens.get("expires_in")
                if expires_in:
                    token.expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))
                db.commit()
                logger.info(f"Token ML renovado para usuário {user.id}")
            else:
                logger.warning(f"Falha ao renovar token ML para usuário {user.id}")
                return None
        
        return token
    finally:
        db.close()


@app.get("/api/ml-status")
def ml_status(user: User = Depends(get_current_user)):
    """Retorna se o usuário tem conta ML conectada."""
    db = SessionLocal()
    try:
        token = db.query(MlToken).filter(MlToken.user_id == user.id).first()
        return {"connected": token is not None, "seller_id": token.seller_id if token else None}
    finally:
        db.close()


@app.get("/api/ml/items")
def ml_items(
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(paid_guard),
):
    """Lista anúncios do usuário conectado ao Mercado Livre."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(
            status_code=403,
            detail="Conta do Mercado Livre não conectada. Conecte sua conta primeiro.",
        )
    
    result = get_user_items(token.access_token, token.seller_id, status=status, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Erro ao buscar anúncios do Mercado Livre.",
        )
    
    # Busca detalhes dos itens se houver IDs
    items_data = []
    if result.get("results"):
        item_ids = result["results"][:20]  # Máx 20 por vez
        items_details = get_multiple_items(token.access_token, item_ids)
        if items_details:
            items_data = items_details
    
    return {
        "total": result.get("paging", {}).get("total", 0),
        "offset": result.get("paging", {}).get("offset", 0),
        "limit": result.get("paging", {}).get("limit", 50),
        "items": items_data,
        "item_ids": result.get("results", []),
    }


@app.get("/api/ml/items/{item_id}")
def ml_item_details(item_id: str, user: User = Depends(paid_guard)):
    """Busca detalhes de um anúncio específico."""
    token = get_valid_ml_token(user)
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Conta do Mercado Livre não conectada. Conecte sua conta primeiro.",
        )
    
    item = get_item_details(token.access_token, item_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Anúncio não encontrado.",
        )
    
    # Busca descrição também
    description = get_item_description(token.access_token, item_id)
    
    return {
        "item": item,
        "description": description,
    }


@app.get("/api/ml/orders")
def ml_orders(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(paid_guard),
):
    """Lista pedidos/vendas do usuário conectado ao Mercado Livre."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(
            status_code=403,
            detail="Conta do Mercado Livre não conectada. Conecte sua conta primeiro.",
        )
    
    result = get_orders(token.access_token, token.seller_id, status=status, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Erro ao buscar pedidos do Mercado Livre.",
        )
    
    return result


@app.get("/api/ml/orders/{order_id}")
def ml_order_details(order_id: str, user: User = Depends(paid_guard)):
    """Busca detalhes de um pedido específico."""
    token = get_valid_ml_token(user)
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Conta do Mercado Livre não conectada. Conecte sua conta primeiro.",
        )
    
    order = get_order_details(token.access_token, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado.",
        )
    
    return order


@app.get("/api/ml/metrics")
def ml_metrics(user: User = Depends(paid_guard)):
    """Retorna métricas gerais da conta do Mercado Livre."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(
            status_code=403,
            detail="Conta do Mercado Livre não conectada. Conecte sua conta primeiro.",
        )
    
    # Busca anúncios ativos
    active_items = get_user_items(token.access_token, token.seller_id, status="active", limit=50)
    paused_items = get_user_items(token.access_token, token.seller_id, status="paused", limit=50)
    closed_items = get_user_items(token.access_token, token.seller_id, status="closed", limit=50)
    
    # Busca pedidos pagos recentes
    paid_orders = get_orders(token.access_token, token.seller_id, status="paid", limit=50)
    
    total_active = active_items.get("paging", {}).get("total", 0) if active_items else 0
    total_paused = paused_items.get("paging", {}).get("total", 0) if paused_items else 0
    total_closed = closed_items.get("paging", {}).get("total", 0) if closed_items else 0
    total_orders = paid_orders.get("paging", {}).get("total", 0) if paid_orders else 0
    
    return {
        "items": {
            "active": total_active,
            "paused": total_paused,
            "closed": total_closed,
            "total": total_active + total_paused + total_closed,
        },
        "orders": {
            "paid": total_orders,
        },
    }


@app.post("/api/calculate-profit")
def calculate_profit_endpoint(
    data: ProfitInput,
    user: User = Depends(get_current_user),
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
    user: User = Depends(paid_guard),
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
    user: User = Depends(paid_guard),
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
def list_jobs(user: User = Depends(paid_guard)):
    """Retorna todos os jobs (id -> status)."""
    return JOB_STORE


@app.get("/jobs/{job_id}")
def get_job(job_id: str, user: User = Depends(paid_guard)):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job não encontrado")
    return job


@app.get("/api/admin/users")
def admin_users(admin_user: User = Depends(admin_guard)):
    """Lista todos os usuários (admin)."""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return [
            {
                "id": u.id,
                "email": u.email,
                "clerk_user_id": u.clerk_user_id,
                "plan": u.plan,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    finally:
        db.close()


@app.get("/api/admin/subscriptions")
def admin_subscriptions(admin_user: User = Depends(admin_guard)):
    """Lista assinaturas (admin)."""
    db = SessionLocal()
    try:
        subs = (
            db.query(Subscription)
            .join(User)
            .order_by(Subscription.created_at.desc())
            .all()
        )
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "user_email": s.user.email if s.user else None,
                "stripe_subscription_id": s.stripe_subscription_id,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ends_at": s.ends_at.isoformat() if s.ends_at else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in subs
        ]
    finally:
        db.close()


@app.post("/api/create-checkout-session")
def create_checkout(request: Request, user: User = Depends(get_current_user)):
    """Cria sessão Mercado Pago Checkout e retorna a URL para redirecionar o usuário."""
    base_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = str(request.base_url).rstrip("/")
    success_url = f"{base_url}/frontend/dashboard.html?success=1"
    cancel_url = f"{base_url}/frontend/dashboard.html?canceled=1"
    webhook_base = os.getenv("BACKEND_URL", "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    webhook_url = f"{webhook_base}/api/mercado-pago-webhook" if webhook_base else None
    url = create_checkout_url(user.clerk_user_id, success_url, cancel_url, webhook_url)
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Mercado Pago não configurado. Defina MP_ACCESS_TOKEN.",
        )
    return {"url": url}


@app.post("/api/mercado-pago-webhook")
async def mercado_pago_webhook(request: Request):
    """Recebe notificações do Mercado Pago (subscription_preapproval)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido")

    topic = body.get("type")  # subscription_preapproval, subscription_authorized_payment, etc
    if topic != "subscription_preapproval":
        return {"received": True}

    data = body.get("data", {})
    preapproval_id = data.get("id")
    if not preapproval_id:
        return {"received": True}

    preapproval = get_preapproval(preapproval_id)
    if not preapproval:
        return {"received": True}

    db = SessionLocal()
    try:
        action = body.get("action", "")
        if action in ("created", "authorized"):
            handle_preapproval_created(preapproval, db)
        else:
            handle_preapproval_updated(preapproval, db)
    finally:
        db.close()
    return {"received": True}


@app.get("/api/admin/logs")
def admin_logs(admin_user: User = Depends(admin_guard)):
    """Retorna logs do backend (admin)."""
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
