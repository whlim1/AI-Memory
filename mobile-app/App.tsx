import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { SafeAreaProvider } from "react-native-safe-area-context";

import CaptureScreen from "./src/components/CaptureScreen";
import NotesScreen from "./src/components/NotesScreen";
import SettingsScreen from "./src/components/SettingsScreen";
import { SyncStatusBanner } from "./src/components/SyncStatusBanner";

type RootStackParamList = {
  Capture: undefined;
  Notes: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <StatusBar style="auto" />
        <Stack.Navigator
          initialRouteName="Capture"
          screenOptions={{ headerStyle: { backgroundColor: "#1e293b" } }}
        >
          <Stack.Screen
            name="Capture"
            component={CaptureScreen}
            options={{ title: "Capture", headerShown: false }}
          />
          <Stack.Screen name="Notes" component={NotesScreen} options={{ title: "Notes" }} />
          <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Settings" }} />
        </Stack.Navigator>
        <SyncStatusBanner />
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
