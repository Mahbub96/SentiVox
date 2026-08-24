/* AdminScreen.js — Admin Panel for Model Hot-Swapping & App Settings */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from 'react-native';
import client from '../api/client';

export default function AdminScreen({ navigation }) {
  const [models, setModels] = useState([]);
  const [configs, setConfigs] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [modelsResp, configResp, usersResp] = await Promise.all([
        client.get('/api/v1/admin/models'),
        client.get('/api/v1/config'),
        client.get('/api/v1/admin/users'),
      ]);

      setModels(modelsResp.data);
      setConfigs(configResp.data);
      setUsers(usersResp.data);
    } catch (err) {
      Alert.alert('Error', err.response?.data?.detail || 'Failed to fetch admin data.');
    } finally {
      setLoading(false);
    }
  };

  const handleActivateModel = async (modelId) => {
    try {
      await client.post(`/api/v1/admin/models/${modelId}/activate`);
      Alert.alert('Success', `Model ${modelId} activated and hot-swapped in RAM!`);
      fetchAdminData();
    } catch (err) {
      Alert.alert('Hot-Swap Error', err.response?.data?.detail || 'Activation failed.');
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Admin Control Center</Text>
      </View>

      {loading ? (
        <ActivityIndicator color="#F59E0B" size="large" style={{ marginTop: 40 }} />
      ) : (
        <>
          {/* Models Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🧠 UPLOADED KERA MODELS (.H5)</Text>
            {models.map((m) => (
              <View key={m.id} style={styles.card}>
                <View style={styles.cardHeader}>
                  <Text style={styles.modelName}>{m.filename}</Text>
                  {m.is_active ? (
                    <Text style={styles.activeTag}>● ACTIVE</Text>
                  ) : null}
                </View>

                <Text style={styles.cardSub}>Input Shape: {m.input_shape} | Classes: {m.num_classes}</Text>

                {!m.is_active ? (
                  <TouchableOpacity
                    style={styles.activateBtn}
                    onPress={() => handleActivateModel(m.id)}
                  >
                    <Text style={styles.activateText}>⚡ Hot-Swap & Activate</Text>
                  </TouchableOpacity>
                ) : null}
              </View>
            ))}
          </View>

          {/* Configs Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>⚙️ DYNAMIC APP CONFIGURATIONS</Text>
            {configs.map((c) => (
              <View key={c.config_key} style={styles.card}>
                <Text style={styles.configKey}>{c.config_key}</Text>
                <Text style={styles.configVal}>{c.config_value}</Text>
                <Text style={styles.cardSub}>{c.description}</Text>
              </View>
            ))}
          </View>

          {/* Registered Users Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>👥 REGISTERED USERS ({users.length})</Text>
            {users.map((u) => (
              <View key={u.id} style={styles.card}>
                <View style={styles.cardHeader}>
                  <Text style={styles.userName}>{u.full_name}</Text>
                  <Text style={[styles.roleTag, u.role === 'ADMIN' && styles.adminTag]}>
                    {u.role}
                  </Text>
                </View>
                <Text style={styles.cardSub}>{u.email}</Text>
              </View>
            ))}
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
  },
  content: {
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
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#F59E0B',
    letterSpacing: 1,
    marginBottom: 12,
  },
  card: {
    backgroundColor: '#111827',
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  modelName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#F9FAFB',
  },
  activeTag: {
    color: '#10B981',
    fontSize: 11,
    fontWeight: '800',
  },
  cardSub: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 4,
  },
  activateBtn: {
    backgroundColor: '#6366F1',
    borderRadius: 8,
    padding: 10,
    alignItems: 'center',
    marginTop: 10,
  },
  activateText: {
    color: '#FFF',
    fontSize: 13,
    fontWeight: '700',
  },
  configKey: {
    fontSize: 14,
    fontWeight: '700',
    color: '#6366F1',
  },
  configVal: {
    fontSize: 16,
    fontWeight: '800',
    color: '#F9FAFB',
    marginVertical: 2,
  },
  userName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#F9FAFB',
  },
  roleTag: {
    backgroundColor: 'rgba(99, 102, 241, 0.2)',
    color: '#6366F1',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    fontSize: 11,
    fontWeight: '700',
    overflow: 'hidden',
  },
  adminTag: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    color: '#F59E0B',
  },
});
