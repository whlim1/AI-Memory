# AI Memory Mobile App

React Native (Expo) + TypeScript app for capturing notes on the go and
syncing them into the AI Memory pipeline (Obsidian vault → Qdrant →
LM Studio).

**Android-first.** iOS is supported but Android is the primary target.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Mobile App (Expo / React Native)           │
│                                             │
│  Capture ──► Offline Queue (AsyncStorage)   │
│     │              │                        │
│     ▼              ▼                        │
│  Vault Mirror ──► Sync Service ──► Backend  │
│  (expo-file-      (FIFO push,     (Phase 5  │
│   system .md)     retry on error)  API :9091)│
└─────────────────────────────────────────────┘
```

- **Offline-first**: every capture is written locally (queue + Markdown
  file in the on-device vault mirror) before any network call.
- **Sync**: pending notes are pushed to the ingestion API in FIFO order
  every 30 s while the Notes screen is visible, plus a manual "Sync now".
- **Vault mirror**: notes are written as
  `<captureFolder>/<YYYY-MM-DD> <template>-<slug>.md` with YAML
  frontmatter, matching what the desktop `VaultWatcher` expects.

## Prerequisites

- Node.js 20+
- Android device with USB debugging enabled (or Expo Go on the device)
- Phone and NAS on the same network (192.168.0.x) **or** Tailscale

## Setup (Android)

1. Install dependencies:

   ```powershell
   cd mobile-app
   npm install
   ```

2. Start the dev server:

   ```powershell
   npm run android
   ```

   Or scan the QR code with **Expo Go** (fastest way to try it).

3. Open **Settings** in the app and verify the endpoints:

   | Setting        | Local network default      | Tailscale (remote)                    |
   |----------------|----------------------------|---------------------------------------|
   | Ingestion API  | `http://192.168.0.16:9091` | `http://gmktec-hx9.ts-dns.xyz:9091`   |
   | Qdrant         | `http://192.168.0.16:6333` | `http://gmktec-hx9.ts-dns.xyz:6333`   |
   | LM Studio      | `http://192.168.0.19:1234` | `http://gmktec-hx9.ts-dns.xyz:1234`   |

4. Capture a note, switch to **Notes**, and watch the status badge move
   `Pending → Syncing… → Synced`.

## Cleartext HTTP (Android)

The backend uses plain HTTP on the local network. Expo Go allows this by
default. For a **production build**, add to `android/app/src/main/AndroidManifest.xml`:

```xml
<application android:usesCleartextTraffic="true" ...>
```

or a network-security-config that allows cleartext for `192.168.*` and
`*.ts-dns.xyz` only.

## Project Layout

```
mobile-app/
├── App.tsx                  # Navigation + screens
├── index.ts                 # Expo entry point
├── app.json                 # App config (endpoints in `extra`)
├── package.json
├── tsconfig.json
├── src/
│   ├── components/          # CaptureScreen, NotesScreen, SettingsScreen,
│   │                        # NoteCard, TemplatePicker, SyncStatusBanner
│   ├── services/
│   │   ├── api.ts           # Backend + Qdrant HTTP client
│   │   ├── storage.ts       # AsyncStorage queue/settings
│   │   └── syncService.ts   # Offline queue → backend FIFO sync
│   ├── store/
│   │   └── useAppStore.ts   # zustand global state
│   ├── config.ts            # Default endpoints (from app.json extra)
│   └── types.ts             # Shared types
├── obsidian-sync/
│   └── vaultWriter.ts       # On-device vault mirror (expo-file-system)
└── assets/
    └── templates/           # meeting / idea / observation / quote
```

## Roadmap (Phase 6.2 → 6.3)

- [ ] Voice recording + transcription (LM Studio Whisper)
- [ ] Image capture with on-device OCR
- [ ] Push notifications for sync failures
- [ ] Knowledge graph view (from `graph.json`)
- [ ] Template expansion from `assets/templates/`

## iOS Notes

iOS is supported via `npm run ios` (requires Xcode + a signing identity).
Voice capture requires the `NSMicrophoneUsageDescription` already set in
`app.json`. No cleartext-HTTP flag needed (ATS exception required for
local IPs in a production build).
