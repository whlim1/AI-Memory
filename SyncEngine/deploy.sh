# =============================================================================
# AI Memory Pipeline - Obsidian Sync Engine Deployment
# =============================================================================
# Deploys the sync engine to NAS via Portainer stack (stack 43).
# The sync engine watches an Obsidian vault directory and syncs
# Markdown changes to Qdrant vector store + LM Studio embeddings.
# =============================================================================

# Prerequisites:
#   1. NAS has the Obsidian vault directory mounted (e.g., /volume3/obsidian-vault)
#   2. Qdrant is running (stack 43 or standalone)
#   3. LM Studio is accessible on the network (for embeddings)

# --- Step 1: Create sync engine directory on NAS ---
ssh inf-nas@192.168.0.16 "sudo -S mkdir -p /volume3/docker/compose/43/sync_engine /volume3/obsidian-vault /volume3/docker/data/sync_engine"

# --- Step 2: Upload Dockerfile ---
scp Dockerfile.sync_engine inf-nas@192.168.0.16:/volume3/docker/compose/43/sync_engine/

# --- Step 3: Upload compose file ---
scp docker-compose.sync_engine.yml inf-nas@192.168.0.16:/volume3/docker/compose/43/sync_engine/

# --- Step 4: Upload application code ---
scp -r ai_memory_pipeline/ inf-nas@192.168.0.16:/volume3/docker/compose/43/sync_engine/ai_memory_pipeline/

# --- Step 5: Build and deploy ---
ssh inf-nas@192.168.0.16 "sudo -S docker compose -f /volume3/docker/compose/43/sync_engine/docker-compose.sync_engine.yml up -d --build"

# --- Step 6: Verify ---
ssh inf-nas@192.168.0.16 "sudo -S docker ps --filter 'name=sync-engine' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
