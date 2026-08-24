/* HomeScreen.js — Main Voice Recording & Emotion Analysis Screen */

import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { Audio } from 'expo-av';
import { AuthContext } from '../context/AuthContext';
import client from '../api/client';
import EmotionBadge from '../components/EmotionBadge';
import ConfidenceBars from '../components/ConfidenceBars';

export default function HomeScreen({ navigation }) {
  const { user, isAdmin, logout } = useContext(AuthContext);
  const [recording, setRecording] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [permissionResponse, requestPermission] = Audio.usePermissions();

  useEffect(() => {
    return () => {
      if (recording) {
        recording.stopAndUnloadAsync();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      if (permissionResponse.status !== 'granted') {
        const resp = await requestPermission();
        if (resp.status !== 'granted') {
          Alert.alert('Permission Required', 'Microphone access is required to record speech.');
          return;
        }
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording: newRecording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      setRecording(newRecording);
      setIsRecording(true);
      setResult(null);
    } catch (err) {
      Alert.alert('Recording Error', err.message);
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    try {
      setIsRecording(false);
      setAnalyzing(true);

      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      const uri = recording.getURI();

      setRecording(null);

      // Upload audio file to API
      const formData = new FormData();
      formData.append('file', {
        uri,
        name: 'mobile_speech.wav',
        type: 'audio/wav',
      });

      const response = await client.post('/api/v1/predict', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setResult(response.data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      Alert.alert('Analysis Failed', msg);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top Bar */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.userName}>{user?.full_name || 'User'}</Text>
          <View style={styles.badgeRow}>
            <Text style={[styles.roleBadge, isAdmin && styles.adminRole]}>
              {user?.role}
            </Text>
          </View>
        </View>

        <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      {/* Mic Record Card */}
      <View style={styles.recordCard}>
        <Text style={styles.cardHeader}>VOICE EMOTION RECOGNITION</Text>
        <Text style={styles.cardSub}>
          Tap the button below to record your speech for real-time analysis.
        </Text>

        <TouchableOpacity
          style={[
            styles.micButton,
            isRecording && styles.micRecording,
            analyzing && styles.micDisabled,
          ]}
          onPress={isRecording ? stopRecording : startRecording}
          disabled={analyzing}
        >
          {analyzing ? (
            <ActivityIndicator color="#FFF" size="large" />
          ) : (
            <Text style={styles.micEmoji}>{isRecording ? '⏹️' : '🎤'}</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.statusText}>
          {isRecording
            ? '🔴 Recording... Tap to Stop & Analyze'
            : analyzing
            ? '⚡ Running 1D-CNN Feature Extraction...'
            : 'Tap Microphone to Start'}
        </Text>
      </View>

      {/* Results Section */}
      {result ? (
        <View style={styles.resultsSection}>
          <EmotionBadge
            emotion={result.predicted_class}
            confidence={result.confidence_score}
            latency={result.inference_latency_ms}
          />
          <ConfidenceBars distribution={result.probability_distribution} />
        </View>
      ) : null}

      {/* Bottom Nav Actions */}
      <View style={styles.navRow}>
        <TouchableOpacity
          style={styles.navCard}
          onPress={() => navigation.navigate('History')}
        >
          <Text style={styles.navIcon}>📜</Text>
          <Text style={styles.navText}>View History</Text>
        </TouchableOpacity>

        {isAdmin ? (
          <TouchableOpacity
            style={[styles.navCard, styles.adminNavCard]}
            onPress={() => navigation.navigate('Admin')}
          >
            <Text style={styles.navIcon}>⚙️</Text>
            <Text style={styles.navText}>Admin Panel</Text>
          </TouchableOpacity>
        ) : null}
      </View>
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
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  greeting: {
    fontSize: 13,
    color: '#9CA3AF',
  },
  userName: {
    fontSize: 22,
    fontWeight: '800',
    color: '#F9FAFB',
  },
  badgeRow: {
    flexDirection: 'row',
    marginTop: 4,
  },
  roleBadge: {
    backgroundColor: 'rgba(99, 102, 241, 0.2)',
    color: '#6366F1',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    fontSize: 11,
    fontWeight: '700',
    overflow: 'hidden',
  },
  adminRole: {
    backgroundColor: 'rgba(245, 158, 11, 0.2)',
    color: '#F59E0B',
  },
  logoutBtn: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 10,
  },
  logoutText: {
    color: '#EF4444',
    fontSize: 13,
    fontWeight: '600',
  },
  recordCard: {
    backgroundColor: '#111827',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  cardHeader: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B7280',
    letterSpacing: 1,
  },
  cardSub: {
    fontSize: 13,
    color: '#9CA3AF',
    textAlign: 'center',
    marginVertical: 12,
  },
  micButton: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: '#6366F1',
    justifyContent: 'center',
    alignItems: 'center',
    marginVertical: 16,
    elevation: 8,
  },
  micRecording: {
    backgroundColor: '#EF4444',
  },
  micDisabled: {
    backgroundColor: '#4B5563',
  },
  micEmoji: {
    fontSize: 36,
  },
  statusText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#F9FAFB',
  },
  resultsSection: {
    marginTop: 16,
  },
  navRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 20,
  },
  navCard: {
    flex: 1,
    backgroundColor: '#111827',
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  adminNavCard: {
    borderColor: 'rgba(245, 158, 11, 0.3)',
  },
  navIcon: {
    fontSize: 24,
    marginBottom: 6,
  },
  navText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#F9FAFB',
  },
});
