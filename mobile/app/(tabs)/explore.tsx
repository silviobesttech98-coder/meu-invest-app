import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';

export default function InvestirScreen() {
  const [ticker, setTicker] = useState('');
  const [preco, setPreco] = useState('');
  const [quantidade, setQuantidade] = useState('');
  const [loading, setLoading] = useState(false);

  // 👇 COLOQUE SEU IP AQUI DE NOVO 👇
  const API_URL = "http://192.168.1.124:8000/comprar";

  async function handleInvestir() {
    if (!ticker || !preco || !quantidade) {
      Alert.alert("Opa!", "Preencha todos os campos.");
      return;
    }

    setLoading(true);

    try {
      const resposta = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(), // Força letra maiúscula
          preco: parseFloat(preco),     // Converte texto para número decimal
          quantidade: parseInt(quantidade), // Converte texto para número inteiro
          tipo: "compra"
        }),
      });

      if (resposta.ok) {
        Alert.alert("Sucesso! 🚀", `Você comprou ${quantidade} cotas de ${ticker}`);
        // Limpar os campos
        setTicker('');
        setPreco('');
        setQuantidade('');
      } else {
        Alert.alert("Erro", "Não foi possível salvar no banco de dados.");
      }
    } catch (error) {
      Alert.alert("Erro de Conexão", "Verifique se o servidor backend está rodando.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>➕ Novo Aporte</Text>

      <View style={styles.inputContainer}>
        <Text style={styles.label}>Ativo (Ticker)</Text>
        <TextInput 
          style={styles.input} 
          placeholder="Ex: PETR4" 
          placeholderTextColor="#666"
          value={ticker}
          onChangeText={setTicker}
          autoCapitalize="characters"
        />
      </View>

      <View style={styles.row}>
        <View style={[styles.inputContainer, { flex: 1, marginRight: 10 }]}>
          <Text style={styles.label}>Preço (R$)</Text>
          <TextInput 
            style={styles.input} 
            placeholder="0.00" 
            placeholderTextColor="#666"
            keyboardType="numeric"
            value={preco}
            onChangeText={setPreco}
          />
        </View>

        <View style={[styles.inputContainer, { flex: 1 }]}>
          <Text style={styles.label}>Quantidade</Text>
          <TextInput 
            style={styles.input} 
            placeholder="0" 
            placeholderTextColor="#666"
            keyboardType="numeric"
            value={quantidade}
            onChangeText={setQuantidade}
          />
        </View>
      </View>

      <TouchableOpacity 
        style={styles.botao} 
        onPress={handleInvestir}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#000" />
        ) : (
          <Text style={styles.textoBotao}>CONFIRMAR COMPRA</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
    padding: 20,
    justifyContent: 'center',
  },
  titulo: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#00ff00',
    marginBottom: 30,
    textAlign: 'center',
  },
  inputContainer: {
    marginBottom: 20,
  },
  label: {
    color: '#fff',
    marginBottom: 8,
    fontSize: 16,
    fontWeight: 'bold',
  },
  input: {
    backgroundColor: '#1e1e1e',
    color: '#fff',
    padding: 15,
    borderRadius: 10,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  botao: {
    backgroundColor: '#00ff00',
    padding: 15,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 20,
  },
  textoBotao: {
    color: '#000',
    fontSize: 18,
    fontWeight: 'bold',
  },
});