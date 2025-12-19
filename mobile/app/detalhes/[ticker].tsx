import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Dimensions, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router'; // Ferramentas de navegação
import { LineChart } from 'react-native-chart-kit';
import { Ionicons } from '@expo/vector-icons';

export default function DetalhesScreen() {
  // Pega o ticker que veio pela URL (ex: PETR4)
  const { ticker } = useLocalSearchParams(); 
  const router = useRouter(); // Para poder voltar
  
  const [grafico, setGrafico] = useState(null);
  const [loading, setLoading] = useState(true);

  // 👇 SEU IP AQUI 👇
  const BASE_URL = "https://meu-invest-app.onrender.com";

  useEffect(() => {
    fetch(`${BASE_URL}/historico/${ticker}`)
      .then(res => res.json())
      .then(json => {
        if (json.data) {
          setGrafico(json);
        }
      })
      .catch(err => console.error("Erro gráfico:", err))
      .finally(() => setLoading(false));
  }, [ticker]);

  return (
    <View style={styles.container}>
      {/* Botão de Voltar */}
      <TouchableOpacity onPress={() => router.back()} style={styles.btnVoltar}>
        <Ionicons name="arrow-back" size={28} color="#00ff00" />
      </TouchableOpacity>

      <Text style={styles.titulo}>{ticker}</Text>
      <Text style={styles.subtitulo}>Histórico - Últimos 30 dias</Text>

      {loading ? (
        <ActivityIndicator size="large" color="#00ff00" style={{marginTop: 50}}/>
      ) : grafico ? (
        <View style={{alignItems: 'center'}}>
          <LineChart
            data={{
              labels: grafico.labels,
              datasets: [{ data: grafico.data }]
            }}
            width={Dimensions.get("window").width - 20} 
            height={220}
            yAxisLabel="R$ "
            yAxisInterval={1} 
            chartConfig={{
              backgroundColor: "#1e1e1e",
              backgroundGradientFrom: "#1e1e1e",
              backgroundGradientTo: "#121212",
              decimalPlaces: 2, 
              color: (opacity = 1) => `rgba(0, 255, 0, ${opacity})`,
              labelColor: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
              propsForDots: { r: "4", strokeWidth: "2", stroke: "#00ff00" }
            }}
            bezier // Deixa a linha curva (mais bonito)
            style={{ borderRadius: 16, marginTop: 20 }}
          />
        </View>
      ) : (
        <Text style={{color: '#fff', textAlign: 'center', marginTop: 20}}>
            Não foi possível carregar o histórico.
        </Text>
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
  btnVoltar: {
    marginBottom: 10,
    padding: 5
  },
  titulo: {
    color: '#00ff00',
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  subtitulo: {
    color: '#aaa',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20
  }
});