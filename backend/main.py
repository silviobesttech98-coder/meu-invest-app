from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from bcb import sgs # Para pegar o CDI

app = FastAPI()

# --- CONFIGURAÇÃO DO SUPABASE ---
URL_SUPABASE = "https://xknyjejaygbpkgcxotpw.supabase.co"
CHAVE_SUPABASE = "sb_secret_nkf0QL6Whoz7ymg9_OSiPQ_kPK6EDRJ"
supabase: Client = create_client(URL_SUPABASE, CHAVE_SUPABASE)

# --- MODELOS DE DADOS ---
class Compra(BaseModel):
    ticker: str
    preco: float
    quantidade: int
    tipo: str = "compra"

class AtualizacaoTransacao(BaseModel):
    novo_preco: float | None = None
    nova_quantidade: int | None = None

# --- ROTAS ---

@app.get("/")
def home():
    return {"mensagem": "API conectada ao Supabase! 🚀"}

@app.get("/minha-carteira")
def listar_carteira():
    # 1. Pega os dados brutos do Supabase
    resposta = supabase.table("transacoes").select("*").execute()
    carteira = resposta.data
    
    # 2. Vamos enriquecer cada item com o preço atual
    for acao in carteira:
        ticker = acao['ticker'].strip() # Remove espaços vazios acidentais
        # Adiciona o .SA se não tiver
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
                acao['preco_atual'] = acao['preco']
                
        except Exception:
            acao['preco_atual'] = acao['preco']
            
        # 3. Calcula o lucro/prejuízo por ação
        acao['lucro_total'] = (acao['preco_atual'] - acao['preco']) * acao['quantidade']
        
    return carteira

@app.post("/comprar")
def comprar_acao(compra: Compra):
    nova_transacao = {
        "ticker": compra.ticker.upper().strip(), # Salva sempre maiúsculo e sem espaço
        "preco": compra.preco,
        "quantidade": compra.quantidade,
        "tipo": compra.tipo
    }
    try:
        supabase.table("transacoes").insert(nova_transacao).execute()
        return {"mensagem": "Salvo no banco com sucesso!", "dados": nova_transacao}
    except Exception as e:
        return {"erro": "Falha ao salvar no banco", "detalhes": str(e)}

@app.get("/cotacao/{ticker}")
def ler_cotacao(ticker: str):
    try:
        acao = yf.Ticker(ticker.strip())
        preco_atual = acao.history(period="1d")['Close'].iloc[-1]
        return {"ativo": ticker, "preco": round(preco_atual, 2)}
    except:
        return {"erro": "Ativo não encontrado"}

@app.delete("/transacoes/{id_transacao}")
def deletar_transacao(id_transacao: int):
    try:
        supabase.table("transacoes").delete().eq("id", id_transacao).execute()
        return {"mensagem": "Deletado com sucesso!"}
    except Exception as e:
        return {"erro": "Erro ao deletar", "detalhes": str(e)}

@app.put("/transacoes/{id_transacao}")
def atualizar_transacao(id_transacao: int, dados: AtualizacaoTransacao):
    try:
        update_data = {}
        if dados.novo_preco is not None:
            update_data['preco'] = dados.novo_preco
        if dados.nova_quantidade is not None:
            update_data['quantidade'] = dados.nova_quantidade
            
        if not update_data:
            return {"erro": "Nenhum dado para atualizar"}

        supabase.table("transacoes").update(update_data).eq("id", id_transacao).execute()
        return {"mensagem": "Atualizado com sucesso!"}
    except Exception as e:
        return {"erro": "Erro ao atualizar", "detalhes": str(e)}

# Rota individual (Detalhes do App)
@app.get("/historico/{ticker}")
def historico_individual(ticker: str):
    try:
        ticker = ticker.strip()
        if not ticker.endswith(".SA"):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        acao = yf.Ticker(ticker_yahoo)
        historico = acao.history(period="1mo")
        
        if historico.empty:
             return {"erro": "Ticker não encontrado"}

        precos = historico['Close'].tolist()
        datas = [data.strftime("%d/%m") for data in historico.index]

        return {
            "labels": datas[::3], 
            "data": precos[::3]
        }
    except Exception as e:
        return {"erro": str(e)}

# 👇 ROTA DO GRÁFICO COMPARATIVO (CORRIGIDA E BLINDADA) 👇
@app.get("/historico")
def obter_historico_carteira():
    try:
        # 1. Pega sua carteira
        response = supabase.table("transacoes").select("*").execute()
        transacoes = response.data
        if not transacoes:
            return []

        # 2. FIX: Reduzido para 20 dias (limite atual da API pública do BC)
        dias_atras = 20
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        
        # 3. FIX: .strip() para remover espaços vazios que quebram o Yahoo
        tickers = [t['ticker'].strip() + ".SA" for t in transacoes] 
        
        # 4. Busca Yahoo com proteção
        try:
            # Baixa dados de fechamento ('Close')
            dados_mercado = yf.download(tickers + ['^BVSP'], start=data_inicio, progress=False)['Close']
        except Exception as e:
            print(f"Erro Yahoo: {e}")
            return [] 

        # 5. Busca CDI com proteção
        try:
            cdi = sgs.get({'CDI': 12}, last=dias_atras)
        except Exception as e:
            print(f"Erro BCB: {e}")
            cdi = pd.DataFrame() # Cria vazio se der erro pra não travar tudo

        if dados_mercado.empty:
            return []

        # 6. Processamento Matemático
        historico_final = []
        datas = dados_mercado.index
        base_cdi = 100
        
        primeiro_dia = True
        val_ref_carteira = 1
        val_ref_ibov = 1

        for data in datas:
            data_str = data.strftime('%d/%m')
            
            # --- Carteira ---
            valor_dia_carteira = 0
            for t in transacoes:
                ticker_limpo = t['ticker'].strip() + ".SA"
                qtd = t['quantidade']
                
                # Verifica se a ação existe nas colunas baixadas pelo Yahoo
                if ticker_limpo in dados_mercado.columns:
                    preco = dados_mercado.loc[data, ticker_limpo]
                    if pd.notna(preco):
                        valor_dia_carteira += preco * qtd
            
            # --- Ibovespa ---
            val_ibov = dados_mercado.loc[data, '^BVSP'] if '^BVSP' in dados_mercado.columns else 0
            
            # --- CDI ---
            taxa_cdi_dia = 0
            try:
                taxa_cdi_dia = cdi.loc[data.strftime('%Y-%m-%d')]['CDI']
            except:
                pass # Se não tiver CDI no dia (feriado/fds), segue o baile
            
            # Define o valor inicial (Marco Zero)
            if primeiro_dia:
                val_ref_carteira = valor_dia_carteira if valor_dia_carteira > 0 else 1
                val_ref_ibov = val_ibov if val_ibov > 0 else 1
                primeiro_dia = False
            
            # Cálculos de Rentabilidade (%)
            rent_carteira = ((valor_dia_carteira / val_ref_carteira) - 1) * 100
            rent_ibov = ((val_ibov / val_ref_ibov) - 1) * 100
            
            # CDI é juros compostos
            base_cdi = base_cdi * (1 + (taxa_cdi_dia/100))
            rent_cdi = base_cdi - 100

            historico_final.append({
                "data": data_str,
                "carteira": round(rent_carteira, 2),
                "ibovespa": round(rent_ibov, 2),
                "cdi": round(rent_cdi, 2)
            })
            
        return historico_final

    except Exception as e:
        print(f"Erro Geral: {e}")
        return {"erro": str(e)}