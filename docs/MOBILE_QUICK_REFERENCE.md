# Mobile Quick Reference Guide

> **Purpose:** Quick access to AI Memory system from Android devices (Samsung Fold 8 Ultra)
> **Optimized for:** Tailscale MagicDNS remote access

---

## 📱 Remote Access URLs

### Qdrant Dashboard
```
http://gmktec-hx9.ts-dns.xyz/dashboard
```
- **Port:** 6333 (implicit via MagicDNS)
- **Use:** Vector database management, collections, search queries

### LM Studio API
```
http://gmktec-hx9.ts-dns.xyz:1234
```
- **Port:** 1234
- **Use:** LLM inference, model switching, embeddings

---

## 🚨 Browser Tips (Android/Chrome)

### If HTTPS Blocks Your Request
1. **Tap "Proceed anyway"** on the warning screen
2. **Or use HTTP explicitly:** `http://hostname` not `https://`

### Bookmark These URLs
```
Qdrant: http://gmktec-hx9.ts-dns.xyz/dashboard
LM Studio: http://gmktec-hx9.ts-dns.xyz:1234
```

---

## 🔧 Common Admin Tasks

### Check Service Status
```bash
# From Android Termux or PowerShell:
ping gmktec-hx9.ts-dns.xyz
curl http://gmktec-hx9.ts-dns.xyz/dashboard
curl http://gmktec-hx9.ts-dns.xyz:1234/v1/models
```

### View Collections (Qdrant)
Open Qdrant dashboard → Select collection from sidebar

### Switch LM Studio Model
1. Open LM Studio API URL
2. Use model switching endpoint or UI

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Page doesn't load | Check Tailscale is active on Android |
| Connection refused | Verify services running on Windows host |
| Slow responses | Check network quality, try again |

### Quick Diagnostics
```bash
# Test MagicDNS resolution
nslookup gmktec-hx9.ts-dns.xyz

# Test Qdrant
curl http://gmktec-hx9.ts-dns.xyz:6333/health

# Test LM Studio
curl http://gmktec-hx9.ts-dns.xyz:1234/v1/models
```

---

## 📋 Quick Notes

- **Host:** GMKtec AMD HX9 470 (Windows)
- **Tailscale MagicDNS:** `*.ts-dns.xyz`
- **No port forwarding needed** - Tailscale handles routing
- **Access from anywhere** with Tailscale installed on Android

---

*Last Updated: 2026-11-14*
