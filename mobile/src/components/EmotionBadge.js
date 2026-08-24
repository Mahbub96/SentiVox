/* EmotionBadge.js — Hero Winner Badge for Predicted Emotion */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const EMOTION_EMOJIS = {
  happy: '😃',
  sad: '😢',
  angry: '😡',
  surprised: '😲',
  neutral: '😐',
  disgust: '🤢',
  fear: '😨',
};

const EMOTION_COLORS = {
  happy: '#10B981',
  sad: '#3B82F6',
  angry: '#EF4444',
  surprised: '#F59E0B',
  neutral: '#6B7280',
  disgust: '#8B5CF6',
  fear: '#EC4899',
};

export default function EmotionBadge({ emotion, confidence, latency }) {
  const emoKey = (emotion || 'neutral').toLowerCase();
  const emoji = EMOTION_EMOJIS[emoKey] || '🎙️';
  const color = EMOTION_COLORS[emoKey] || '#6366F1';
  const confPct = ((confidence || 0) * 100).toFixed(1);

  return (
    <View style={[styles.card, { borderColor: color }]}>
      <View style={[styles.emojiContainer, { backgroundColor: `${color}20` }]}>
        <Text style={styles.emoji}>{emoji}</Text>
      </View>
      <View style={styles.details}>
        <Text style={styles.label}>DETECTED EMOTION</Text>
        <Text style={[styles.title, { color }]}>{emoKey.toUpperCase()}</Text>
        <View style={styles.row}>
          <Text style={styles.confidence}>{confPct}% Confidence</Text>
          {latency ? <Text style={styles.latency}>⚡ {latency}ms</Text> : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#111827',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1.5,
    marginVertical: 12,
  },
  emojiContainer: {
    padding: 14,
    borderRadius: 14,
    marginRight: 16,
  },
  emoji: {
    fontSize: 36,
  },
  details: {
    flex: 1,
  },
  label: {
    fontSize: 10,
    fontWeight: '700',
    color: '#6B7280',
    letterSpacing: 1,
  },
  title: {
    fontSize: 24,
    fontWeight: '800',
    marginVertical: 2,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
  },
  confidence: {
    fontSize: 13,
    fontWeight: '600',
    color: '#9CA3AF',
  },
  latency: {
    fontSize: 11,
    fontWeight: '600',
    color: '#10B981',
  },
});
