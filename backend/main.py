from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client # Importando o conector
import yfinance as yf

app = FastAPI()

# --- CONFIGURAÇÃO DO SUPABASE ---
# ⚠️ SUBSTITUA PELOS SEUS DADOS DO SUPABASE (Mantenha as aspas!)
URL_SUPABASE = "https://xknyjejaygbpkgcxotpw.supabase.co"
CHAVE_SUPABASE = "sb_secret_nkf0QL6Whoz7ymg9_OSiPQ_kPK6EDRJ"
# Conectando...
supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)

class Compra(BaseModel):
    ticker: str
    preco: float
    quantidade: int
    tipo: str = "compra" # Padrão é compra

@app.get("/")
def home():
    return {"mensagem": "API conectada ao Supabase! 🚀"}

# Rota para ler do banco de dados real
# ⚠️ Substitua a função 'listar_carteira' antiga por esta NOVA:

@app.get("/minha-carteira")
def listar_carteira():
    # 1. Pega os dados brutos do Supabase
    resposta = supabase.table("transacoes").select("*").execute()
    carteira = resposta.data
    
    # 2. Vamos enriquecer cada item com o preço atual
    for acao in carteira:
        ticker = acao['ticker']
        # Adiciona o .SA se não tiver (padrão brasileiro no Yahoo)
        if not ticker.endswith(".SA"):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        try:
            # Busca a cotação online
            dados_mercado = yf.Ticker(ticker_yahoo)
            historico = dados_mercado.history(period="1d")
            
            if not historico.empty:
                preco_atual = historico['Close'].iloc[-1]
                acao['preco_atual'] = round(preco_atual, 2)
            else:
                # Se não achar (ex: TESTE3), usa o preço de compra mesmo
                acao['preco_atual'] = acao['preco']
                
        except Exception:
            # Se der erro na internet, mantém o preço original pra não travar
            acao['preco_atual'] = acao['preco']
            
        # 3. Calcula o lucro/prejuízo por ação
        acao['lucro_total'] = (acao['preco_atual'] - acao['preco']) * acao['quantidade']
        
    return carteira

# Rota para salvar no banco de dados
@app.post("/comprar")
def comprar_acao(compra: Compra):
    
    # Prepara o dado para enviar
    nova_transacao = {
        "ticker": compra.ticker,
        "preco": compra.preco,
        "quantidade": compra.quantidade,
        "tipo": compra.tipo
    }
    
    try:
        # Envia para o Supabase!
        supabase.table("transacoes").insert(nova_transacao).execute()
        return {"mensagem": "Salvo no banco com sucesso!", "dados": nova_transacao}
    except Exception as e:
        return {"erro": "Falha ao salvar no banco", "detalhes": str(e)}

# Rota de cotação (continua igual)
@app.get("/cotacao/{ticker}")
def ler_cotacao(ticker: str):
    try:
        acao = yf.Ticker(ticker)
        preco_atual = acao.history(period="1d")['Close'].iloc[-1]
        return {"ativo": ticker, "preco": round(preco_atual, 2)}
    except:
        return {"erro": "Ativo não encontrado"}# Rota para DELETAR uma transação
@app.delete("/transacoes/{id_transacao}")
def deletar_transacao(id_transacao: int):
    try:
        # Manda o Supabase apagar onde o id for igual ao solicitado
        supabase.table("transacoes").delete().eq("id", id_transacao).execute()
        return {"mensagem": "Deletado com sucesso!"}
    except Exception as e:
        return {"erro": "Erro ao deletar", "detalhes": str(e)}# Rota para pegar o histórico de 1 mês (para o gráfico)
@app.get("/historico/{ticker}")
def historico_mensal(ticker: str):
    try:
        # Garante o .SA
        if not ticker.endswith(".SA"):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        # Pega 1 mês de dados
        acao = yf.Ticker(ticker_yahoo)
        historico = acao.history(period="1mo")
        
        # Se vier vazio (ex: ticker errado), retorna erro
        if historico.empty:
             return {"erro": "Ticker não encontrado"}

        # Prepara os dados para o gráfico do App
        # Vamos pegar apenas os preços de fechamento ('Close')
        precos = historico['Close'].tolist()
        
        # Vamos pegar as datas formatadas (Dia/Mês)
        datas = [data.strftime("%d/%m") for data in historico.index]

        # Para o gráfico não ficar gigante no celular, vamos pegar apenas 1 a cada 3 dias
        # Isso é um truque de performance visual
        return {
            "labels": datas[::3], 
            "data": precos[::3]
        }
    except Exception as e:
        return {"erro": str(e)}