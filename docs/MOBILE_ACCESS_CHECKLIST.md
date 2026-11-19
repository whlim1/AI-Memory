# Mobile Access Deployment Verification Checklist

> **Purpose:** Verify that the AI Memory system is fully accessible from an Android device
> **When to run:** After initial deployment, after NAS reboots, after network changes, or when mobile access breaks
> **Time required:** ~10 minutes
> **Companion docs:** `MOBILE_QUICK_REFERENCE.md` (URLs), `MOBILE_USER_GUIDE.md` (full setup)

---

## 1. Prerequisites

- [ ] Android phone (Samsung Fold 8 Ultra) with Chrome installed
- [ ] Phone connected to **home WiFi** (same network as NAS) — or Tailscale active for remote
- [ ] Synology NAS (192.168.0.16) powered on
- [ ] Inference PC (192.168.0.19) powered on with LM Studio server running

---

## 2. Service Health (on NAS)

Verify from Portainer (`http://192.168.0.16:9000`), SSH, or the Docker UI:

| Service | Expected State | Port |
|---------|---------------|------|
| [ ] `open-webui` | Up | 3001 |
| [ ] `qdrant` | Up | 6333 |
| [ ] `infisical` | Up | 8081 |
| [ ] `dynamic-chunking` | Up or Restarting* | 9091 |
| [ ] `embedding-quality-monitor` | Up or Restarting* | 9092 |
| [ ] `model-caching-strategy` | Up or Restarting* | 9093 |

> *Phase 5 services complete their initial run and restart by design (`restart: unless-stopped`). "Restarting" briefly is normal.

**LM Studio (on inference PC):**
- [ ] LM Studio server running on port 1234
- [ ] `curl http://192.168.0.19:1234/v1/models` returns a model list

---

## 3. Port Reachability from Phone

Open Chrome on the phone and confirm each URL loads:

| # | URL | Expected |
|---|-----|----------|
| [ ] 1 | `http://192.168.0.16:3001` | OpenWebUI login screen |
| [ ] 2 | `http://192.168.0.16:6333/dashboard` | Qdrant dashboard |
| [ ] 3 | `http://192.168.0.16:8081` | Infisical login |
| [ ] 4 | `http://192.168.0.16:9000` | Portainer login |
| [ ] 5 | `http://192.168.0.19:1234` | LM Studio API (JSON or UI) |

**If a page fails:**
1. `ping 192.168.0.16` from phone (Termux) — NAS reachable?
2. Check DSM → **Security → Firewall** — port open?
3. Check Portainer — container actually running?
4. Remote access? Verify Tailscale is connected on the phone.

---

## 4. OpenWebUI Login & RAG Test

- [ ] Log in to OpenWebUI at `http://192.168.0.16:3001` (credentials from Infisical)
- [ ] Home screen shows chat interface
- [ ] **RAG test:** ask a question about content you know is in your Obsidian vault / Qdrant, e.g.:
  - *"What do my notes say about the AI Memory Pipeline phases?"*
- [ ] Response cites or references your notes (not a generic answer)
- [ ] **Fallback test:** ask a general question — AI responds via LM Studio

**If RAG fails:**
1. Check Qdrant collections exist (dashboard → Collections)
2. Check `docker logs open-webui` for Qdrant/LM Studio connection errors
3. Verify OpenWebUI is configured with Qdrant at `192.168.0.16:6333` and LM Studio at the correct host

---

## 5. Voice Input

- [ ] Microphone icon visible in OpenWebUI chat box
- [ ] Tap mic → Chrome shows permission prompt → **Allow**
- [ ] Speak a test phrase → transcript appears in chat box
- [ ] Send → AI responds (ideally with voice output if TTS enabled)

**If mic fails:**
1. Chrome → ⋮ → Site settings → **Microphone → Allow** for `192.168.0.16:3001`
2. Android: Settings → Apps → Chrome → Permissions → **Microphone → Allow**
3. Note: mic requires HTTPS or a trusted origin — on LAN, Chrome treats `192.168.0.16` as potentially trustworthy; if blocked, use Tailscale MagicDNS HTTPS or a reverse proxy with TLS

---

## 6. Obsidian Sync Test

- [ ] Obsidian app installed on phone
- [ ] Vault connected (WebDAV `https://192.168.0.16:5006` → `/docker/AI-Memory/obsidian-vault`, or Synology Drive)
- [ ] Existing notes visible in the vault
- [ ] **Write test:** create a new note on phone → save
- [ ] **Sync test:** note appears on NAS (check via File Station or `ls /docker/AI-Memory/obsidian-vault`)
- [ ] **RAG loop test:** after sync, ask OpenWebUI about the new note's content

**If sync fails:**
1. DSM → File Services → WebDAV → confirm **HTTPS enabled on port 5006**
2. Verify WebDAV credentials
3. Check the remote path matches exactly (case-sensitive)

---

## 7. Phase 5 Services (optional, admin)

- [ ] `http://192.168.0.16:9091/health` — dynamic chunking responds
- [ ] `http://192.168.0.16:9092/health` — embedding quality monitor responds
- [ ] `http://192.168.0.16:9093/health` — model caching strategy responds
- [ ] Grafana (`http://192.168.0.16:3000`) shows monitoring dashboards with data

---

## 8. Remote Access (Tailscale) — if applicable

- [ ] Tailscale app installed and connected on phone
- [ ] Phone **off home WiFi** (use mobile data)
- [ ] `http://gmktec-hx9.ts-dns.xyz/dashboard` — Qdrant loads
- [ ] `http://gmktec-hx9.ts-dns.xyz:1234` — LM Studio loads
- [ ] (If NAS on Tailscale) OpenWebUI via NAS MagicDNS hostname

---

## ✅ Final Sign-Off

| Check | Status |
|-------|--------|
| All services healthy | ☐ |
| All ports reachable from phone | ☐ |
| OpenWebUI login works | ☐ |
| RAG returns notes-based answers | ☐ |
| Voice input works | ☐ |
| Obsidian sync round-trip works | ☐ |
| Phase 5 services responding | ☐ |
| Remote access (if configured) | ☐ |

**Verified by:** ____________________  **Date:** ____________

---

*Last Updated: 2026-11-19*
