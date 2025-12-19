import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

export default function EditarScreen() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  
  const [preco, setPreco] = useState('');
  const [quantidade, setQuantidade] = useState('');
  const [loading, setLoading] = useState(false);

  // 👇 URL DA NUVEM (CONFIRA SE ESTÁ IGUAL)
  const BASE_URL = "https://meu-invest-app.onrender.com";

  const salvarEdicao = async () => {
    if (!preco && !quantidade) {
      Alert.alert("Atenção", "Preencha pelo menos um campo para editar.");
      return;
    }

    setLoading(true);
    try {
      const corpoRequisicao: any = {};
      if (preco) corpoRequisicao.novo_preco = parseFloat(preco.replace(',', '.'));
      if (quantidade) corpoRequisicao.nova_quantidade = parseInt(quantidade);

      const response = await fetch(`${BASE_URL}/transacoes/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpoRequisicao),
      });

      if (response.ok) {
        Alert.alert("Sucesso", "Atualizado com sucesso!");
        router.back(); // Volta para a tela inicial
      } else {
        Alert.alert("Erro", "Não foi possível atualizar.");
      }
    } catch (error) {
      Alert.alert("Erro", "Falha na conexão.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>Editar Investimento</Text>
      
      <Text style={styles.label}>Novo Preço (R$)</Text>
      <TextInput 
        style={styles.input} 
        placeholder="Ex: 32.50" 
        placeholderTextColor="#666"
        keyboardType="numeric"
        value={preco}
        onChangeText={setPreco}
      />

      <Text style={styles.label}>Nova Quantidade</Text>
      <TextInput 
        style={styles.input} 
        placeholder="Ex: 100" 
        placeholderTextColor="#666"
        keyboardType="numeric"
        value={quantidade}
        onChangeText={setQuantidade}
      />

      <TouchableOpacity style={styles.botao} onPress={salvarEdicao} disabled={loading}>
        {loading ? (
          <ActivityIndicator color="#000" />
        ) : (
          <Text style={styles.textoBotao}>Salvar Alterações</Text>
        )}
      </TouchableOpacity>

      <TouchableOpacity style={styles.botaoVoltar} onPress={() => router.back()}>
        <Text style={styles.textoVoltar}>Cancelar</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#121212', padding: 20, justifyContent: 'center' },
  titulo: { color: '#fff', fontSize: 24, fontWeight: 'bold', marginBottom: 30, textAlign: 'center' },
  label: { color: '#aaa', marginBottom: 5, marginLeft: 5 },
  input: { 
    backgroundColor: '#1e1e1e', 
    color: '#fff', 
    padding: 15, 
    borderRadius: 10, 
    marginBottom: 20, 
    borderWidth: 1, 
    borderColor: '#333' 
  },
  botao: { backgroundColor: '#00ff00', padding: 15, borderRadius: 10, alignItems: 'center', marginTop: 10 },
  textoBotao: { color: '#000', fontWeight: 'bold', fontSize: 16 },
  botaoVoltar: { marginTop: 15, alignItems: 'center' },
  textoVoltar: { color: '#aaa' }
});