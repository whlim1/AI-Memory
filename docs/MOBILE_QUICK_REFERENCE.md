# Mobile Quick Reference Guide

> **Purpose:** Quick access to AI Memory system from Android devices (Samsung Fold 8 Ultra)
> **Optimized for:** Local network (192.168.0.x) + Tailscale MagicDNS remote access

---

## 📱 Service URLs

### Local Network (on home WiFi — fastest)

| Service | URL | Port | Use |
|---------|-----|------|-----|
| **OpenWebUI** | `http://192.168.0.16:3001` | 3001 | Chat with your knowledge base (main app) |
| **Qdrant Dashboard** | `http://192.168.0.16:6333/dashboard` | 6333 | Vector DB management, collections, search |
| **Infisical** | `http://192.168.0.16:8081` | 8081 | Secrets management |
| **Portainer** | `http://192.168.0.16:9000` | 9000 | Docker container management UI |
| **Prometheus** | `http://192.168.0.16:9090` | 9090 | Metrics / queries |
| **Grafana** | `http://192.168.0.16:3000` | 3000 | Dashboards |
| **Dynamic Chunking** | `http://192.168.0.16:9091` | 9091 | Phase 5: adaptive chunking service |
| **Embedding Quality Monitor** | `http://192.168.0.16:9092` | 9092 | Phase 5: embedding drift detection |
| **Model Caching Strategy** | `http://192.168.0.16:9093` | 9093 | Phase 5: LM Studio model caching |
| **LM Studio API** | `http://192.168.0.19:1234` | 1234 | LLM inference (on inference PC) |

### Remote Access (Tailscale MagicDNS — anywhere)

```
Qdrant:    http://gmktec-hx9.ts-dns.xyz/dashboard
LM Studio: http://gmktec-hx9.ts-dns.xyz:1234
```

> If the Synology NAS is also on Tailscale, replace `192.168.0.16` with its
> MagicDNS hostname (e.g. `<nas-name>.ts-dns.xyz`) for remote access to
> OpenWebUI, Infisical, and the Phase 5 services.

---

## 📲 App Setup (5 minutes)

### OpenWebUI (main chat app)
1. Chrome → `http://192.168.0.16:3001`
2. Log in (admin credentials from Infisical)
3. Tap ⋮ → **Add to Home Screen** → "OpenWebUI"
4. First chat: *"What's in my notes about project X?"*

### Obsidian Mobile (notes)
1. Install **Obsidian** from Play Store
2. Settings → **Vaults** → **Add local vault** (if on same network, use WebDAV)
3. WebDAV: `https://192.168.0.16:5006` → path `/docker/AI-Memory/obsidian-vault`
4. Or sync via Synology Drive app (simplest on LAN)

### Voice Input
1. In OpenWebUI, tap the **microphone icon** in the chat box
2. Chrome → Site settings → **Microphone → Allow** for `192.168.0.16:3001`
3. Android: Settings → Apps → Chrome → Permissions → **Microphone → Allow**

---

## 🚨 Browser Tips (Android/Chrome)

### If HTTPS Blocks Your Request
1. **Tap "Proceed anyway"** on the warning screen
2. **Or use HTTP explicitly:** `http://hostname` not `https://`

### Bookmark These URLs
```
OpenWebUI:  http://192.168.0.16:3001
Qdrant:     http://192.168.0.16:6333/dashboard
Infisical:  http://192.168.0.16:8081
LM Studio:  http://192.168.0.19:1234
```

---

## 🔧 Common Admin Tasks

### Check Service Status
```bash
# From Android Termux or PowerShell:
ping 192.168.0.16
curl http://192.168.0.16:6333/health
curl http://192.168.0.19:1234/v1/models
curl http://192.168.0.16:9091/health   # dynamic chunking
curl http://192.168.0.16:9092/health   # embedding quality
curl http://192.168.0.16:9093/health   # model caching
```

### View Collections (Qdrant)
Open Qdrant dashboard → Select collection from sidebar

### Switch LM Studio Model
1. Open `http://192.168.0.19:1234`
2. Use model switching endpoint or UI

### Restart a Phase 5 Service (via Portainer)
1. Open `http://192.168.0.16:9000` → Containers
2. Find the service → **Restart**
3. Or SSH: `docker compose -f Monitoring/docker-compose.monitoring.yml up -d`

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Page doesn't load (remote) | Check Tailscale is active on Android |
| Page doesn't load (home) | Check phone is on home WiFi, NAS powered on |
| Connection refused | Verify services running: Portainer → Containers |
| OpenWebUI blank page | Check port 3001 in DSM → Security → Firewall |
| Mic not working | Allow microphone permission for Chrome (see App Setup) |
| Slow responses | Check network quality, try again |

### Quick Diagnostics
```bash
# Test LAN reachability
ping 192.168.0.16

# Test Qdrant
curl http://192.168.0.16:6333/health

# Test LM Studio
curl http://192.168.0.19:1234/v1/models

# Test MagicDNS resolution (remote)
nslookup gmktec-hx9.ts-dns.xyz
```

---

## 📋 Quick Notes

- **NAS (Synology):** 192.168.0.16 — OpenWebUI, Qdrant, Infisical, Portainer, Phase 5 services
- **Inference PC:** 192.168.0.19 — LM Studio (port 1234)
- **Windows host:** GMKtec AMD HX9 470 — Tailscale MagicDNS `*.ts-dns.xyz`
- **No port forwarding needed** for LAN access; Tailscale handles remote routing
- **Full verification:** see `docs/MOBILE_ACCESS_CHECKLIST.md`

---

*Last Updated: 2026-11-19*
