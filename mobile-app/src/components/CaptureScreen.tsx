/**
 * Quick capture screen: template picker + title + body + tags.
 *
 * Notes are saved locally first (offline-first); syncing happens in the
 * background via the sync service.
 */
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import { StackNavigationProp } from "@react-navigation/native-stack";

import TemplatePicker from "./TemplatePicker";
import { useAppStore } from "../store/useAppStore";
import { CaptureTemplate } from "../types";

type Nav = StackNavigationProp<{ Capture: undefined; Notes: undefined; Settings: undefined }>;

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function CaptureScreen() {
  const navigation = useNavigation<Nav>();
  const capture = useAppStore((s) => s.capture);

  const [template, setTemplate] = useState<CaptureTemplate>("idea");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [tags, setTags] = useState("");

  const canSave = title.trim().length > 0 || body.trim().length > 0;

  const handleSave = async () => {
    if (!canSave) return;
    try {
      await capture({
        id: newId(),
        template,
        title: title.trim() || "Untitled",
        body: body.trim(),
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setTitle("");
      setBody("");
      setTags("");
      navigation.navigate("Notes");
    } catch (e) {
      Alert.alert("Capture failed", String(e));
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <Text style={styles.header}>Quick Capture</Text>
        <TemplatePicker selected={template} onSelect={setTemplate} />
        <TextInput
          style={styles.title}
          placeholder="Title"
          placeholderTextColor="#64748b"
          value={title}
          onChangeText={setTitle}
        />
        <TextInput
          style={styles.body}
          placeholder="Write your note… (Markdown supported)"
          placeholderTextColor="#64748b"
          value={body}
          onChangeText={setBody}
          multiline
          textAlignVertical="top"
        />
        <TextInput
          style={styles.tags}
          placeholder="tags, comma, separated"
          placeholderTextColor="#64748b"
          value={tags}
          onChangeText={setTags}
        />
        <TouchableOpacity
          style={[styles.save, !canSave && styles.saveDisabled]}
          onPress={handleSave}
          disabled={!canSave}
          activeOpacity={0.8}
        >
          <Text style={styles.saveText}>Save Note</Text>
        </TouchableOpacity>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0f172a" },
  flex: { flex: 1 },
  header: {
    color: "#f8fafc",
    fontSize: 24,
    fontWeight: "700",
    paddingHorizontal: 16,
    paddingTop: 8,
    marginBottom: 12,
  },
  title: {
    color: "#f8fafc",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  body: {
    color: "#e2e8f0",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    marginHorizontal: 16,
    minHeight: 220,
    marginBottom: 8,
  },
  tags: {
    color: "#e2e8f0",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    marginHorizontal: 16,
    marginBottom: 12,
  },
  save: {
    backgroundColor: "#3b82f6",
    borderRadius: 10,
    paddingVertical: 14,
    marginHorizontal: 16,
    alignItems: "center",
  },
  saveDisabled: { backgroundColor: "#334155" },
  saveText: { color: "#ffffff", fontSize: 16, fontWeight: "600" },
});
