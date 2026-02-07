# ML Intelligence

Ferramentas inteligentes para quem vende no Mercado Livre.

## Rodar localmente

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

Se faltar algum pacote (pandas, openpyxl, etc.), instale:

```bash
pip install fastapi uvicorn pydantic python-dotenv requests pandas openpyxl aiofiles
```

### 2. Subir o backend

```bash
uvicorn app.main:app --reload
```

### 3. Abrir no navegador

- **Landing page:** http://127.0.0.1:8000/frontend/
- **Calculadora de lucro:** http://127.0.0.1:8000/frontend/calculator.html

---

## Custos

Veja o arquivo [COSTS.md](COSTS.md) para um guia didático sobre o que precisa desembolsar e configurar.
