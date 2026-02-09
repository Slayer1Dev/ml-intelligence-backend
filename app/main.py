# app/main.py
import os
from fastapi import FastAPI, Request, UploadFile, File, BackgroundTasks, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.auth import admin_guard, clerk_auth_guard, get_admin_emails, get_clerk_config, get_current_user, is_admin

import hashlib
import hmac
import json
import logging
import time
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
DEBUG_LOG = Path(__file__).resolve().parent.parent / ".cursor" / "debug.log"

def _debug_log(message: str, data: dict, hypothesis_id: str = ""):
    try:
        DEBUG_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {"timestamp": time.time(), "location": "main.py", "message": message, "data": data}
        if hypothesis_id:
            entry["hypothesisId"] = hypothesis_id
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

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


@app.exception_handler(Exception)
async def _debug_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    _debug_log("backend_exception", {"path": str(request.url.path), "error": str(exc), "type": type(exc).__name__}, "H4")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


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
from app.models import AuditLog, CompetitorItem, ItemCost, MlToken, PendingQuestion, QuestionAnswerFeedback, Subscription, User
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
    get_question_detail,
    get_questions_search,
    get_item_by_id,
    post_answer,
    search_public,
)

# ------------------------------------------------------------------
# STORE de jobs (em memória)
# ------------------------------------------------------------------
JOB_STORE: Dict[str, Dict[str, Any]] = {}
JOB_STORE_MAX_SIZE = 500


def _trim_job_store(max_size: int = JOB_STORE_MAX_SIZE) -> None:
    """Mantém apenas os últimos max_size jobs (FIFO) para evitar crescimento ilimitado."""
    if len(JOB_STORE) < max_size:
        return
    keys = sorted(JOB_STORE.keys(), key=lambda k: JOB_STORE.get(k, {}).get("_created", 0) or 0)
    for k in keys[: len(JOB_STORE) - max_size]:
        JOB_STORE.pop(k, None)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def process_job(job_id: str, file_path: str, user_id: Optional[int] = None):
    """Processa a planilha em background e atualiza JOB_STORE."""
    logger.info(f"Job {job_id} - iniciando processamento do arquivo {file_path}")
    JOB_STORE[job_id]["status"] = "processing"
    try:
        records = process_sheet(file_path)
        if isinstance(records, dict) and records.get("error"):
            prev = JOB_STORE.get(job_id, {})
            JOB_STORE[job_id] = {"status": "error", "error": records.get("error"), "_created": prev.get("_created", time.time())}
            logger.error(f"Job {job_id} - erro no processamento: {records.get('error')}")
            return

        records_list = records.get("records", []) if isinstance(records, dict) else []
        analysis = analyze_uploaded_sheet(records_list, user_id=user_id)
        prev = JOB_STORE.get(job_id, {})
        JOB_STORE[job_id] = {"status": "done", "result": analysis, "_created": prev.get("_created", time.time())}
        logger.info(f"Job {job_id} - finalizado com sucesso")
    except Exception as e:
        err_msg = str(e)
        if "KeyError" in type(e).__name__ or "TypeError" in type(e).__name__:
            user_msg = "Erro ao processar dados da planilha. Verifique se as colunas sku, custo_produto e preco_venda existem."
        else:
            user_msg = err_msg
        prev = JOB_STORE.get(job_id, {})
        JOB_STORE[job_id] = {"status": "error", "error": user_msg, "_created": prev.get("_created", time.time())}
        logger.exception(f"Job {job_id} - falhou: {e}")
    finally:
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception as ex:
            logger.warning("Falha ao remover arquivo temporário %s: %s", file_path, ex)

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


class ItemCostUpdate(BaseModel):
    item_id: str
    sku: Optional[str] = None
    custo_produto: Optional[float] = None
    embalagem: Optional[float] = None
    frete: Optional[float] = None
    taxa_pct: Optional[float] = None
    imposto_pct: Optional[float] = None


class ItemCostsBatch(BaseModel):
    items: List[ItemCostUpdate]


class IAPerguntaInput(BaseModel):
    pergunta: str


class IARespostaClienteInput(BaseModel):
    tipo: str  # pedido_atrasado | duvida_produto | reclamacao | agradecimento | orcamento | outro
    contexto: Optional[str] = None
    mensagem_cliente: Optional[str] = None


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


def _is_subscription_plan(item: dict) -> bool:
    """Identifica anúncios que são planos de assinatura (não produtos)."""
    title = (item.get("title") or "").lower()
    exclude = ("plano pro", "plano mensal", "assinatura", "plano anual")
    return any(x in title for x in exclude)


def _find_col(df: pd.DataFrame, *aliases: str) -> Optional[str]:
    """Encontra coluna por alias (case-insensitive, sem acentos)."""
    cols_lower = {str(c).lower().replace("á", "a").replace("ã", "a").replace("ç", "c"): c for c in df.columns}
    for a in aliases:
        key = a.lower().replace(" ", "").replace(".", "")
        for k, v in cols_lower.items():
            if key in k.replace(" ", "").replace(".", ""):
                return v
    return None


def _parse_analise_anuncios(file_bytes: bytes) -> List[Dict[str, Any]]:
    """Parse planilha ANALISE ANUNCIOS (formato CONTA 1 ML, CONTA 2 ML). Retorna lista de anúncios com análise."""
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    sheets_ml = [s for s in xl.sheet_names if "ML" in s.upper() and "SHOPEE" not in s.upper()]
    if not sheets_ml:
        raise ValueError("Planilha deve ter abas CONTA 1 ML ou CONTA 2 ML.")
    rows = []
    for sheet in sheets_ml:
        df = xl.parse(sheet)
        df = df.dropna(how="all")
        if df.empty:
            continue
        sku_col = _find_col(df, "COD. DO PROD.", "SKU", "COD DO PROD") or df.columns[0]
        desc_col = _find_col(df, "Descrição", "DESCRIÇÃO", "Descricao") or df.columns[1]
        custo_col = _find_col(df, "Valor Unit.", "VALOR UNIT", "Custo")
        precmed_col = _find_col(df, "Preço de venda médio", "PREÇO MÉDIO", "PRECO MEDIO")
        margem_col = _find_col(df, "Margem Atual", "MARGEM ATUAL")  # deve vir antes de atual
        lucro_col = _find_col(df, "LUCRO EM R$", "LUCRO")
        preco_min_col = _find_col(df, "PREÇO MAIS BARATO", "PRECO MAIS BARATO")
        preco_max_col = _find_col(df, "PREÇO MAIS CARO", "PRECO MAIS CARO")
        # ATUAL = preço atual (não confundir com Margem Atual)
        atual_col = None
        for c in df.columns:
            cn = str(c).strip().upper().replace("Á", "A").replace("Ã", "A")
            if "MARGEM" in cn:
                continue
            if cn == "ATUAL" or cn == "VALOR ATUAL" or cn.replace(" ", "") == "VALORATUAL":
                atual_col = c
                break
        mais_vendido_col = _find_col(df, "Valor do mais vendido", "VALOR DO MAIS VENDIDO")
        vendas_mes_col = _find_col(df, "VENDAS NO MÊS", "VENDAS NO MES")
        obs_col = _find_col(df, "OBS", "OBS.")
        acoes_col = _find_col(df, "AÇÕES PROPOSTAS", "ACOES PROPOSTAS")
        atencao_col = _find_col(df, "ATENÇÃO", "ATENCAO")
        for _, r in df.iterrows():
            sku = str(r.get(sku_col, "")).strip()
            if not sku or sku.lower() == "nan":
                continue
            desc = str(r.get(desc_col, "")).strip()[:100] if desc_col and desc_col in r else ""
            custo = _parse_currency(r.get(custo_col)) if custo_col and custo_col in r else None
            precmed = _parse_currency(r.get(precmed_col)) if precmed_col and precmed_col in r else None
            margem_raw = r.get(margem_col) if margem_col and margem_col in r else None
            margem = None
            if margem_raw is not None and not (isinstance(margem_raw, float) and pd.isna(margem_raw)):
                try:
                    v = float(str(margem_raw).replace(",", "."))
                    margem = v if v > 1 else v * 100  # se < 1 assume ratio (0.12 -> 12%)
                except Exception:
                    pass
            lucro = _parse_currency(r.get(lucro_col)) if lucro_col and lucro_col in r else None
            preco_min = _parse_currency(r.get(preco_min_col)) if preco_min_col and preco_min_col in r else None
            preco_max = _parse_currency(r.get(preco_max_col)) if preco_max_col and preco_max_col in r else None
            atual = _parse_currency(r.get(atual_col)) if atual_col and atual_col in r else None
            mais_vendido = str(r.get(mais_vendido_col, "")).strip() if mais_vendido_col and mais_vendido_col in r else None
            vendas_mes = str(r.get(vendas_mes_col, "")).strip() if vendas_mes_col and vendas_mes_col in r else None
            obs = str(r.get(obs_col, "")).strip() if obs_col and obs_col in r else None
            acoes = str(r.get(acoes_col, "")).strip() if acoes_col and acoes_col in r else None
            atencao = str(r.get(atencao_col, "")).strip() if atencao_col and atencao_col in r else None
            rows.append({
                "sku": sku,
                "descricao": desc,
                "custo": custo if custo is not None and not pd.isna(custo) else None,
                "preco_medio": precmed if precmed is not None and not pd.isna(precmed) else None,
                "margem_pct": round(margem, 2) if margem is not None else None,
                "lucro": lucro if lucro is not None and not pd.isna(lucro) else None,
                "preco_mais_barato": preco_min if preco_min is not None and not pd.isna(preco_min) else None,
                "preco_mais_caro": preco_max if preco_max is not None and not pd.isna(preco_max) else None,
                "preco_atual": atual if atual is not None and not pd.isna(atual) else None,
                "valor_mais_vendido": mais_vendido,
                "vendas_mes": vendas_mes,
                "obs": obs,
                "acoes_propostas": acoes,
                "atencao": atencao,
                "conta": sheet,
            })
    return rows


def _parse_costs_sheet(file_bytes: bytes, filename: str) -> Dict[str, float]:
    """Detecta CSV vs Excel pelo conteúdo (magic bytes) ou pela extensão do nome."""
    is_excel = filename and (filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls"))
    if not is_excel and len(file_bytes) >= 4:
        if file_bytes[:2] == b"PK" or file_bytes[:4] == b"\xd0\xcf\x11\xe0":
            is_excel = True
    if not is_excel:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
            if len(df.columns) >= 2:
                pass
            else:
                is_excel = True
        except Exception:
            is_excel = True
    if is_excel:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheet_names = [s.lower() for s in xl.sheet_names]
        sheet = "custos" if "custos" in sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet)
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))

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
    # #region agent log
    _debug_log("api_clerk_config_entry", {}, "H1")
    # #endregion
    return get_clerk_config()


@app.get("/api/me")
def get_me(user: User = Depends(get_current_user)):
    """Retorna dados do usuário logado (plan, email, isAdmin, telegramLinked)."""
    # #region agent log
    _debug_log("api_me_ok", {"user_id": user.id, "email": (user.email or "")[:20], "isAdmin": is_admin(user.email)}, "H3")
    # #endregion
    return {
        "plan": user.plan,
        "email": user.email,
        "isAdmin": is_admin(user.email),
        "telegramLinked": bool(getattr(user, "telegram_chat_id", None)),
    }


class TelegramLinkInput(BaseModel):
    chat_id: str


@app.post("/api/me/telegram")
def link_telegram(data: TelegramLinkInput, user: User = Depends(get_current_user)):
    """Vincula o chat_id do Telegram ao usuário para receber notificações de perguntas nos anúncios."""
    chat_id = (data.chat_id or "").strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id é obrigatório.")
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == user.id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        u.telegram_chat_id = chat_id[:64]
        db.commit()
        return {"ok": True, "message": "Telegram vinculado. Você receberá notificações de novas perguntas."}
    finally:
        db.close()


@app.get("/api/debug-admin")
def debug_admin(user: User = Depends(get_current_user)):
    """Diagnóstico: por que isAdmin pode estar false. Use para conferir ADMIN_EMAILS."""
    email = user.email
    is_admin_result = is_admin(email)
    admin_list = get_admin_emails()
    return {
        "seu_email": email,
        "isAdmin": is_admin_result,
        "admin_emails_quantidade": len(admin_list),
        "dica": (
            "Seu email está vazio no sistema - verifique se o Clerk JWT envia o claim 'email'."
            if not email
            else (
                "ADMIN_EMAILS vazio. Defina a variável e reinicie o backend."
                if not admin_list
                else (
                    "Email não consta em ADMIN_EMAILS. Use exatamente (copie): " + repr(email.strip().lower())
                    if not is_admin_result
                    else "Tudo ok - você é admin."
                )
            )
        ),
    }


@app.get("/api/ml-auth-url")
def ml_auth_url(user: User = Depends(get_current_user)):
    """Retorna URL para redirecionar o usuário ao OAuth do Mercado Livre."""
    # #region agent log
    _debug_log("api_ml_auth_url_entry", {"user_id": user.id}, "H2")
    # #endregion
    url = get_auth_url()
    if not url:
        _debug_log("api_ml_auth_url_no_config", {}, "H2")
        raise HTTPException(
            status_code=503,
            detail="Mercado Livre não configurado. Defina ML_APP_ID, ML_SECRET e ML_REDIRECT_URI.",
        )
    _debug_log("api_ml_auth_url_ok", {"has_url": bool(url)}, "H2")
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
    """Retorna se o usuário tem conta ML conectada. Tenta renovar o token automaticamente se expirado."""
    token = get_valid_ml_token(user)
    return {"connected": token is not None, "seller_id": token.seller_id if token else None}


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
            detail="ml_not_connected",  # Código para frontend distinguir de paid_guard
        )
    
    result = get_user_items(token.access_token, token.seller_id, status=status, limit=limit, offset=offset)
    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Erro ao buscar anúncios do Mercado Livre.",
        )
    
    # Busca detalhes dos itens se houver IDs e custos salvos
    items_data = []
    if result.get("results"):
        item_ids = result["results"][:20]  # Máx 20 por vez
        items_details = get_multiple_items(token.access_token, item_ids)
        if items_details:
            items_data = [i for i in items_details if not _is_subscription_plan(i)]
        # Injeta custos salvos por item
        if items_data:
            ids = [i.get("id") for i in items_data if i.get("id")]
            if ids:
                db = SessionLocal()
                try:
                    costs = {c.item_id: c for c in db.query(ItemCost).filter(ItemCost.user_id == user.id, ItemCost.item_id.in_(ids)).all()}
                    for it in items_data:
                        c = costs.get(it.get("id"))
                        if c:
                            it["custo_produto"] = c.custo_produto
                            it["embalagem"] = c.embalagem or 0
                            it["frete"] = c.frete or 0
                            it["taxa_pct"] = c.taxa_pct
                            it["imposto_pct"] = c.imposto_pct
                finally:
                    db.close()
    
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
        raise HTTPException(status_code=403, detail="ml_not_connected")
    
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
        raise HTTPException(status_code=403, detail="ml_not_connected")
    
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
        raise HTTPException(status_code=403, detail="ml_not_connected")
    
    order = get_order_details(token.access_token, order_id)
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Pedido não encontrado.",
        )
    
    return order


@app.get("/api/ml/search")
def ml_search(
    q: str = "",
    limit: int = 50,
    offset: int = 0,
    sort: Optional[str] = None,
    user: User = Depends(paid_guard),
):
    """Busca no ML — lista concorrentes por termo. Usa busca pública (sem token) pois token gera 403 em apps não certificados."""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Digite pelo menos 2 caracteres para buscar.")
    # Prioriza busca SEM token: API ML retorna 403 com token em apps não certificados
    result = search_public(site_id="MLB", q=q.strip(), limit=limit, offset=offset, sort=sort, access_token=None)
    if result is None:
        token = get_valid_ml_token(user)
        access_token = token.access_token if token else None
        if access_token:
            result = search_public(site_id="MLB", q=q.strip(), limit=limit, offset=offset, sort=sort, access_token=access_token)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Busca indisponível. Verifique sua conexão ou tente novamente em instantes.",
        )
    return result


def _parse_ml_item_id(url_or_id: str) -> Optional[str]:
    """Extrai ID do anúncio (MLB123...) de URL do ML ou do próprio ID. Aceita MLB-123 ou MLB123."""
    if not url_or_id or not isinstance(url_or_id, str):
        return None
    s = url_or_id.strip()
    match = re.search(r"MLB-?\d+", s, re.IGNORECASE)
    if match:
        raw = match.group(0).upper()
        return raw.replace("-", "") if "-" in raw else raw
    return None


class AddCompetitorInput(BaseModel):
    item_id: Optional[str] = None
    url: Optional[str] = None
    nickname: Optional[str] = None


@app.post("/api/ml/competitors")
def ml_competitors_add(data: AddCompetitorInput, user: User = Depends(paid_guard)):
    """Adiciona um concorrente por ID ou URL do anúncio no ML (funciona sem certificação da busca)."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    item_id = _parse_ml_item_id(data.item_id or data.url or "")
    if not item_id:
        raise HTTPException(status_code=400, detail="Informe o ID do anúncio (ex: MLB123456) ou a URL do produto no Mercado Livre.")
    item = get_item_by_id(token.access_token, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado no Mercado Livre. Verifique o ID ou a URL.")
    db = SessionLocal()
    try:
        existing = db.query(CompetitorItem).filter(CompetitorItem.user_id == user.id, CompetitorItem.item_id == item_id).first()
        if existing:
            if data.nickname is not None:
                existing.nickname = (data.nickname or "").strip()[:128] or None
                db.commit()
            return {"ok": True, "item_id": item_id, "message": "Concorrente já cadastrado; apelido atualizado."}
        db.add(CompetitorItem(user_id=user.id, item_id=item_id, nickname=(data.nickname or "").strip()[:128] or None))
        db.commit()
        return {"ok": True, "item_id": item_id, "message": "Concorrente adicionado."}
    finally:
        db.close()


@app.get("/api/ml/competitors")
def ml_competitors_list(user: User = Depends(paid_guard)):
    """Lista concorrentes cadastrados com detalhes (preço, título, vendidos) do ML."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    db = SessionLocal()
    try:
        rows = db.query(CompetitorItem).filter(CompetitorItem.user_id == user.id).order_by(CompetitorItem.created_at.desc()).all()
        items = []
        for r in rows:
            detail = get_item_by_id(token.access_token, r.item_id)
            if detail:
                items.append({
                    "item_id": r.item_id,
                    "nickname": r.nickname,
                    "title": detail.get("title"),
                    "price": detail.get("price"),
                    "sold_quantity": detail.get("sold_quantity", 0),
                    "permalink": detail.get("permalink"),
                    "thumbnail": detail.get("thumbnail"),
                })
            else:
                items.append({"item_id": r.item_id, "nickname": r.nickname, "title": None, "price": None, "sold_quantity": None, "permalink": None, "thumbnail": None})
        return {"items": items}
    finally:
        db.close()


@app.delete("/api/ml/competitors/{item_id}")
def ml_competitors_remove(item_id: str, user: User = Depends(paid_guard)):
    """Remove um concorrente da lista."""
    item_id = _parse_ml_item_id(item_id) or item_id
    db = SessionLocal()
    try:
        row = db.query(CompetitorItem).filter(CompetitorItem.user_id == user.id, CompetitorItem.item_id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Concorrente não encontrado.")
        db.delete(row)
        db.commit()
        return {"ok": True, "message": "Concorrente removido."}
    finally:
        db.close()


@app.get("/api/ml/compare/{item_id}")
def ml_compare(
    item_id: str,
    user: User = Depends(paid_guard),
):
    """Compara um anúncio do usuário com concorrentes na busca do ML."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    
    item = get_item_details(token.access_token, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Anúncio não encontrado.")
    
    # Busca por título ou categoria
    search_term = item.get("title", "").strip()
    if not search_term and item.get("category_id"):
        search_term = item.get("category_id", "")
    if not search_term or len(search_term) < 2:
        raise HTTPException(status_code=400, detail="Não foi possível definir termo de busca para este anúncio.")
    
    # Busca pública primeiro (token gera 403 em apps não certificados)
    result = search_public(site_id="MLB", q=search_term[:80], limit=50, offset=0, access_token=None)
    if result is None:
        result = search_public(site_id="MLB", q=search_term[:80], limit=50, offset=0, access_token=token.access_token)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Comparação indisponível. Tente reconectar sua conta no dashboard.",
        )
    
    results = result.get("results", [])
    paging = result.get("paging", {})
    total_results = paging.get("total", 0)
    
    # Encontra a posição do item do usuário (0-indexed)
    user_position = None
    for i, r in enumerate(results):
        rid = r.get("id") if isinstance(r, dict) else None
        if rid == item_id:
            user_position = i + 1
            break
    
    return {
        "my_item": item,
        "search_term": search_term,
        "results": results,
        "paging": paging,
        "user_position": user_position,
        "total_results": total_results,
        "in_top_50": user_position is not None,
    }


@app.get("/api/ml/metrics")
def ml_metrics(user: User = Depends(paid_guard)):
    """Retorna métricas gerais da conta do Mercado Livre."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    
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


# ------------------------------------------------------------------
# Perguntas nos anúncios ML (webhook + fila aprovação + publicar)
# ------------------------------------------------------------------
def _user_by_seller_id(seller_id: str) -> Optional[User]:
    """Retorna User que possui o seller_id no MlToken."""
    if not seller_id:
        return None
    db = SessionLocal()
    try:
        token = db.query(MlToken).filter(MlToken.seller_id == str(seller_id)).first()
        return db.query(User).filter(User.id == token.user_id).first() if token else None
    finally:
        db.close()


def _get_few_shot_feedback(user_id: int, item_id: Optional[str], limit: int = 5) -> list:
    """Últimos (pergunta, resposta_final) do usuário para few-shot."""
    db = SessionLocal()
    try:
        q = (
            db.query(QuestionAnswerFeedback)
            .filter(QuestionAnswerFeedback.user_id == user_id)
            .order_by(QuestionAnswerFeedback.created_at.desc())
            .limit(limit * 2)
        )
        rows = q.all()
        out = []
        for r in rows:
            out.append((r.pergunta_texto or "", r.resposta_final_publicada or ""))
        return out[:limit]
    finally:
        db.close()


def _process_ml_question_webhook(question_id: str, user_id: int):
    """Background: busca pergunta no ML, gera resposta com IA, salva em PendingQuestion."""
    from app.services.llm_service import run_answer_for_question

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        token = db.query(MlToken).filter(MlToken.user_id == user_id).first()
        if not token or not token.access_token:
            return
        detail = get_question_detail(token.access_token, question_id)
        if not detail:
            logger.warning("Webhook question: não foi possível obter detalhe da pergunta %s", question_id)
            return
        if db.query(PendingQuestion).filter(PendingQuestion.question_id == question_id).first():
            return
        item_id = (detail.get("item_id") or detail.get("item", {}).get("id") if isinstance(detail.get("item"), dict) else None) or None
        if not item_id and isinstance(detail.get("item"), str):
            item_id = detail.get("item")
        pergunta_texto = (detail.get("text") or "").strip()
        if not pergunta_texto:
            return
        item_title = None
        if item_id:
            item = get_item_details(token.access_token, item_id)
            item_title = (item or {}).get("title")
        few_shot = _get_few_shot_feedback(user_id, item_id)
        try:
            resposta_ia = run_answer_for_question(
                pergunta_texto,
                item_title=item_title,
                few_shot_examples=few_shot if few_shot else None,
            )
        except Exception as e:
            logger.exception("IA resposta pergunta: %s", e)
            resposta_ia = "Obrigado pela mensagem. Retornaremos em breve."
        db.add(
            PendingQuestion(
                user_id=user_id,
                question_id=question_id,
                item_id=item_id,
                item_title=item_title,
                pergunta_texto=pergunta_texto[:2048],
                resposta_ia_sugerida=resposta_ia[:2048] if resposta_ia else None,
                status="pending",
            )
        )
        db.commit()
        logger.info("Pergunta %s enfileirada para aprovação (user_id=%s)", question_id, user_id)
        # Notificação (Telegram preferencial, e-mail fallback)
        try:
            from app.services.notification_service import send_question_notification, send_question_notification_email
            u = db.query(User).filter(User.id == user_id).first()
            sent = False
            if u and getattr(u, "telegram_chat_id", None):
                sent = send_question_notification(
                    u.telegram_chat_id,
                    pergunta_texto[:200],
                    resposta_ia[:300] if resposta_ia else "",
                )
            if not sent and u and (u.email or "").strip():
                send_question_notification_email(
                    (u.email or "").strip(),
                    pergunta_texto[:200],
                    resposta_ia[:300] if resposta_ia else "",
                )
        except Exception as en:
            logger.warning("Notificação pergunta: %s", en)
    except Exception as e:
        logger.exception("process_ml_question_webhook: %s", e)
    finally:
        db.close()


@app.post("/api/ml-webhook")
async def ml_webhook(request: Request, background_tasks: BackgroundTasks):
    """Recebe notificações do Mercado Livre (tópico questions). Responder 200 em <500ms."""
    try:
        body = await request.json()
    except Exception:
        logger.warning("Webhook ML: body inválido ou não-JSON")
        return JSONResponse(status_code=400, content={"received": False})

    topic = body.get("topic") or body.get("type")
    if topic != "questions":
        return JSONResponse(status_code=200, content={"received": True})

    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    resource = body.get("resource") or data.get("resource") or data.get("id")
    user_id_ml = body.get("user_id") or body.get("seller_id") or data.get("user_id") or data.get("seller_id")

    question_id = None
    if isinstance(resource, str):
        if "questions" in resource:
            question_id = resource.split("/")[-1].strip() or resource.replace("questions/", "").strip()
        else:
            question_id = resource.strip()
    if not question_id:
        logger.warning("Webhook ML questions: resource vazio. body_keys=%s", list(body.keys()))
        return JSONResponse(status_code=200, content={"received": True})

    logger.info("Webhook ML questions: question_id=%s user_id_ml=%s", question_id, user_id_ml)

    user = None
    if user_id_ml is not None:
        user = _user_by_seller_id(str(user_id_ml))
    if not user:
        db = SessionLocal()
        try:
            for token in db.query(MlToken).all():
                u = db.query(User).filter(User.id == token.user_id).first()
                if not u:
                    continue
                t = get_valid_ml_token(u)
                if t and t.access_token:
                    detail = get_question_detail(t.access_token, question_id)
                    if detail:
                        user = u
                        break
        finally:
            db.close()

    if user:
        background_tasks.add_task(_process_ml_question_webhook, question_id, user.id)
        logger.info("Webhook ML questions: tarefa adicionada para user_id=%s question_id=%s", user.id, question_id)
    else:
        logger.warning("Webhook ML questions: usuário não encontrado. question_id=%s user_id_ml=%s", question_id, user_id_ml)

    return JSONResponse(status_code=200, content={"received": True})


@app.get("/api/ml/questions")
def ml_questions_list(
    status: Optional[str] = None,
    item_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(paid_guard),
):
    """Lista perguntas recebidas nos anúncios do vendedor (API ML)."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    result = get_questions_search(
        token.access_token,
        seller_id=token.seller_id,
        item_id=item_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Erro ao buscar perguntas no Mercado Livre.")
    return result


@app.get("/api/ml/questions/pending")
def ml_questions_pending(user: User = Depends(paid_guard)):
    """Lista perguntas com resposta sugerida aguardando aprovação/edição."""
    db = SessionLocal()
    try:
        rows = (
            db.query(PendingQuestion)
            .filter(PendingQuestion.user_id == user.id, PendingQuestion.status == "pending")
            .order_by(PendingQuestion.created_at.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "question_id": r.question_id,
                "item_id": r.item_id,
                "item_title": r.item_title,
                "pergunta_texto": r.pergunta_texto,
                "resposta_ia_sugerida": r.resposta_ia_sugerida,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


class PublishAnswerInput(BaseModel):
    text: str


@app.get("/api/ml/questions/metrics")
def ml_questions_metrics(user: User = Depends(paid_guard)):
    """Métricas de atendimento: total de perguntas, respondidas, não respondidas, tempo médio até resposta."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    result = get_questions_search(token.access_token, seller_id=token.seller_id, limit=100, offset=0)
    if result is None:
        raise HTTPException(status_code=500, detail="Erro ao buscar perguntas no Mercado Livre.")
    questions = result.get("questions") or []
    total = len(questions)
    answered = 0
    unanswered = 0
    times_seconds = []
    for q in questions:
        status = (q.get("status") or "").upper()
        if status == "ANSWERED":
            answered += 1
            ans = q.get("answer") or {}
            q_created = q.get("date_created")
            a_created = ans.get("date_created")
            if q_created and a_created:
                try:
                    from datetime import datetime
                    q_dt = datetime.fromisoformat(q_created.replace("Z", "+00:00")) if isinstance(q_created, str) else q_created
                    a_dt = datetime.fromisoformat(a_created.replace("Z", "+00:00")) if isinstance(a_created, str) else a_created
                    delta = (a_dt - q_dt).total_seconds()
                    if delta >= 0:
                        times_seconds.append(delta)
                except Exception:
                    pass
        elif status in ("UNANSWERED", "CLOSED_UNANSWERED"):
            unanswered += 1
    avg_seconds = sum(times_seconds) / len(times_seconds) if times_seconds else None
    return {
        "total_questions": total,
        "answered": answered,
        "unanswered": unanswered,
        "avg_time_to_answer_seconds": round(avg_seconds, 0) if avg_seconds is not None else None,
        "avg_time_to_answer_hours": round(avg_seconds / 3600, 2) if avg_seconds is not None else None,
    }


@app.post("/api/ml/questions/{question_id}/publish")
def ml_question_publish(question_id: str, data: PublishAnswerInput, user: User = Depends(paid_guard)):
    """Aprova ou edita a resposta e publica no ML. Grava feedback para few-shot."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    text = (data.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto da resposta é obrigatório.")
    result = post_answer(token.access_token, question_id, text)
    if result is None:
        raise HTTPException(status_code=400, detail="Não foi possível publicar a resposta no Mercado Livre.")
    db = SessionLocal()
    try:
        pending = db.query(PendingQuestion).filter(PendingQuestion.user_id == user.id, PendingQuestion.question_id == question_id).first()
        if pending:
            db.add(
                QuestionAnswerFeedback(
                    user_id=user.id,
                    question_id=question_id,
                    item_id=pending.item_id,
                    pergunta_texto=pending.pergunta_texto or "",
                    resposta_ia_sugerida=pending.resposta_ia_sugerida,
                    resposta_final_publicada=text[:2048],
                )
            )
            pending.status = "published"
            db.commit()
        return {"ok": True, "message": "Resposta publicada."}
    finally:
        db.close()


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


# ------------------------------------------------------------------
# Painel financeiro integrado ML (dados via API + custos no banco)
# ------------------------------------------------------------------
@app.get("/api/financial-panel")
def financial_panel(user: User = Depends(paid_guard)):
    """Retorna dados financeiros dos anúncios do usuário via API ML + custos salvos no banco."""
    return _compute_financial_panel(user)


@app.post("/api/financial-panel/costs")
def save_financial_costs(data: ItemCostsBatch, user: User = Depends(paid_guard)):
    """Salva/atualiza custos por anúncio no banco."""
    db = SessionLocal()
    try:
        for upd in data.items:
            c = db.query(ItemCost).filter(ItemCost.user_id == user.id, ItemCost.item_id == upd.item_id).first()
            if c is None:
                c = ItemCost(user_id=user.id, item_id=upd.item_id)
                db.add(c)
            if upd.sku is not None:
                c.sku = upd.sku
            if upd.custo_produto is not None:
                c.custo_produto = upd.custo_produto
            if upd.embalagem is not None:
                c.embalagem = upd.embalagem
            if upd.frete is not None:
                c.frete = upd.frete
            if upd.taxa_pct is not None:
                c.taxa_pct = upd.taxa_pct
            if upd.imposto_pct is not None:
                c.imposto_pct = upd.imposto_pct
        db.commit()
        return {"ok": True, "saved": len(data.items)}
    finally:
        db.close()


def _compute_financial_panel(user: User) -> dict:
    """Lógica interna do painel financeiro (reutilizada por ai-insights)."""
    token = get_valid_ml_token(user)
    if not token or not token.seller_id:
        raise HTTPException(status_code=403, detail="ml_not_connected")
    result = get_user_items(token.access_token, token.seller_id, status="all", limit=50)
    if not result or not result.get("results"):
        return {"metrics": {"total_listings": 0, "profit_total": 0, "margin_mean": 0, "missing_cost": 0}, "items": [], "top_profit": []}
    item_ids = result["results"][:50]
    items_data = get_multiple_items(token.access_token, item_ids) or []
    items_data = [i for i in items_data if not _is_subscription_plan(i)]
    db = SessionLocal()
    try:
        costs = {c.item_id: c for c in db.query(ItemCost).filter(ItemCost.user_id == user.id).all()}
    finally:
        db.close()
    DEFAULT_TAXA, DEFAULT_IMPOSTO = 13.0, 5.0
    items = []
    for it in items_data:
        c = costs.get(it.get("id"))
        price = float(it.get("price") or 0)
        taxa = (c.taxa_pct if c and c.taxa_pct is not None else None) or DEFAULT_TAXA
        imposto = (c.imposto_pct if c and c.imposto_pct is not None else None) or DEFAULT_IMPOSTO
        custo = c.custo_produto if c and c.custo_produto is not None else None
        emb, frt = (c.embalagem if c else 0) or 0, (c.frete if c else 0) or 0
        fee_amount = price * (taxa / 100)
        imp_amount = price * (imposto / 100)
        cost_total = (custo or 0) + fee_amount + imp_amount + emb + frt
        profit = price - cost_total if custo is not None else None
        margin = (profit / price * 100) if profit is not None and price else None
        sku = (c.sku if c else None) or it.get("seller_custom_field") or it.get("id")
        items.append({"id": it.get("id"), "title": it.get("title"), "sku": sku, "price": price, "sold_quantity": it.get("sold_quantity", 0), "available_quantity": it.get("available_quantity", 0), "status": it.get("status"), "custo_produto": custo, "embalagem": emb, "frete": frt, "taxa_pct": taxa, "imposto_pct": imposto, "fee_amount": round(fee_amount, 2), "cost_total": round(cost_total, 2), "profit": round(profit, 2) if profit is not None else None, "margin_pct": round(margin, 2) if margin is not None else None})
    valid_profits = [i for i in items if i["profit"] is not None]
    total_listings = len(items)
    active_listings = sum(1 for i in items if str(i.get("status", "")).lower() == "active")
    total_stock = sum(i.get("available_quantity", 0) or 0 for i in items)
    avg_price = sum(i["price"] for i in items) / total_listings if total_listings else 0
    avg_fee = sum(i["taxa_pct"] for i in items) / total_listings if total_listings else DEFAULT_TAXA
    profit_mean = sum(i["profit"] for i in valid_profits) / len(valid_profits) if valid_profits else 0
    margin_mean = sum(i["margin_pct"] for i in valid_profits) / len(valid_profits) if valid_profits else 0
    profit_total = sum(i["profit"] for i in valid_profits)
    fee_total = sum(i["fee_amount"] for i in items)
    missing_cost = sum(1 for i in items if i["custo_produto"] is None)
    top_profit = sorted(valid_profits, key=lambda x: x["profit"], reverse=True)[:10]
    return {"metrics": {"total_listings": total_listings, "active_listings": active_listings, "total_stock": total_stock, "avg_price": round(avg_price, 2), "avg_fee_pct": round(avg_fee, 2), "profit_mean": round(profit_mean, 2), "margin_mean": round(margin_mean, 2), "profit_total": round(profit_total, 2), "fee_total": round(fee_total, 2), "missing_cost": missing_cost}, "items": items, "top_profit": [{"ITEM_ID": i["id"], "SKU_STR": i["sku"], "TITLE": i["title"], "PRICE_NUM": i["price"], "COST": i["custo_produto"], "PROFIT": i["profit"], "MARGIN_PCT": i["margin_pct"]} for i in top_profit]}


def _log_ia_failure(user_id: Optional[int], event_type: str, message: str, extra: Optional[str] = None):
    """Registra falha de IA no audit_log para admin."""
    db = SessionLocal()
    try:
        db.add(AuditLog(user_id=user_id, event_type=event_type, message=message[:512], extra=(extra or "")[:1024]))
        db.commit()
    except Exception as ex:
        logger.warning("Falha ao registrar audit_log: %s", ex)
    finally:
        db.close()


@app.post("/api/financial-panel/ai-insights")
def financial_ai_insights(user: User = Depends(paid_guard)):
    """Gera insights de IA sobre o painel financeiro."""
    try:
        from app.services.llm_service import run_market_analysis
    except Exception:
        raise HTTPException(status_code=503, detail="IA não configurada. Defina OPENAI_API_KEY.")
    panel = _compute_financial_panel(user)
    items = panel.get("items", [])
    metrics = panel.get("metrics", {})
    # Monta resumo por item: preço, margem, vendidos (CRÍTICO para avaliar competitividade)
    items_summary = []
    for it in items[:15]:
        titulo = (it.get("title") or "")[:50]
        preco = it.get("price", 0)
        margem = it.get("margin_pct")
        vendidos = it.get("sold_quantity", 0)
        lucro = it.get("profit")
        items_summary.append(f"  - {titulo}... | preço R$ {preco:.2f} | margem {margem}% | vendidos: {vendidos} | lucro R$ {lucro}")
    items_text = "\n".join(items_summary) if items_summary else "(nenhum item)"
    total_vendidos = sum(i.get("sold_quantity", 0) or 0 for i in items)
    prompt = f"""Você é um consultor de vendas do Mercado Livre. Analise os dados de forma CRÍTICA e REALISTA.

REGRAS IMPORTANTES:
- Margem alta com ZERO vendas indica PREÇO ACIMA DO MERCADO — o vendedor provavelmente está mais caro que concorrentes.
- Lucro positivo sem vendas não é "saúde financeira excelente" — é apenas potencial teórico.
- Sugira ações CONCRETAS: revisar preço vs concorrentes, promoções, estoque, anúncio inativo, etc.
- Evite sugestões genéricas como "manter margem" ou "expandir anúncios" se não houver vendas.

DADOS:
- Total de anúncios: {len(items)}
- Lucro total: R$ {metrics.get('profit_total', 0)}
- Margem média: {metrics.get('margin_mean', 0)}%
- Total de VENDAS (sold_quantity): {total_vendidos}
- Itens sem custo cadastrado: {metrics.get('missing_cost', 0)}

DETALHAMENTO POR ANÚNCIO (preço, margem, vendidos, lucro):
{items_text}

Retorne um JSON com:
- "resumo": análise curta e CRÍTICA (ex: "Margem boa, mas zero vendas sugere preço elevado. Compare com concorrentes.")
- "alertas": problemas reais (ex: "Anúncios com margem alta e 0 vendas — provável preço acima do mercado")
- "sugestoes": ações CONCRETAS (ex: "Pesquise preços de concorrentes e ajuste oferta", "Considere promoção para testar demanda")
- "top_oportunidades": até 3 oportunidades REAIS baseadas nos dados

Retorne APENAS o JSON, sem markdown."""
    try:
        out = run_market_analysis(prompt)
        return out
    except Exception as e:
        _log_ia_failure(user.id, "ia_insights_fail", str(e)[:512], f"user_id={user.id}")
        logger.exception("Erro ao gerar insights IA: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# IA Assistente: perguntas e respostas para clientes
# ------------------------------------------------------------------
@app.post("/api/ia/perguntas")
def ia_perguntas(data: IAPerguntaInput, user: User = Depends(paid_guard)):
    """Responde perguntas do vendedor sobre vendas, estratégia, Mercado Livre, etc."""
    pergunta = (data.pergunta or "").strip()
    if not pergunta or len(pergunta) < 5:
        raise HTTPException(status_code=400, detail="Digite uma pergunta com pelo menos 5 caracteres.")
    if len(pergunta) > 2000:
        raise HTTPException(status_code=400, detail="Pergunta muito longa. Resuma em até 2000 caracteres.")
    try:
        from app.services.llm_service import run_chat
    except Exception:
        raise HTTPException(status_code=503, detail="IA não configurada. Defina OPENAI_API_KEY.")
    system = "Você é um assistente especializado em vendas no Mercado Livre. Responda de forma clara e objetiva, em português."
    try:
        resposta = run_chat(pergunta, system_hint=system)
        return {"resposta": resposta}
    except Exception as e:
        _log_ia_failure(user.id, "ia_perguntas_fail", str(e)[:512], f"user_id={user.id}")
        logger.exception("Erro IA perguntas: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


_RESPOSTA_TIPOS = {
    "pedido_atrasado": "O cliente está perguntando sobre atraso no envio ou entrega do pedido.",
    "duvida_produto": "O cliente tem dúvida sobre características, especificações ou uso do produto.",
    "reclamacao": "O cliente está reclamando de algo (produto, prazo, atendimento).",
    "agradecimento": "O cliente agradeceu pela compra ou pelo atendimento.",
    "orcamento": "O cliente pediu orçamento ou informação sobre preços.",
    "outro": "Outra situação de atendimento ao cliente.",
}


@app.post("/api/ia/resposta-cliente")
def ia_resposta_cliente(data: IARespostaClienteInput, user: User = Depends(paid_guard)):
    """Gera sugestão de resposta profissional para mensagem de cliente no Mercado Livre."""
    tipo = (data.tipo or "outro").strip()
    contexto = (data.contexto or "").strip()
    msg = (data.mensagem_cliente or "").strip()
    tipo_desc = _RESPOSTA_TIPOS.get(tipo, _RESPOSTA_TIPOS["outro"])
    try:
        from app.services.llm_service import run_chat
    except Exception:
        raise HTTPException(status_code=503, detail="IA não configurada. Defina OPENAI_API_KEY.")
    prompt_parts = [f"Situação: {tipo_desc}"]
    if contexto:
        prompt_parts.append(f"Contexto adicional: {contexto}")
    if msg:
        prompt_parts.append(f"Mensagem do cliente: {msg}")
    prompt_parts.append("\nGere uma resposta profissional, cordial e concisa para o vendedor enviar ao cliente no Mercado Livre. Use tom adequado e evite jargões. Responda em português.")
    prompt = "\n".join(prompt_parts)
    system = "Você é um assistente que ajuda vendedores do Mercado Livre a redigir respostas para clientes. Seja cordial, profissional e objetivo."
    try:
        resposta = run_chat(prompt, system_hint=system)
        return {"resposta": resposta}
    except Exception as e:
        _log_ia_failure(user.id, "ia_resposta_cliente_fail", str(e)[:512], f"user_id={user.id}")
        logger.exception("Erro IA resposta cliente: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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

    # Colunas da planilha ML podem vir em PT ou EN
    price_col = _find_col(df, "PRICE", "Preço", "Preco", "VALOR")
    fee_col = _find_col(df, "FEE_PER_SALE", "TAXA", "Taxa", "FEE")
    sku_col = _find_col(df, "SKU", "COD. DO PROD.", "COD DO PROD", "CODIGO")
    status_col = _find_col(df, "STATUS", "Status", "ESTADO")
    qty_col = _find_col(df, "QUANTITY", "QUANTITY", "Quantidade", "QTD", "ESTQ")
    title_col = _find_col(df, "TITLE", "Título", "Titulo", "DESCRIÇÃO", "Descricao")

    if not price_col:
        raise HTTPException(status_code=400, detail="Coluna de preço (PRICE/Preço) não encontrada na planilha.")
    df["PRICE_NUM"] = pd.to_numeric(df[price_col], errors="coerce")
    if fee_col:
        df["FEE_PCT"] = df[fee_col].apply(_parse_percent)
    else:
        df["FEE_PCT"] = 0.0
    df["FEE_AMOUNT"] = df["PRICE_NUM"] * (df["FEE_PCT"].fillna(0) / 100)

    df["SKU_STR"] = (df[sku_col] if sku_col else df.iloc[:, 0]).astype(str).str.strip()
    df["COST"] = df["SKU_STR"].map(cost_map) if cost_map else pd.NA

    df["COST_TOTAL"] = df["COST"] + df["FEE_AMOUNT"] + embalagem + frete
    df["PROFIT"] = df["PRICE_NUM"] - df["COST_TOTAL"]
    price_safe = df["PRICE_NUM"].replace(0, float("nan"))
    df["MARGIN_PCT"] = (df["PROFIT"] / price_safe) * 100

    total_listings = int(len(df))
    if status_col:
        active_listings = int(df[status_col].astype(str).str.contains("Ativo", case=False, na=False).sum())
    else:
        active_listings = total_listings
    if qty_col:
        total_stock = int(pd.to_numeric(df[qty_col], errors="coerce").fillna(0).sum())
    else:
        total_stock = 0

    avg_price = float(df["PRICE_NUM"].mean()) if total_listings else 0.0
    avg_fee_pct = float(df["FEE_PCT"].mean()) if total_listings else 0.0

    profit_mean = float(df["PROFIT"].mean()) if df["PROFIT"].notna().any() else 0.0
    margin_mean = float(df["MARGIN_PCT"].mean()) if df["MARGIN_PCT"].notna().any() else 0.0
    profit_total = float(df["PROFIT"].sum()) if df["PROFIT"].notna().any() else 0.0
    fee_total = float(df["FEE_AMOUNT"].sum()) if df["FEE_AMOUNT"].notna().any() else 0.0

    missing_cost = int(df["COST"].isna().sum())

    title_series = df[title_col] if title_col else df["SKU_STR"]
    top_cols = ["ITEM_ID", "SKU_STR", "PRICE_NUM", "COST", "PROFIT", "MARGIN_PCT"]
    top_df = df.copy()
    top_df["TITLE"] = title_series
    top_profit = (
        top_df[["ITEM_ID", "SKU_STR", "TITLE", "PRICE_NUM", "COST", "PROFIT", "MARGIN_PCT"]]
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


@app.post("/api/analise-anuncios")
async def analise_anuncios(file: UploadFile = File(...), user: User = Depends(paid_guard)):
    """Importa planilha ANALISE ANUNCIOS (formato CONTA 1 ML, CONTA 2 ML) e retorna análise por anúncio."""
    if not file or not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Envie um arquivo XLSX (planilha ANALISE ANUNCIOS).")
    try:
        data = await file.read()
        items = _parse_analise_anuncios(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erro ao parsear planilha analise: %s", e)
        raise HTTPException(status_code=400, detail=f"Erro ao ler planilha: {e}")
    return {"items": items, "total": len(items)}


@app.get("/sheets/test")
def test_sheets(user: User = Depends(get_current_user)):
    return read_sheet()


@app.get("/analysis/base")
def base_analysis(user: User = Depends(get_current_user)):
    data = read_sheet()
    concorrentes = normalize_concorrentes(data.get("concorrentes", []))
    return {"produto": data.get("produto", []), "concorrentes": concorrentes}


@app.get("/analysis/market")
def market_analysis(user: User = Depends(get_current_user)):
    data = read_sheet()
    return analyze_market(produto=data.get("produto", []), concorrentes=data.get("concorrentes", []))


@app.get("/analysis/market/ai")
def market_analysis_ai(user: User = Depends(get_current_user)):
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

    # registra job e dispara background (limita JOB_STORE aos últimos 500 jobs)
    _trim_job_store(JOB_STORE_MAX_SIZE)
    JOB_STORE[job_id] = {"status": "pending", "filename": file.filename, "_created": time.time()}
    background_tasks.add_task(process_job, job_id, str(file_path), user.id)

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


def _verify_mp_webhook_signature(raw_body: bytes, x_signature: Optional[str], secret: str) -> bool:
    """Verifica assinatura do webhook MP (x-signature). Se MP_WEBHOOK_SECRET não estiver definido, aceita qualquer POST."""
    if not secret:
        return True
    if not x_signature:
        return False
    try:
        parts = dict(p.split("=", 1) for p in x_signature.split(",") if "=" in p)
        v1 = parts.get("v1", "").strip()
        ts = parts.get("ts", "").strip()
        if not v1:
            return False
        secret_b = secret.encode() if isinstance(secret, str) else secret
        # Padrão comum: v1 = HMAC-SHA256(secret, body) ou HMAC(secret, "id:ts")
        expected_body = hmac.new(secret_b, raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(v1, expected_body):
            return True
        if ts:
            expected_ts = hmac.new(secret_b, ts.encode(), hashlib.sha256).hexdigest()
            if hmac.compare_digest(v1, expected_ts):
                return True
        return False
    except Exception:
        return False


@app.post("/api/mercado-pago-webhook")
async def mercado_pago_webhook(request: Request):
    """Recebe notificações do Mercado Pago (subscription_preapproval)."""
    raw_body = await request.body()
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Payload inválido")

    mp_secret = os.getenv("MP_WEBHOOK_SECRET", "").strip()
    if mp_secret:
        x_sig = request.headers.get("x-signature") or request.headers.get("X-Signature")
        if not _verify_mp_webhook_signature(raw_body, x_sig, mp_secret):
            logger.warning("Webhook MP: assinatura inválida ou ausente")
            raise HTTPException(status_code=401, detail="Assinatura do webhook inválida")

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


@app.get("/api/admin/audit-logs")
def admin_audit_logs(
    event_type: Optional[str] = None,
    limit: int = 100,
    admin_user: User = Depends(admin_guard),
):
    """Lista logs de auditoria (falhas IA, etc.) — admin."""
    db = SessionLocal()
    try:
        q = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if event_type:
            q = q.filter(AuditLog.event_type == event_type)
        logs = q.all()
        return [
            {"id": l.id, "user_id": l.user_id, "event_type": l.event_type, "message": l.message, "extra": l.extra, "created_at": l.created_at.isoformat() if l.created_at else None}
            for l in logs
        ]
    finally:
        db.close()


@app.get("/api/admin/metrics")
def admin_metrics(admin_user: User = Depends(admin_guard)):
    """Métricas do sistema para gestão (admin)."""
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        active_plan = db.query(User).filter(User.plan == "active").count()
        free_plan = db.query(User).filter(User.plan == "free").count()
        subs = db.query(Subscription).filter(Subscription.status == "active").count()
        ml_connected = db.query(MlToken).count()
        return {
            "total_users": total_users,
            "users_active_plan": active_plan,
            "users_free_plan": free_plan,
            "subscriptions_active": subs,
            "ml_accounts_connected": ml_connected,
        }
    finally:
        db.close()


class AdminUpdatePlan(BaseModel):
    plan: str  # free | active


@app.patch("/api/admin/users/{user_id}/plan")
def admin_update_user_plan(
    user_id: int,
    data: AdminUpdatePlan,
    admin_user: User = Depends(admin_guard),
):
    """Altera o plano de um usuário (admin)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        if data.plan not in ("free", "active"):
            raise HTTPException(status_code=400, detail="Plano inválido. Use 'free' ou 'active'.")
        user.plan = data.plan
        db.commit()
        return {"ok": True, "user_id": user_id, "plan": data.plan}
    finally:
        db.close()


@app.get("/api/admin/logs")
def admin_logs(admin_user: User = Depends(admin_guard)):
    """Retorna logs do backend (admin)."""
    if not LOG_FILE.exists():
        return PlainTextResponse("Arquivo de log ainda não criado. O backend registrará eventos aqui ao processar requisições.")
    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return PlainTextResponse("(Arquivo de log vazio)\n\nO backend registrará eventos aqui quando houver atividade.")
        # Últimas ~500 linhas para não sobrecarregar
        lines = text.strip().split("\n")
        if len(lines) > 500:
            text = "\n".join(lines[-500:])
        return PlainTextResponse(text, media_type="text/plain")
    except Exception as e:
        logger.exception(f"Erro ao ler log: {e}")
        return PlainTextResponse(f"Erro ao ler logs: {e}")

# ------------------------------------------------------------------
# Frontend estático (caminho absoluto para funcionar de qualquer pasta)
# ------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
