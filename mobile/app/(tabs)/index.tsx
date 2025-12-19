import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, Text, View, FlatList, ActivityIndicator, TouchableOpacity, Alert, Dimensions } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router'; // <--- Importamos useRouter
import { Ionicons } from '@expo/vector-icons';
import { PieChart } from "react-native-chart-kit";

export default function HomeScreen() {
  const [saldo, setSaldo] = useState([]);
  const [loading, setLoading] = useState(true);
  const [patrimonioTotal, setPatrimonioTotal] = useState(0);
  
  const router = useRouter(); // <--- Instanciamos o roteador

  // 👇 CONFIRA SEU IP 👇
  const BASE_URL = "http://192.168.1.124:8000"; 

  const carregarDados = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/minha-carteira`);
      const json = await response.json();
      setSaldo(json);

      const total = json.reduce((acumulador, item) => {
        const precoConsiderado = item.preco_atual || item.preco;
        return acumulador + (precoConsiderado * item.quantidade);
      }, 0);
      
      setPatrimonioTotal(total);

    } catch (error) {
      console.error("Erro ao buscar:", error);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      carregarDados();
    }, [])
  );

  const deletarItem = (id, ticker) => {
    Alert.alert("Excluir", `Apagar ${ticker}?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Apagar", style: 'destructive', onPress: async () => {
          try {
            await fetch(`${BASE_URL}/transacoes/${id}`, { method: 'DELETE' });
            carregarDados();
          } catch (error) { Alert.alert("Erro ao deletar"); }
      }}
    ]);
  };

  const formatarMoeda = (valor) => {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const coresGrafico = ['#FF005C', '#FFBD00', '#00B8FF', '#00FF9F', '#8C52FF', '#FF6D00'];
  const dadosGrafico = saldo.map((item, index) => {
    const valorTotalItem = (item.preco_atual || item.preco) * item.quantidade;
    return {
      name: item.ticker,
      population: valorTotalItem,
      color: coresGrafico[index % coresGrafico.length],
      legendFontColor: "#fff",
      legendFontSize: 12
    };
  });

  return (
    <View style={styles.container}>
      
      <View style={styles.header}>
        <Text style={styles.labelHeader}>Patrimônio Total</Text>
        <Text style={styles.valorTotal}>{formatarMoeda(patrimonioTotal)}</Text>
      </View>

      {patrimonioTotal > 0 && (
        <View style={{ alignItems: 'center', marginBottom: 20 }}>
          <PieChart
            data={dadosGrafico}
            width={Dimensions.get("window").width - 20}
            height={220}
            chartConfig={{ color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})` }}
            accessor={"population"}
            backgroundColor={"transparent"}
            paddingLeft={"15"}
            center={[0, 0]}
            absolute
          />
        </View>
      )}

      <Text style={styles.subtitulo}>Meus Ativos</Text>

      {loading ? (
        <ActivityIndicator size="large" color="#00ff00" />
      ) : (
        <FlatList
          data={saldo}
          keyExtractor={(item) => String(item.id)} 
          renderItem={({ item }) => {
            const isLucro = item.lucro_total >= 0;
            const corLucro = isLucro ? '#00ff00' : '#ff4444'; 
            const sinal = isLucro ? '+' : ''; 

            return (
              // 🔽 AGORA O CARD É CLICÁVEL 🔽
              <TouchableOpacity 
                activeOpacity={0.7}
                onPress={() => router.push(`/detalhes/${item.ticker}`)} // Navega para a nova tela
              >
                <View style={styles.card}>
                  <View>
                    <Text style={styles.ativo}>{item.ticker}</Text>
                    <Text style={styles.detalhe}>{item.quantidade} un. • Médio: {formatarMoeda(item.preco)}</Text>
                  </View>
                  
                  <View style={{alignItems: 'flex-end'}}>
                    <Text style={styles.valorItem}>
                        {formatarMoeda((item.preco_atual || item.preco) * item.quantidade)}
                    </Text>
                    <Text style={{color: corLucro, fontSize: 14, fontWeight: 'bold'}}>
                        {sinal}{formatarMoeda(item.lucro_total || 0)}
                    </Text>
                    
                    {/* Botão de Lixeira (com stopPropagation para não abrir o detalhe ao clicar na lixeira) */}
                    <TouchableOpacity onPress={(e) => {
                        e.stopPropagation(); // Impede o clique de subir para o card
                        deletarItem(item.id, item.ticker);
                    }} style={{marginTop: 5}}>
                        <Ionicons name="trash-outline" size={20} color="#ff4444" />
                    </TouchableOpacity>
                  </View>
                </View>
              </TouchableOpacity>
            );
          }}
          ListEmptyComponent={<Text style={styles.vazio}>Nenhum investimento ainda.</Text>}
          contentContainerStyle={{ paddingBottom: 100 }}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
    paddingTop: 50,
    paddingHorizontal: 10,
  },
  header: {
    alignItems: 'center',
    marginBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
    paddingBottom: 20
  },
  labelHeader: {
    color: '#aaa',
    fontSize: 14,
    textTransform: 'uppercase',
  },
  valorTotal: {
    color: '#fff',
    fontSize: 32,
    fontWeight: 'bold',
    textShadowColor: 'rgba(0, 255, 0, 0.5)',
    textShadowOffset: {width: 0, height: 0},
    textShadowRadius: 10
  },
  subtitulo: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    marginLeft: 10
  },
  card: {
    backgroundColor: '#1e1e1e',
    padding: 15,
    borderRadius: 12,
    marginBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ativo: { color: 'white', fontSize: 18, fontWeight: 'bold' },
  detalhe: { color: '#888', fontSize: 12 },
  valorItem: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  vazio: { color: '#666', textAlign: 'center', marginTop: 50 }
});