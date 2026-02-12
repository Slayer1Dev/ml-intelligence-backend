# Mercado Insights — Brand Guidelines

Guia de identidade visual. Documento completo: **IDENTIDADE_VISUAL.md**

---

## Paleta de Cores

| Nome | Hex | Uso |
|------|-----|-----|
| **Azul Primario** | `#1e40af` | Titulos, logo, elementos de destaque |
| **Azul Escuro** | `#1e3a8a` | Hover em elementos azuis |
| **Azul Claro** | `#dbeafe` | Fundos, gradientes (topo) |
| **Azul Ceu** | `#bfdbfe` | Fundos secundarios |
| **Amarelo** | `#fbbf24` | CTAs, botoes, destaques de acao |
| **Amarelo Hover** | `#f59e0b` | Hover em botoes amarelos |
| **Preto** | `#0f172a` | Textos principais |
| **Cinza** | `#475569` | Textos secundarios |
| **Cinza Claro** | `#94a3b8` | Textos terciarios, placeholders |
| **Branco** | `#ffffff` | Fundos, cards |

---

## Tipografia

- **Fonte:** Plus Jakarta Sans (Google Fonts)
- **Pesos:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold), 800 (extrabold)

### Hierarquia

| Elemento | Tamanho | Peso | Cor |
|----------|---------|------|-----|
| H1 (Hero) | 3.5rem | 800 | Preto |
| H1 (Paginas) | 1.75rem | 700 | Preto |
| H2 | 2rem | 700 | Preto |
| H3 | 1.25rem | 600 | Azul Primario |
| Body | 1rem | 400 | Preto |
| Muted | 0.95rem | 400 | Cinza |

---

## Componentes

### Botoes

- **Primario (CTA):** Fundo amarelo, texto preto, borda arredondada 10-12px
- **Secundario:** Fundo azul claro, texto azul primario

### Cards

- Fundo branco
- Borda: 1px solid rgba(30, 64, 175, 0.08)
- Border-radius: 12px
- Sombra sutil: 0 2px 8px rgba(30, 64, 175, 0.04)

### Sidebar

- Fundo branco
- Item ativo: fundo azul claro + borda esquerda amarela

---

## Gradientes

### Landing (fundo)
```css
background: linear-gradient(180deg, #dbeafe 0%, #ffffff 50%);
```

### App (fundo do main)
```css
background: linear-gradient(180deg, rgba(219, 234, 254, 0.3) 0%, #ffffff 100%);
```

---

## Efeitos

### Parallax (Landing)
- Circulos decorativos com animacao float
- Movimento no scroll (velocidades diferentes)

### Animacoes de entrada
- Fade-in + translateY(40px -> 0)
- Duracao: 0.6s
- Trigger: Intersection Observer (threshold 0.15)

### Hover
- Botoes: translateY(-1px a -3px) + sombra
- Cards: sombra mais intensa

---

## Arquivos

| Arquivo | Descricao |
|---------|-----------|
| `app.css` | Design system do app (dashboard, paginas internas) |
| `index.html` | Landing page com estilos inline |
| `BRAND.md` | Este documento |

---

## Referencias

- Cores inspiradas no Mercado Livre (amarelo) + profissionalismo (azul)
- Layout de dashboard inspirado no painel do vendedor ML
- Landing inspirada em paginas de lancamento modernas (Nintendo Switch 2, SaaS)
