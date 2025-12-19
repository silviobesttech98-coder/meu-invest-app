import yfinance as yf

# Buscando dados da Petrobras
acao = yf.Ticker("PETR4.SA")

# Pega o histórico do último dia
dados = acao.history(period="1d")

# Pega apenas o preço de fechamento
preco = dados['Close'].iloc[-1]

print(f"O preço atual da PETR4 é: R$ {preco:.2f}")