/* ConfidenceBars.js — 7-Class Probability Progress Bar Distribution */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

const EMOTION_COLORS = {
  happy: '#10B981',
  sad: '#3B82F6',
  angry: '#EF4444',
  surprised: '#F59E0B',
  neutral: '#6B7280',
  disgust: '#8B5CF6',
  fear: '#EC4899',
};

export default function ConfidenceBars({ distribution }) {
  if (!distribution) return null;

  const sortedEmotions = Object.keys(distribution).sort(
    (a, b) => distribution[b] - distribution[a]
  );

  return (
    <View style={styles.container}>
      <Text style={styles.header}>CONFIDENCE DISTRIBUTION</Text>
      {sortedEmotions.map((emo) => {
        const prob = distribution[emo] || 0;
        const pct = (prob * 100).toFixed(1);
        const color = EMOTION_COLORS[emo] || '#6366F1';

        return (
          <View key={emo} style={styles.row}>
            <Text style={styles.label}>{emo}</Text>
            <View style={styles.track}>
              <View
                style={[
                  styles.fill,
                  { width: `${Math.max(pct, 2)}%`, backgroundColor: color },
                ]}
              />
            </View>
            <Text style={styles.percentage}>{pct}%</Text>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#111827',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
  },
  header: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B7280',
    letterSpacing: 1,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 4,
  },
  label: {
    width: 80,
    fontSize: 13,
    fontWeight: '600',
    color: '#9CA3AF',
    textTransform: 'capitalize',
  },
  track: {
    flex: 1,
    height: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 5,
    marginHorizontal: 10,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 5,
  },
  percentage: {
    width: 45,
    textAlign: 'right',
    fontSize: 12,
    fontWeight: '700',
    color: '#F9FAFB',
  },
});
