/* RegisterScreen.js — Account Creation Screen */

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

export default function RegisterScreen({ navigation }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { register, loading, error, setError } = useContext(AuthContext);

  const handleRegister = async () => {
    if (!fullName || !email || !password) {
      setError('Please fill in all required fields.');
      return;
    }
    await register(email, password, fullName);
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerContainer}>
        <Text style={styles.icon}>🎙️</Text>
        <Text style={styles.title}>Create Account</Text>
        <Text style={styles.subtitle}>Join SentiVox Emotion Recognition Platform</Text>
      </View>

      <View style={styles.card}>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <Text style={styles.label}>Full Name</Text>
        <TextInput
          style={styles.input}
          placeholder="Mahbub Alam"
          placeholderTextColor="#6B7280"
          value={fullName}
          onChangeText={(txt) => { setFullName(txt); setError(null); }}
        />

        <Text style={styles.label}>Email Address</Text>
        <TextInput
          style={styles.input}
          placeholder="user@sentivox.com"
          placeholderTextColor="#6B7280"
          value={email}
          onChangeText={(txt) => { setEmail(txt); setError(null); }}
          autoCapitalize="none"
          keyboardType="email-address"
        />

        <Text style={styles.label}>Password (min 6 chars)</Text>
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
          onPress={handleRegister}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <Text style={styles.buttonText}>Create Account</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={() => navigation.navigate('Login')}
        >
          <Text style={styles.secondaryText}>
            Already have an account? <Text style={styles.linkText}>Sign In</Text>
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
    marginBottom: 24,
  },
  icon: {
    fontSize: 40,
    marginBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: '#F9FAFB',
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
    marginBottom: 14,
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
