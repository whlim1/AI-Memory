# Phase 6: Unified Knowledge Management Layer

## Overview

Phase 6 adds the critical user interface layer that connects human inputs to the AI Memory Pipeline's processing capabilities. This phase enables seamless note-taking, mobile input, and automatic knowledge organization.

---

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  OpenWebUI       │────▶│  Obsidian Vault  │────▶│ AI Memory Pipeline │
│  (Mobile Browser)│     │   (Sync Engine)  │     │  (Processing)   │
└──────────────────┘     └──────────────────┘     └─────────────────┘
                            │                        │
                            ▼                        ▼
                     ┌──────────────────┐    ┌──────────────┐
                     │  Auto-Organizer  │    │  Qdrant DB   │
                     │   (AI Engine)    │    │  + Phase 5   │
                     └──────────────────┘    │  Services    │
                                              └──────────────┘
```

> **Note**: React Native mobile app was abandoned in favor of OpenWebUI's built-in
> mobile-responsive browser interface. Users access the system via mobile browser
> at `http://192.168.0.16:3001`.

---

## Components

### 1. Obsidian Vault Integration Service

**Purpose**: Bridge between Obsidian notes and AI processing pipeline

**Features**:
- Real-time file system monitoring
- Automatic content extraction (Markdown, attachments)
- Smart note categorization using Phase 5 services
- Knowledge graph building from backlinks
- Two-way sync support

**Technical Implementation**:
```python
# ai_memory_pipeline/obsidian/
├── __init__.py
├── vault_watcher.py      # File system monitoring
├── content_processor.py  # Content extraction & categorization
├── graph_builder.py      # Knowledge graph construction
└── sync_engine.py        # Two-way synchronization
```

---

### 2. Mobile Input Interface (OpenWebUI Mobile Browser)

**Purpose**: Mobile-responsive web interface for quick notes, chat, and voice inputs via OpenWebUI

**Features**:
- Quick capture via chat interface (text, voice, image)
- Mobile-responsive design (no separate app needed)
- Real-time sync with Obsidian vault
- Voice-to-text integration (browser-native)
- Template-based input (Meeting, Idea, Observation, Quote)
- RAG-powered search across knowledge base

**Technical Implementation**:
```
OpenWebUI (ghcr.io/open-webui/open-webui:main)
├── Mobile browser access at http://192.168.0.16:3001
├── RAG integration with Qdrant (http://192.168.0.16:6333)
├── Obsidian vault as document source
└── LM Studio models (http://192.168.0.16:1234)
```

---

### 3. Auto-Organization Engine

**Purpose**: Automatically organize incoming notes using AI

**Features**:
- Context-aware categorization
- Automatic tagging
- Entity extraction (people, places, concepts)
- Knowledge graph enrichment
- Temporal organization (timeline view)

**Technical Implementation**:
```python
# ai_memory_pipeline/organization/
├── __init__.py
├── categorizer.py      # AI-powered categorization
├── tagger.py           # Auto-tagging system
├── entity_extractor.py # NER and concept extraction
└── knowledge_graph.py  # Graph construction & updates
```

---

## Implementation Plan

### Phase 6.1: Core Infrastructure (Weeks 1-2)

- [x] Obsidian vault watcher service (`ai_memory_pipeline/obsidian/vault_watcher.py`)
- [x] Content extraction pipeline (`ai_memory_pipeline/obsidian/content_processor.py`)
- [x] Knowledge graph builder (`ai_memory_pipeline/obsidian/graph_builder.py`)
- [x] Sync engine: vault → chunk → embed → Qdrant (`ai_memory_pipeline/obsidian/sync_engine.py`)
- [x] Mobile app architecture design (`mobile-app/` skeleton)
- [ ] Auto-organization engine foundation (basic auto-categorize lives in
      `sync_engine._auto_categorize`; full `organization/` package is Phase 6.3)

**Deliverable**: Basic Obsidian sync with automatic ingestion ✅

---

### Phase 6.2: Mobile Interface (Weeks 3-4)

- [x] React Native mobile app skeleton (`mobile-app/`, Expo + TypeScript)
- [x] Quick capture interface (text + templates; voice/image pending)
- [ ] Voice recording & transcription
- [x] Offline sync mechanism (local queue + FIFO push to ingestion API)

**Deliverable**: Working mobile app for note capture

---

### Phase 6.3: Intelligence Layer (Weeks 5-6)

- [ ] Advanced categorization using Phase 5 services
- [ ] Knowledge graph integration
- [ ] Entity extraction and linking
- [ ] Smart tagging system

**Deliverable**: AI-powered automatic organization

---

### Phase 6.4: Integration & Testing (Weeks 7-8)

- [x] End-to-end testing — `tests/test_phase6_integration.py` (17 test cases, 9 classes)
- [x] Performance optimization — Response caching, heuristic fallback, timeout handling
- [x] Documentation — `docs/PHASE_6_4_COMPLETION.md`
- [x] Migration guides — `docs/MIGRATION_GUIDE.md`

**Deliverable**: ✅ Production-ready Phase 6 system

> **See**: `docs/PHASE_6_4_COMPLETION.md` for detailed results.

---

### Phase 6.5: OpenWebUI Interface (Weeks 9-10)

- [ ] Deploy OpenWebUI container on Synology NAS
- [ ] Configure RAG integration with Qdrant
- [ ] Set up Obsidian vault as document source
- [ ] Integrate LM Studio models
- [ ] Configure voice/audio settings
- [ ] Mobile responsiveness testing
- [ ] User training documentation

**Deliverable**: ChatGPT+ experience on desktop and mobile

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Mobile App | React Native + TypeScript |
| Obsidian Sync | Node.js + obsidian API |
| AI Processing | Phase 5 Services (Qdrant, Embeddings) |
| Backend | Python FastAPI |
| Database | Qdrant + SQLite (mobile) |
| Real-time | WebSockets / Push Notifications |

---

## Configuration

### Environment Variables

```bash
# Obsidian Integration
OBSIDIAN_VAULT_PATH=/path/to/vault
OBSIDIAN_SYNC_INTERVAL=60
OBSIDIAN_AUTO_CATEGORIZE=true

# Mobile App
MOBILE_API_URL=http://localhost:8000
MOBILE_SYNC_TIMEOUT=30

# Auto-Organization
ORGANIZATION_THRESHOLD=0.7
AUTO_TAGGING_ENABLED=true
KNOWLEDGE_GRAPH_UPDATE=true
```

---

## Migration Path

### From Current State to Phase 6

1. **Current**: Manual document ingestion → Qdrant → Phase 5 services
2. **Phase 6**: Obsidian/Mobile → Auto-organization → Qdrant → Phase 5 services

### Backward Compatibility

- All existing ingestion scripts remain functional
- Phase 5 services continue to work unchanged
- Qdrant database structure remains compatible

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Note ingestion latency | < 5 seconds |
| Mobile sync reliability | > 99.9% |
| Auto-tagging accuracy | > 85% |
| Knowledge graph coverage | > 90% of notes linked |

---

## Future Phases

- **Phase 7**: Advanced AI features (summarization, Q&A, chat with notes)
- **Phase 8**: Collaboration features (shared vaults, annotations)
- **Phase 9**: Advanced visualization (knowledge graphs, mind maps)

---

## OpenWebUI Integration Guide

### Quick Start (After Phase 6 Core)

1. **Deploy OpenWebUI**:
```bash
# On Synology NAS
docker run -d --name open-webui \
  -p 3001:8080 \
  -v open-webui:/app/backend/data \
  --env-file .env.openwebui \
  ghcr.io/open-webui/open-webui:main
```

2. **Configure RAG with Qdrant**:
   - URL: `http://192.168.0.16:6333`
   - Collection: `ai_memory_documents`
   - Embedding model: `text-embedding-qwen3-embedding-8b`

3. **Connect Obsidian Vault**:
   - Mount vault as volume or use sync folder
   - Enable automatic ingestion on file changes

4. **Add LM Studio Models**:
   - URL: `http://host.docker.internal:1234`
   - Models auto-discover from LM Studio

5. **Access**:
   - Desktop: `http://localhost:3001`
   - Mobile: `http://192.168.0.16:3001`

### Expected Features

| Feature | Status |
|---------|--------|
| Chat with your notes | ✅ |
| Voice input/output | ✅ |
| RAG search | ✅ |
| Multi-model support | ✅ |
| File upload/ingestion | ✅ |
| Mobile responsive | ✅ |
| Export conversations | ✅ |

---

# MOBILE APP USER GUIDES

## Android Setup Guide

### Option 1: OpenWebUI (Web App - No Installation Required)

#### Step 1: Access OpenWebUI on Android

1. **Open Chrome or Firefox browser** on your Android phone
2. **Navigate to**: `http://192.168.0.16:3001`
3. **Bookmark this page** for easy access:
   - Tap the three dots (menu) → **Add to Home screen**
   - This creates an app-like icon on your home screen

#### Step 2: Configure OpenWebUI Settings

1. **Tap the profile icon** (top right)
2. **Go to Settings** → **Models**
3. **Add LM Studio Model**:
   - Model Name: `qwen3-coder-next`
   - API Base URL: `http://192.168.0.16:1234/v1`
   - Click **Save**

#### Step 3: Enable RAG (Retrieval Augmented Generation)

1. **Go to Settings** → **Files**
2. **Configure Qdrant**:
   - Qdrant URL: `http://192.168.0.16:6333`
   - Collection Name: `ai_memory_documents`
   - Embedding Model: `text-embedding-qwen3-embedding-8b`
   - Click **Save**

#### Step 4: Use Voice Features

1. **Start a new chat**
2. **Tap the microphone icon** (bottom left)
3. **Speak your message**
4. **AI will respond with voice** (enable in Settings → Audio)

---

### Option 2: Obsidian Mobile App

#### Step 1: Install Obsidian from Google Play Store

1. **Open Google Play Store**
2. **Search for "Obsidian"**
3. **Install the official app** (by Obsidian Helium)
4. **Open the app**

#### Step 2: Connect to Your Vault

**Method A: Sync via Synology NAS (Recommended)**

1. **In Obsidian app**: Tap the gear icon → **Sync**
2. **Select "Synology"**
3. **Enter your Synology NAS details**:
   - Host: `192.168.0.16`
   - Port: `5005` (HTTP) or `5006` (HTTPS)
   - Username: Your Synology username
   - Password: Your Synology password
   - Remote Path: `/docker/AIPlatform/obsidian-vault`

**Method B: Sync via WebDAV**

1. **Enable WebDAV on Synology**:
   - Open **Synology DSM** → **File Services**
   - Enable **WebDAV HTTPS**
2. **In Obsidian**: Select "WebDAV" and enter:
   - Server: `https://192.168.0.16:5006`
   - Username/Password: Your Synology credentials

#### Step 3: Configure Quick Capture

1. **Add Quick Capture template**:
   - Go to Settings → **Quick Capture**
   - Template: 
   ```markdown
   ---
   created: {{date}} {{time}}
   tags: quick-capture
   ---
   
   {{selection}}
   ```

2. **Add to Home Screen**:
   - Open Obsidian → Tap three dots → **Add to Home screen**
   - This creates a dedicated capture app icon

#### Step 4: Use Voice Notes

1. **Create a new note** in Quick Capture
2. **Tap the microphone icon** (if using a voice recording plugin)
3. **Or use Android's built-in voice recorder** and save to your Obsidian folder

---

### Option 3: Custom AI Memory App (Advanced)

#### Step 1: Install Termux (Alternative App Store)

1. **Download Termux from F-Droid** (not Google Play):
   - Open browser → Go to `https://f-droid.org/packages/com.termux.app`
   - Download and install

2. **Install required packages**:
```bash
pkg update
pkg install python
pkg install git
pip install requests
```

#### Step 2: Clone AI Memory Pipeline

```bash
cd ~
git clone https://github.com/whlim1/AIPlatform.git
cd AIPlatform
```

#### Step 3: Create Simple Capture Script

Create `~/.shortcuts/capture.sh`:
```bash
#!/bin/bash
# Quick capture script for Android
echo "Enter your note (press Ctrl+D when done):"
cat > /docker/AIPlatform/obsidian-vault/QuickCapture/$(date +%Y%m%d_%H%M%S).md
```

Make executable:
```bash
chmod +x ~/.shortcuts/capture.sh
```

---

## iOS Setup Guide (Brief)

### Option 1: OpenWebUI on iOS

1. **Open Safari** → Navigate to `http://192.168.0.16:3001`
2. **Tap "Share" button** → **Add to Home Screen**
3. **Configure in Settings** (same as Android)

### Option 2: Obsidian on iOS

1. **Download from App Store**
2. **Connect via WebDAV or Synology**
3. **Use Quick Capture widget**

---

## Troubleshooting

### Android Issues

| Issue | Solution |
|-------|----------|
| Cannot connect to OpenWebUI | Ensure device is on same WiFi as NAS |
| Voice not working | Check browser permissions for microphone |
| Sync failing | Verify Synology WebDAV settings |

### Common Fixes

1. **Check network connectivity**:
```bash
# From Android, test connection to NAS
ping 192.168.0.16
```

2. **Clear browser cache** if experiencing issues

3. **Restart containers** if services unavailable:
```bash
docker restart open-webui
docker restart qdrant
```
