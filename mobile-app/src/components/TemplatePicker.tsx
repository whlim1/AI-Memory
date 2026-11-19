import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { CaptureTemplate } from "../types";

const TEMPLATES: { id: CaptureTemplate; label: string; icon: string }[] = [
  { id: "idea", label: "Idea", icon: "💡" },
  { id: "meeting", label: "Meeting", icon: "📋" },
  { id: "observation", label: "Observation", icon: "👁" },
  { id: "quote", label: "Quote", icon: "❝" },
];

interface Props {
  selected: CaptureTemplate;
  onSelect: (t: CaptureTemplate) => void;
}

export default function TemplatePicker({ selected, onSelect }: Props) {
  return (
    <View style={styles.row}>
      {TEMPLATES.map((t) => (
        <TouchableOpacity
          key={t.id}
          style={[styles.chip, selected === t.id && styles.chipActive]}
          onPress={() => onSelect(t.id)}
          activeOpacity={0.7}
        >
          <Text style={styles.icon}>{t.icon}</Text>
          <Text style={[styles.label, selected === t.id && styles.labelActive]}>
            {t.label}
          </Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", gap: 8, paddingHorizontal: 16, marginBottom: 12 },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#334155",
  },
  chipActive: { backgroundColor: "#3b82f6" },
  icon: { fontSize: 14 },
  label: { color: "#e2e8f0", fontSize: 13 },
  labelActive: { color: "#ffffff", fontWeight: "600" },
});
