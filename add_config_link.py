#!/usr/bin/env python3
"""Adiciona link para config-ml.html no menu de todas as páginas"""
from pathlib import Path
import re

frontend_dir = Path(__file__).parent / "frontend"
html_files = [
    "dashboard.html",
    "financeiro.html",
    "calculator.html",
    "anuncios.html",
    "performance.html",
    "concorrentes.html",
    "perguntas-anuncios.html",
    "ia-assistente.html",
    "admin.html"
]

link_to_add = '        <a href="config-ml.html">⚙️ Config. Mercado Livre</a>\n'

count = 0
for filename in html_files:
    file_path = frontend_dir / filename
    if not file_path.exists():
        print(f"[SKIP] {filename}: Não encontrado")
        continue
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Verifica se já tem o link
        if 'config-ml.html' in content:
            print(f"[OK] {filename}: Já tem o link")
            continue
        
        # Procura o padrão: <a href="ia-assistente.html"> seguido de admin-link-wrap ou </nav>
        # Adiciona o link antes do admin-link-wrap
        pattern = r'(        <a href="ia-assistente\.html"[^>]*>.*?</a>\n)(        <span id="admin-link-wrap")'
        
        if re.search(pattern, content):
            new_content = re.sub(pattern, r'\1' + link_to_add + r'\2', content)
            file_path.write_text(new_content, encoding='utf-8')
            print(f"[OK] {filename}: Link adicionado")
            count += 1
        else:
            print(f"[WARN] {filename}: Padrão não encontrado, pulando")
    
    except Exception as e:
        print(f"[ERR] {filename}: {e}")

print(f"\n[DONE] {count} arquivos atualizados!")
