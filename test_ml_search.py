#!/usr/bin/env python3
"""
Script de teste diagnóstico para pesquisa de concorrência ML
Executa a mesma chamada que o backend faz e mostra detalhes do erro
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

ML_API = "https://api.mercadolibre.com"
ML_APP_ID = os.getenv("ML_APP_ID")
ML_SECRET = os.getenv("ML_SECRET")

def test_search_no_token():
    """Testa busca pública SEM token (como o código atual faz primeiro)"""
    print("\n" + "="*60)
    print("TESTE 1: Busca SEM token (pública)")
    print("="*60)
    
    params = {
        "q": "fone bluetooth",
        "limit": 5,
    }
    headers = {
        "User-Agent": "MLIntelligence/1.0 (https://mercadoinsights.online)"
    }
    
    try:
        resp = requests.get(f"{ML_API}/sites/MLB/search", params=params, headers=headers, timeout=15)
        
        print(f"\n✓ Status Code: {resp.status_code}")
        print(f"✓ Headers: {dict(resp.headers)}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Sucesso! Encontrados {data.get('paging', {}).get('total', 0)} resultados")
            print(f"✓ Primeiros 3 resultados:")
            for i, item in enumerate(data.get('results', [])[:3], 1):
                print(f"  {i}. {item.get('title', 'Sem título')[:60]} - R$ {item.get('price', 0)}")
        else:
            print(f"\n❌ Erro {resp.status_code}")
            print(f"❌ Body: {resp.text[:500]}")
            
            # Tenta parsear JSON do erro
            try:
                error_data = resp.json()
                print(f"\n❌ Erro estruturado:")
                print(f"   - message: {error_data.get('message', 'N/A')}")
                print(f"   - error: {error_data.get('error', 'N/A')}")
                print(f"   - status: {error_data.get('status', 'N/A')}")
                print(f"   - cause: {error_data.get('cause', 'N/A')}")
            except:
                print("   (Erro não está em formato JSON)")
                
    except requests.RequestException as e:
        print(f"\n❌ Exceção de rede: {type(e).__name__}")
        print(f"❌ Detalhes: {str(e)}")


def test_search_with_mock_token():
    """Testa busca COM token (para ver se a resposta muda)"""
    print("\n" + "="*60)
    print("TESTE 2: Busca COM token (requer token válido do ML)")
    print("="*60)
    
    # IMPORTANTE: Para este teste funcionar, você precisa de um token válido
    # Pode obter conectando sua conta ML no dashboard primeiro
    print("\n⚠️  Este teste requer um access_token válido do ML.")
    print("⚠️  Execute apenas se tiver um token para testar.")
    print("⚠️  Caso contrário, pule este teste.\n")
    
    # Descomente as linhas abaixo e insira um token válido se quiser testar:
    # access_token = "SEU_TOKEN_AQUI"
    # params = {"q": "fone bluetooth", "limit": 5}
    # headers = {
    #     "Authorization": f"Bearer {access_token}",
    #     "User-Agent": "MLIntelligence/1.0"
    # }
    # resp = requests.get(f"{ML_API}/sites/MLB/search", params=params, headers=headers, timeout=15)
    # print(f"Status: {resp.status_code}")
    # print(f"Body: {resp.text[:300]}")


def check_credentials():
    """Verifica se as credenciais ML estão configuradas"""
    print("\n" + "="*60)
    print("VERIFICAÇÃO: Credenciais ML no ambiente")
    print("="*60)
    
    print(f"\nML_APP_ID: {'✓ Configurado' if ML_APP_ID else '❌ AUSENTE'}")
    if ML_APP_ID:
        print(f"   Valor: {ML_APP_ID[:10]}...{ML_APP_ID[-5:] if len(ML_APP_ID) > 15 else ''}")
    
    print(f"\nML_SECRET: {'✓ Configurado' if ML_SECRET else '❌ AUSENTE'}")
    if ML_SECRET:
        print(f"   Valor: {ML_SECRET[:10]}...******")


if __name__ == "__main__":
    print("\n🔍 DIAGNÓSTICO: Pesquisa de Concorrência Mercado Livre")
    print("="*60)
    
    check_credentials()
    test_search_no_token()
    test_search_with_mock_token()
    
    print("\n" + "="*60)
    print("CONCLUSÃO:")
    print("="*60)
    print("""
Se o TESTE 1 retornou:
  - 200 OK: A busca pública funciona! Problema pode ser na lógica do backend.
  - 403 Forbidden: App não certificado (esperado). Use "adicionar por link".
  - 404 Not Found: URL incorreta ou site_id inválido.
  - 429 Too Many Requests: Rate limit. Aguarde alguns minutos.
  - 500 Server Error: Problema temporário na API ML.
  
Próximo passo: Aplicar correção no código para informar o erro real ao frontend.
    """)
