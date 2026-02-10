#!/usr/bin/env python3
"""Script para renomear "ML Intelligence" para "Mercado Insights" em todos os HTMLs"""
import os
import sys
from pathlib import Path

# Fix encoding no Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

frontend_dir = Path(__file__).parent / "frontend"

# Lista de arquivos HTML para atualizar
html_files = list(frontend_dir.glob("*.html"))

count = 0
for html_file in html_files:
    try:
        content = html_file.read_text(encoding='utf-8')
        if "ML Intelligence" in content:
            new_content = content.replace("ML Intelligence", "Mercado Insights")
            html_file.write_text(new_content, encoding='utf-8')
            print(f"[OK] {html_file.name}: Atualizado")
            count += 1
        else:
            print(f"[--] {html_file.name}: Sem alteracoes")
    except Exception as e:
        print(f"[ERR] {html_file.name}: Erro - {e}")

print(f"\n[DONE] {count} arquivos atualizados!")
