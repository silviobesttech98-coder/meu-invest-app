import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, Text, View, FlatList, ActivityIndicator, TouchableOpacity, Alert, Dimensions, ScrollView } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { PieChart, LineChart } from "react-native-chart-kit"; // Importando o LineChart

export default function HomeScreen() {
  const [saldo, setSaldo] = useState([]);
  const [historico, setHistorico] = useState([]); // Novo estado para o gráfico de linha
  const [loading, setLoading] = useState(true);
  const [patrimonioTotal, setPatrimonioTotal] = useState(0);
  
  const router = useRouter(); 

  // 👇 SEU SERVIDOR NA NUVEM
  const BASE_URL = "https://meu-invest-app.onrender.com"; 

  const carregarDados = async () => {
    setLoading(true);
    try {
      // 1. Busca carteira e saldo
      const response = await fetch(`${BASE_URL}/minha-carteira`);
      const json = await response.json();
      setSaldo(json);

      const total = json.reduce((acumulador, item) => {
        const precoConsiderado = item.preco_atual || item.preco;
        return acumulador + (precoConsiderado * item.quantidade);
      }, 0);
      setPatrimonioTotal(total);

      // 2. Busca histórico para o gráfico (NOVO)
      // Fazemos isso em paralelo ou depois, mas sem travar a tela se der erro
      try {
        const respHist = await fetch(`${BASE_URL}/historico`);
        const jsonHist = await respHist.json();
        if (Array.isArray(jsonHist)) {
            setHistorico(jsonHist);
        }
      } catch (errHist) {
        console.log("Erro ao buscar histórico (pode ser timeout do Render):", errHist);
      }

    } catch (error) {
      console.error("Erro geral:", error);
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
  const dadosPizza = saldo.map((item, index) => {
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

      {loading ? (
        <ActivityIndicator size="large" color="#00ff00" style={{marginTop: 50}} />
      ) : (
        <FlatList
          ListHeaderComponent={
            <>
                {/* 1. GRÁFICO DE PIZZA (Distribuição) */}
                {patrimonioTotal > 0 && (
                    <View style={{ alignItems: 'center', marginBottom: 10 }}>
                    <PieChart
                        data={dadosPizza}
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

                {/* 2. GRÁFICO DE LINHA (Rentabilidade vs Ibovespa) */}
                {historico.length > 0 && (
                    <View style={{ marginVertical: 10, paddingHorizontal: 5 }}>
                    <Text style={styles.tituloGrafico}>Rentabilidade (30 dias)</Text>
                    <Text style={styles.legendaGrafico}>🟢 Você vs ⚪ Ibovespa</Text>
                    
                    <LineChart
                        data={{
                        labels: historico.map(h => h.data).filter((_, i) => i % 5 === 0), // Mostra 1 data a cada 5
                        datasets: [
                            {
                                data: historico.map(h => h.carteira),
                                color: (opacity = 1) => `rgba(0, 255, 0, ${opacity})`, // Verde (Você)
                                strokeWidth: 3
                            },
                            {
                                data: historico.map(h => h.ibovespa),
                                color: (opacity = 1) => `rgba(200, 200, 200, ${opacity})`, // Cinza (Ibovespa)
                                strokeWidth: 2,
                                withDots: false, // Linha lisa para o benchmark
                            }
                        ],
                        }}
                        width={Dimensions.get("window").width - 20} 
                        height={220}
                        yAxisSuffix="%"
                        chartConfig={{
                        backgroundColor: "#1e1e1e",
                        backgroundGradientFrom: "#1e1e1e",
                        backgroundGradientTo: "#252525",
                        decimalPlaces: 1,
                        color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
                        labelColor: (opacity = 1) => `rgba(180, 180, 180, ${opacity})`,
                        style: { borderRadius: 16 },
                        propsForDots: { r: "4", strokeWidth: "2", stroke: "#00ff00" },
                        propsForBackgroundLines: { strokeDasharray: "" } // Linhas solidas no fundo
                        }}
                        bezier // Curvas suaves
                        style={{ marginVertical: 8, borderRadius: 16 }}
                    />
                    </View>
                )}
                
                <Text style={styles.subtitulo}>Meus Ativos</Text>
            </>
          }
          data={saldo}
          keyExtractor={(item) => String(item.id)} 
          renderItem={({ item }) => {
            const precoAtual = item.preco_atual || item.preco;
            const lucroReais = (precoAtual - item.preco) * item.quantidade;
            const isLucro = lucroReais >= 0;
            const corLucro = isLucro ? '#00ff00' : '#ff4444'; 
            const sinal = isLucro ? '+' : ''; 
            const rentabilidade = item.preco > 0 
              ? ((precoAtual - item.preco) / item.preco) * 100 
              : 0;

            return (
              <TouchableOpacity 
                activeOpacity={0.7}
                onPress={() => router.push(`/detalhes/${item.ticker}`)}
              >
                <View style={styles.card}>
                  <View>
                    <Text style={styles.ativo}>{item.ticker}</Text>
                    <Text style={styles.detalhe}>{item.quantidade} un. • Médio: {formatarMoeda(item.preco)}</Text>
                    <Text style={{color: '#888', fontSize: 11, marginTop: 2}}>Hoje: {formatarMoeda(precoAtual)}</Text>
                  </View>
                  
                  <View style={{alignItems: 'flex-end'}}>
                    <Text style={styles.valorItem}>{formatarMoeda(precoAtual * item.quantidade)}</Text>
                    
                    <View style={{flexDirection: 'row', alignItems: 'center'}}>
                        <Text style={{color: corLucro, fontSize: 13, fontWeight: 'bold'}}>
                            {sinal}{formatarMoeda(lucroReais)}
                        </Text>
                        <View style={{backgroundColor: isLucro ? 'rgba(0, 255, 0, 0.1)' : 'rgba(255, 68, 68, 0.1)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, marginLeft: 6}}>
                            <Text style={{color: corLucro, fontSize: 11, fontWeight: 'bold'}}>{sinal}{rentabilidade.toFixed(2)}%</Text>
                        </View>
                    </View>
                    
                    {/* BOTÕES */}
                    <View style={{flexDirection: 'row', marginTop: 10}}>
                        <TouchableOpacity onPress={(e) => {
                            e.stopPropagation();
                            router.push(`/editar/${item.id}`);
                        }} style={{marginRight: 15}}>
                            <Ionicons name="pencil" size={20} color="#00B8FF" />
                        </TouchableOpacity>

                        <TouchableOpacity onPress={(e) => {
                            e.stopPropagation();
                            deletarItem(item.id, item.ticker);
                        }}>
                            <Ionicons name="trash-outline" size={20} color="#666" />
                        </TouchableOpacity>
                    </View>
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
  container: { flex: 1, backgroundColor: '#121212', paddingTop: 50, paddingHorizontal: 10 },
  header: { alignItems: 'center', marginBottom: 10, borderBottomWidth: 1, borderBottomColor: '#333', paddingBottom: 20 },
  labelHeader: { color: '#aaa', fontSize: 14, textTransform: 'uppercase' },
  valorTotal: { color: '#fff', fontSize: 32, fontWeight: 'bold', textShadowColor: 'rgba(0, 255, 0, 0.5)', textShadowOffset: {width: 0, height: 0}, textShadowRadius: 10 },
  subtitulo: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 10, marginLeft: 10, marginTop: 20 },
  card: { backgroundColor: '#1e1e1e', padding: 15, borderRadius: 12, marginBottom: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  ativo: { color: 'white', fontSize: 18, fontWeight: 'bold' },
  detalhe: { color: '#888', fontSize: 12 },
  valorItem: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  vazio: { color: '#666', textAlign: 'center', marginTop: 50 },
  tituloGrafico: { color: '#aaa', marginLeft: 10, fontSize: 14, fontWeight: 'bold' },
  legendaGrafico: { color: '#666', marginLeft: 10, fontSize: 12, marginBottom: 5 }
});