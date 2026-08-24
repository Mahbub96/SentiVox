/* LoginScreen.js — User / Admin Authentication Screen */

import React, { useState, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function LoginScreen({ navigation }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, loading, error, setError } = useContext(AuthContext);

  const handleLogin = async () => {
    if (!email || !password) {
      setError('Please fill in all fields.');
      return;
    }
    await login(email, password);
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerContainer}>
        <Text style={styles.icon}>🎙️</Text>
        <Text style={styles.title}>SentiVox</Text>
        <Text style={styles.subtitle}>Speech Emotion Recognition Platform</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Sign In</Text>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <Text style={styles.label}>Email Address</Text>
        <TextInput
          style={styles.input}
          placeholder="admin@sentivox.com"
          placeholderTextColor="#6B7280"
          value={email}
          onChangeText={(txt) => { setEmail(txt); setError(null); }}
          autoCapitalize="none"
          keyboardType="email-address"
        />

        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          placeholder="••••••••"
          placeholderTextColor="#6B7280"
          value={password}
          onChangeText={(txt) => { setPassword(txt); setError(null); }}
          secureTextEntry
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.buttonText}>Sign In</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => navigation.navigate('Register')}
        >
          <Text style={styles.secondaryText}>
            Don't have an account? <Text style={styles.linkText}>Register</Text>
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
    justifyContent: 'center',
    padding: 24,
  },
  headerContainer: {
    alignItems: 'center',
    marginBottom: 32,
  },
  icon: {
    fontSize: 48,
    marginBottom: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: '800',
    color: '#F9FAFB',
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 13,
    color: '#9CA3AF',
    marginTop: 4,
  },
  card: {
    backgroundColor: '#111827',
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#F9FAFB',
    marginBottom: 16,
  },
  errorText: {
    color: '#EF4444',
    fontSize: 13,
    marginBottom: 12,
    fontWeight: '600',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: '#9CA3AF',
    marginBottom: 6,
  },
  input: {
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    padding: 14,
    color: '#F9FAFB',
    fontSize: 15,
    marginBottom: 16,
  },
  button: {
    backgroundColor: '#6366F1',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    marginTop: 16,
    alignItems: 'center',
  },
  secondaryText: {
    color: '#9CA3AF',
    fontSize: 13,
  },
  linkText: {
    color: '#6366F1',
    fontWeight: '700',
  },
});
