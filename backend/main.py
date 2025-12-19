from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client # Importando o conector
import yfinance as yf
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
from bcb import sgs # Para pegar o CDI

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
        # 👇 COLE ISSO NO FINAL DO ARQUIVO main.py 👇

# Classe para validar os dados da edição
class AtualizacaoTransacao(BaseModel):
    novo_preco: float | None = None
    nova_quantidade: int | None = None

# Rota para EDITAR (Atualizar) uma transação
@app.put("/transacoes/{id_transacao}")
def atualizar_transacao(id_transacao: int, dados: AtualizacaoTransacao):
    try:
        update_data = {}
        # Só atualiza o que foi enviado (se enviou só preço, muda só preço)
        if dados.novo_preco is not None:
            update_data['preco'] = dados.novo_preco
        if dados.nova_quantidade is not None:
            update_data['quantidade'] = dados.nova_quantidade
            
        if not update_data:
            return {"erro": "Nenhum dado para atualizar"}

        # Manda o Supabase atualizar
        supabase.table("transacoes").update(update_data).eq("id", id_transacao).execute()
        return {"mensagem": "Atualizado com sucesso!"}
    except Exception as e:
        return {"erro": "Erro ao atualizar", "detalhes": str(e)}
        # 👇 ROTA DE ELITE: HISTÓRICO COMPARATIVO 👇
@app.get("/historico")
def obter_historico():
    try:
        # 1. Pega sua carteira atual
        response = supabase.table("transacoes").select("*").execute()
        transacoes = response.data
        if not transacoes:
            return []

        # 2. Define o período (Ex: Últimos 30 dias)
        dias_atras = 30
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        tickers = [t['ticker'] + ".SA" for t in transacoes] # Adiciona .SA para o Yahoo
        
        # 3. Baixa histórico das SUAS ações + IBOVESPA (^BVSP)
        dados_mercado = yf.download(tickers + ['^BVSP'], start=data_inicio, progress=False)['Close']
        
        # 4. Baixa histórico do CDI (Código 11 do Banco Central)
        cdi = sgs.get({'CDI': 12}, last=dias_atras) # Taxa diária %

        # 5. Processa dia a dia (Matemática Financeira)
        historico_final = []
        
        # Normaliza as datas para iterar
        datas = dados_mercado.index
        
        # Valor inicial base para índices (base 100 para comparação visual)
        base_cdi = 100
        base_ibov = 100
        base_carteira = 100
        
        primeiro_dia = True

        for data in datas:
            data_str = data.strftime('%d/%m')
            
            # --- A) CALCULA SUA CARTEIRA ---
            valor_dia_carteira = 0
            for t in transacoes:
                ticker_sa = t['ticker'] + ".SA"
                qtd = t['quantidade']
                # Se tiver cotação naquele dia, soma. Se não (feriado), pega anterior
                if ticker_sa in dados_mercado.columns:
                    preco = dados_mercado.loc[data, ticker_sa]
                    if pd.notna(preco):
                        valor_dia_carteira += preco * qtd
            
            # --- B) CALCULA IBOVESPA (Índice Base 100) ---
            val_ibov = dados_mercado.loc[data, '^BVSP'] if '^BVSP' in dados_mercado.columns else None
            
            # --- C) CALCULA CDI (Acumulado) ---
            # CDI do BC vem como taxa diária (ex: 0.04%). Precisamos compor.
            taxa_cdi_dia = 0
            # Tenta achar a taxa CDI para a data (convertendo formato se necessário)
            try:
                # Ajuste técnico simples para datas
                taxa_cdi_dia = cdi.loc[data.strftime('%Y-%m-%d')]['CDI']
            except:
                pass
            
            # Lógica de Indexação (Transformar tudo em %)
            if primeiro_dia:
                val_ref_carteira = valor_dia_carteira
                val_ref_ibov = val_ibov
                primeiro_dia = False
            
            # Variação Percentual Acumulada
            rent_carteira = ((valor_dia_carteira / val_ref_carteira) - 1) * 100 if val_ref_carteira else 0
            rent_ibov = ((val_ibov / val_ref_ibov) - 1) * 100 if val_ref_ibov and val_ref_ibov else 0
            
            # CDI acumula juros sobre juros
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
        print(f"Erro: {e}")
        return {"erro": str(e)}