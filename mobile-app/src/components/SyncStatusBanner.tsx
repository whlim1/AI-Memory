/**
 * Global sync status banner shown above the navigation bar area.
 * Compact: one line with pending count and last sync time.
 */
import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { useAppStore } from "../store/useAppStore";

export function SyncStatusBanner() {
  const sync = useAppStore((s) => s.sync);
  const hydrated = useAppStore((s) => s.hydrated);

  if (!hydrated) return null;

  const color =
    sync.failed > 0 ? "#ef4444" : sync.pending > 0 ? "#f59e0b" : "#22c55e";
  const label =
    sync.pending > 0
      ? `${sync.pending} note(s) waiting to sync`
      : sync.lastSyncAt
        ? `All synced · ${new Date(sync.lastSyncAt).toLocaleTimeString()}`
        : "Offline — notes stored locally";

  return (
    <View style={styles.banner}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#1e293b",
    paddingHorizontal: 12,
    paddingVertical: 4,
    zIndex: 10,
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  text: { color: "#cbd5e1", fontSize: 11 },
});
