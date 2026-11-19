/**
 * Notes list: shows the offline queue with sync status per note.
 * Long-press a card to delete it.
 */
import React, { useEffect } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from "react-native";
import { useAppStore } from "../store/useAppStore";
import NoteCard from "./NoteCard";

const SYNC_INTERVAL_MS = 30_000;

export default function NotesScreen() {
  const notes = useAppStore((s) => s.notes);
  const sync = useAppStore((s) => s.sync);
  const syncNow = useAppStore((s) => s.syncNow);
  const removeNote = useAppStore((s) => s.removeNote);

  // Background sync while the screen is visible
  useEffect(() => {
    const timer = setInterval(() => {
      void syncNow();
    }, SYNC_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [syncNow]);

  const handleRemove = (id: string) => {
    Alert.alert("Delete note?", "This removes the note from the local queue.", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: () => void removeNote(id) },
    ]);
  };

  return (
    <View style={styles.container}>
      <View style={styles.summary}>
        <Text style={styles.summaryText}>
          {sync.pending} pending · {sync.synced} synced · {sync.failed} failed
        </Text>
        <TouchableOpacity style={styles.syncBtn} onPress={() => void syncNow()}>
          <Text style={styles.syncBtnText}>Sync now</Text>
        </TouchableOpacity>
      </View>
      <FlatList
        data={notes}
        keyExtractor={(n) => n.id}
        renderItem={({ item }) => (
          <NoteCard note={item} onRemove={handleRemove} />
        )}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={false}
            onRefresh={() => void syncNow()}
            tintColor="#3b82f6"
          />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>No notes yet. Capture one from the Capture tab.</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  summary: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  summaryText: { color: "#94a3b8", fontSize: 13 },
  syncBtn: {
    backgroundColor: "#3b82f6",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  syncBtnText: { color: "#ffffff", fontSize: 13, fontWeight: "600" },
  list: { paddingHorizontal: 16, paddingBottom: 24 },
  empty: { color: "#64748b", textAlign: "center", marginTop: 40, fontSize: 14 },
});
