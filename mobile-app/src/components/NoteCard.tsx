import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { CapturedNote } from "../types";

const STATUS_META: Record<CapturedNote["status"], { label: string; color: string }> = {
  pending: { label: "Pending", color: "#f59e0b" },
  syncing: { label: "Syncing…", color: "#3b82f6" },
  synced: { label: "Synced", color: "#22c55e" },
  error: { label: "Error", color: "#ef4444" },
};

interface Props {
  note: CapturedNote;
  onRemove: (id: string) => void;
}

export default function NoteCard({ note, onRemove }: Props) {
  const status = STATUS_META[note.status];
  const date = new Date(note.createdAt).toLocaleString();

  return (
    <TouchableOpacity
      style={styles.card}
      onLongPress={() => onRemove(note.id)}
      activeOpacity={0.8}
    >
      <View style={styles.topRow}>
        <Text style={styles.title} numberOfLines={1}>
          {note.title}
        </Text>
        <View style={[styles.badge, { backgroundColor: status.color }]}>
          <Text style={styles.badgeText}>{status.label}</Text>
        </View>
      </View>
      <Text style={styles.body} numberOfLines={3}>
        {note.body}
      </Text>
      <View style={styles.bottomRow}>
        <Text style={styles.meta}>
          {note.template} · {date}
          {note.tags.length > 0 ? ` · ${note.tags.join(", ")}` : ""}
        </Text>
      </View>
      {note.lastError ? (
        <Text style={styles.error} numberOfLines={1}>
          {note.lastError}
        </Text>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
  },
  topRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  title: { color: "#f8fafc", fontSize: 16, fontWeight: "600", flex: 1 },
  badge: { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText: { color: "#0f172a", fontSize: 11, fontWeight: "700" },
  body: { color: "#cbd5e1", fontSize: 14, marginTop: 6 },
  bottomRow: { flexDirection: "row", marginTop: 8 },
  meta: { color: "#64748b", fontSize: 12 },
  error: { color: "#ef4444", fontSize: 12, marginTop: 4 },
});
