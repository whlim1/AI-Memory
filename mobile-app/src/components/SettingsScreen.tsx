/**
 * Settings screen: backend endpoints + capture folder.
 *
 * Defaults target the local network (192.168.0.16 / 192.168.0.19).
 * For remote access switch to Tailscale MagicDNS hosts, e.g.
 * http://gmktec-hx9.ts-dns.xyz:9091
 */
import React from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  ScrollView,
} from "react-native";
import { useAppStore } from "../store/useAppStore";
import { AppSettings } from "../types";

const FIELDS: { key: keyof AppSettings; label: string; hint: string }[] = [
  {
    key: "apiBaseUrl",
    label: "Ingestion API",
    hint: "Phase 5 ingestion service (port 9091)",
  },
  {
    key: "qdrantUrl",
    label: "Qdrant",
    hint: "Vector database (port 6333)",
  },
  {
    key: "lmStudioUrl",
    label: "LM Studio",
    hint: "Inference PC (port 1234) — diagnostics only",
  },
  {
    key: "captureFolder",
    label: "Capture folder",
    hint: "Vault subfolder for mobile captures",
  },
];

export default function SettingsScreen() {
  const settings = useAppStore((s) => s.settings);
  const updateSettings = useAppStore((s) => s.updateSettings);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {FIELDS.map((f) => (
        <View key={f.key} style={styles.field}>
          <Text style={styles.label}>{f.label}</Text>
          <Text style={styles.hint}>{f.hint}</Text>
          <TextInput
            style={styles.input}
            value={settings[f.key]}
            autoCapitalize="none"
            autoCorrect={false}
            onChangeText={(v) => void updateSettings({ [f.key]: v })}
          />
        </View>
      ))}
      <Text style={styles.note}>
        Changes are saved automatically. On Android, allow cleartext HTTP for
        your local network (see README).
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  content: { padding: 16 },
  field: { marginBottom: 20 },
  label: { color: "#f8fafc", fontSize: 15, fontWeight: "600" },
  hint: { color: "#64748b", fontSize: 12, marginBottom: 6 },
  input: {
    color: "#e2e8f0",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
  },
  note: { color: "#64748b", fontSize: 12, marginTop: 8, lineHeight: 18 },
});
