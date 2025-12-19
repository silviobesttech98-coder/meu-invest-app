from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from bcb import sgs 

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
    resposta = supabase.table("transacoes").select("*").execute()
    carteira = resposta.data
    
    for acao in carteira:
        ticker = acao['ticker'].strip()
        if not ticker.endswith(".SA"):
            ticker_yahoo = f"{ticker}.SA"
        else:
            ticker_yahoo = ticker
            
        try:
            dados_mercado = yf.Ticker(ticker_yahoo)
            historico = dados_mercado.history(period="1d")
            
            if not historico.empty:
                preco_atual = historico['Close'].iloc[-1]
                acao['preco_atual'] = round(preco_atual, 2)
            else:
                acao['preco_atual'] = acao['preco']
                
        except Exception:
            acao['preco_atual'] = acao['preco']
            
        acao['lucro_total'] = (acao['preco_atual'] - acao['preco']) * acao['quantidade']
        
    return carteira

@app.post("/comprar")
def comprar_acao(compra: Compra):
    nova_transacao = {
        "ticker": compra.ticker.upper().strip(),
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

        return {"labels": datas[::3], "data": precos[::3]}
    except Exception as e:
        return {"erro": str(e)}

@app.get("/historico")
def obter_historico_carteira():
    try:
        response = supabase.table("transacoes").select("*").execute()
        transacoes = response.data
        if not transacoes:
            return []

        dias_atras = 20
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        tickers = [t['ticker'].strip() + ".SA" for t in transacoes] 
        
        try:
            dados_mercado = yf.download(tickers + ['^BVSP'], start=data_inicio, progress=False)['Close']
        except Exception:
            return [] 

        try:
            cdi = sgs.get({'CDI': 12}, last=dias_atras)
        except Exception:
            cdi = pd.DataFrame() 

        if dados_mercado.empty:
            return []

        historico_final = []
        datas = dados_mercado.index
        base_cdi = 100
        primeiro_dia = True
        val_ref_carteira = 1
        val_ref_ibov = 1

        for data in datas:
            data_str = data.strftime('%d/%m')
            valor_dia_carteira = 0
            for t in transacoes:
                ticker_limpo = t['ticker'].strip() + ".SA"
                qtd = t['quantidade']
                if ticker_limpo in dados_mercado.columns:
                    preco = dados_mercado.loc[data, ticker_limpo]
                    if pd.notna(preco):
                        valor_dia_carteira += preco * qtd
            
            val_ibov = dados_mercado.loc[data, '^BVSP'] if '^BVSP' in dados_mercado.columns else 0
            taxa_cdi_dia = 0
            try:
                taxa_cdi_dia = cdi.loc[data.strftime('%Y-%m-%d')]['CDI']
            except:
                pass 
            
            if primeiro_dia:
                val_ref_carteira = valor_dia_carteira if valor_dia_carteira > 0 else 1
                val_ref_ibov = val_ibov if val_ibov > 0 else 1
                primeiro_dia = False
            
            rent_carteira = ((valor_dia_carteira / val_ref_carteira) - 1) * 100
            rent_ibov = ((val_ibov / val_ref_ibov) - 1) * 100
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
        return {"erro": str(e)}

# 👇👇👇 ROTA NOVA: MÁQUINA DE DIVIDENDOS 👇👇👇
@app.get("/proventos")
def obter_proventos():
    try:
        response = supabase.table("transacoes").select("*").execute()
        carteira = response.data
        if not carteira:
            return {"labels": [], "data": []}

        # Dicionário para somar dividendos por mês (Chave: "2025-01", Valor: 50.00)
        proventos_por_mes = {}

        for acao in carteira:
            ticker = acao['ticker'].strip()
            qtd = acao['quantidade']
            if not ticker.endswith(".SA"):
                ticker = f"{ticker}.SA"

            try:
                # Baixa dividendos dos últimos 12 meses
                ticker_obj = yf.Ticker(ticker)
                divs = ticker_obj.dividends
                
                # Filtra último ano
                data_limite = datetime.now() - timedelta(days=365)
                # O índice do Pandas já é data, então filtramos direto
                divs_ano = divs[divs.index >= data_limite.replace(tzinfo=divs.index.dtype.tz)]

                for data, valor in divs_ano.items():
                    # Formata a data para "Mês/Ano" (ex: 12/23)
                    mes_chave = data.strftime("%m/%y")
                    valor_total_recebido = valor * qtd
                    
                    if mes_chave in proventos_por_mes:
                        proventos_por_mes[mes_chave] += valor_total_recebido
                    else:
                        proventos_por_mes[mes_chave] = valor_total_recebido
            
            except Exception as e:
                print(f"Erro ao pegar proventos de {ticker}: {e}")
                continue

        # Ordena cronologicamente (Pandas ajuda, mas vamos simplificar aqui)
        # Transformar em listas para o Gráfico
        # Ordenamos pelo ano/mês "cru" para ficar na ordem certa
        sorted_keys = sorted(proventos_por_mes.keys(), key=lambda x: datetime.strptime(x, "%m/%y"))
        
        labels = sorted_keys
        data = [round(proventos_por_mes[k], 2) for k in sorted_keys]

        return {"labels": labels, "data": data}

    except Exception as e:
        return {"erro": str(e)}