/* HistoryScreen.js — User Prediction History Screen */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import client from '../api/client';

export default function HistoryScreen({ navigation }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await client.get('/api/v1/predictions/history?limit=30');
      setHistory(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderItem = ({ item }) => {
    const confPct = ((item.confidence_score || 0) * 100).toFixed(1);
    const dateStr = item.created_at
      ? new Date(item.created_at).toLocaleString()
      : 'Recent';

    return (
      <View style={styles.historyCard}>
        <View style={styles.cardHeader}>
          <Text style={styles.emotionText}>
            {item.predicted_class.toUpperCase()}
          </Text>
          <Text style={styles.confidenceText}>{confPct}%</Text>
        </View>

        <View style={styles.cardFooter}>
          <Text style={styles.fileText}>
            🎵 {item.audio_filename || 'Recording'}
          </Text>
          <Text style={styles.dateText}>{dateStr}</Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Prediction History</Text>
      </View>

      {loading ? (
        <ActivityIndicator color="#6366F1" size="large" style={{ marginTop: 40 }} />
      ) : (
        <FlatList
          data={history}
          keyExtractor={(item) => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No past predictions found.</Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
    padding: 20,
    paddingTop: 50,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  backButton: {
    color: '#6366F1',
    fontSize: 16,
    fontWeight: '600',
    marginRight: 16,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    color: '#F9FAFB',
  },
  listContent: {
    paddingBottom: 20,
  },
  historyCard: {
    backgroundColor: '#111827',
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  emotionText: {
    fontSize: 16,
    fontWeight: '800',
    color: '#6366F1',
  },
  confidenceText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#10B981',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  fileText: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  dateText: {
    fontSize: 11,
    color: '#6B7280',
  },
  emptyText: {
    color: '#6B7280',
    textAlign: 'center',
    marginTop: 40,
    fontSize: 14,
  },
});
