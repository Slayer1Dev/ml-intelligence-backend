# Mercado Insights — Identidade Visual

> **Documento único** de referência para identidade visual. Todas as páginas devem seguir este guia.

---

## 1. Marca

| Item | Valor |
|------|-------|
| **Nome** | Mercado Insights |
| **Tagline** | Insights inteligentes para vendedores do Mercado Livre |
| **Domínio** | https://www.mercadoinsights.online |

---

## 2. Paleta de cores

| Nome | Hex | Uso |
|------|-----|-----|
| **Azul Primário** | `#1e40af` | Títulos, logo, links, elementos de destaque |
| **Azul Escuro** | `#1e3a8a` | Hover em elementos azuis, header |
| **Azul Claro** | `#dbeafe` | Fundos leves, gradientes, item ativo na sidebar |
| **Azul Céu** | `#bfdbfe` | Fundos secundários |
| **Amarelo** | `#fbbf24` | CTAs, botões principais, destaques de ação |
| **Amarelo Hover** | `#f59e0b` | Hover em botões amarelos |
| **Preto** | `#0f172a` | Textos principais |
| **Cinza** | `#475569` | Textos secundários |
| **Cinza Claro** | `#94a3b8` | Textos terciários, placeholders |
| **Branco** | `#ffffff` | Fundos, cards |

### Variáveis CSS (usar em app.css)

```css
--color-primary: #1e40af;
--color-primary-dark: #1e3a8a;
--color-primary-light: #dbeafe;
--color-accent: #fbbf24;
--color-accent-hover: #f59e0b;
--color-text: #0f172a;
--color-text-muted: #475569;
--color-text-tertiary: #94a3b8;
--color-surface: #ffffff;
```

---

## 3. Tipografia

- **Fonte:** Plus Jakarta Sans (Google Fonts)
- **Pesos:** 400, 500, 600, 700, 800

### Hierarquia

| Elemento | Tamanho | Peso | Cor |
|----------|---------|------|-----|
| H1 (Hero) | 3.5rem | 800 | Preto |
| H1 (Páginas) | 1.75rem | 700 | Preto |
| H2 | 2rem | 700 | Preto |
| H3 | 1.25rem | 600 | Azul Primário |
| Body | 1rem | 400 | Preto |
| Muted | 0.95rem | 400 | Cinza |

---

## 4. Componentes

### Botões

| Classe | Uso | Estilo |
|--------|-----|--------|
| `.btn-primary` | CTA principal | Fundo amarelo, texto preto |
| `.btn-secondary` | CTA secundário | Fundo azul claro, texto azul |
| `.button` | Ações gerais (Conectar, Buscar, Salvar) | Fundo azul, texto branco |
| `.tab-btn` | Abas (ex: Painel Financeiro) | Inativo: borda cinza, texto preto; Ativo: fundo azul, texto branco |
| `.btn-outline` | Ações discretas | Borda azul, texto azul |

### Cards

- Fundo branco
- Borda: `1px solid rgba(30, 64, 175, 0.08)`
- Border-radius: 12px
- Sombra: `0 2px 8px rgba(30, 64, 175, 0.04)`

### Sidebar

- Fundo branco
- Item ativo: fundo azul claro + borda esquerda amarela (3px)

### Navbar / Header

- Fundo branco ou azul escuro, conforme contexto
- Altura consistente (~56–64px)

---

## 5. Favicon e logo

### Regras do favicon

1. **Sem fundo branco sólido** — Deve ter fundo transparente para se integrar às abas do navegador.
2. **Ícone simples** — Reconhecível em 16×16 e 32×32.
3. **Cores** — Azul primário `#1e40af` ou amarelo `#fbbf24`; evite gradientes complexos.
4. **Formato** — PNG com transparência ou SVG; manter `favicon.ico` para fallback se necessário.

### Arquivos

- `frontend/favicon.png` — Favicon principal (32×32 ou 48×48, fundo transparente)
- Evitar quadrado branco; o ícone deve ser o símbolo sobre fundo transparente.

---

## 6. Gradientes e fundos

### Landing

```css
background: linear-gradient(180deg, #dbeafe 0%, #ffffff 50%);
```

### App (main)

```css
background: linear-gradient(180deg, rgba(219, 234, 254, 0.3) 0%, #ffffff 100%);
```

---

## 7. Efeitos e animações

| Efeito | Regra |
|--------|-------|
| **Hover botões** | `translateY(-1px a -3px)` + sombra |
| **Hover cards** | Sombra mais intensa |
| **Entrada** | Fade-in + translateY(40px → 0), 0.6s |
| **Parallax (Landing)** | Círculos decorativos com animação float |

---

## 8. Checklist de aplicação

Ao criar ou editar páginas:

- [ ] Usar variáveis CSS de `app.css`
- [ ] Favicon com fundo transparente (não quadrado branco)
- [ ] Fonte Plus Jakarta Sans carregada
- [ ] Cores da paleta (azul primário, amarelo CTA)
- [ ] Cards com border-radius 12px e sombra sutil
- [ ] Botões com estilos padronizados (btn-primary-actions, etc.)

---

## 9. Exceções

- **jobs.html** e **logs.html** — Páginas internas de suporte; usam `style.css` com tema escuro. Manter layout atual.

---

## 10. Arquivos de referência

| Arquivo | Descrição |
|---------|-----------|
| `frontend/app.css` | Design system principal |
| `frontend/BRAND.md` | Guia de marca (resumo) |
| `IDENTIDADE_VISUAL.md` | Este documento |
