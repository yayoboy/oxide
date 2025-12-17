# 🚀 Auto-Start Guide - MCP + Web UI

Guida completa per avviare automaticamente la Web UI insieme all'MCP server.

---

## 📋 Opzioni Disponibili

Hai **3 modi** per avviare automaticamente MCP + Web UI:

### ✅ **Opzione 1: Comando Unificato `oxide-all`** (Raccomandato)

Il modo più semplice - un singolo comando per tutto.

```bash
# Avvia entrambi i servizi
uv run oxide-all

# Solo MCP
uv run oxide-all --mcp-only

# Solo Web UI
uv run oxide-all --web-only

# Con browser auto-open
uv run oxide-all --open-browser
```

**Pro:**
- ✅ Un solo comando
- ✅ Gestione automatica dei processi
- ✅ Cleanup automatico quando premi Ctrl+C
- ✅ Monitoraggio integrato

**Quando usare:**
- Sviluppo locale
- Testing rapido
- Quando vuoi sia MCP che Web UI

---

### ✅ **Opzione 2: Auto-Start dall'MCP Server**

La Web UI parte automaticamente quando usi l'MCP con Claude Code.

#### Setup in Claude Code Settings

Modifica `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yayoboy/Documents/GitHub/oxide",
        "run",
        "oxide-mcp"
      ],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

**Ora quando Claude Code avvia l'MCP server, la Web UI parte automaticamente!**

**Pro:**
- ✅ Completamente automatico
- ✅ Nessun comando extra
- ✅ Web UI disponibile durante l'uso di Claude
- ✅ Cleanup automatico quando Claude si chiude

**Quando usare:**
- Uso quotidiano con Claude Code
- Vuoi monitorare cosa fa Claude in real-time
- Non vuoi lanciare servizi manualmente

**Come funziona:**

1. Claude Code avvia l'MCP server
2. L'MCP vede `OXIDE_AUTO_START_WEB=true`
3. Avvia automaticamente il Web backend in background
4. Puoi aprire http://localhost:8000 e vedere la dashboard
5. Quando Claude si chiude, tutto viene fermato automaticamente

---

### ✅ **Opzione 3: Script Shell**

Script bash che avvia entrambi i servizi con gestione PID.

```bash
./scripts/start_all.sh
```

**Pro:**
- ✅ Semplice bash script
- ✅ Non richiede dipendenze Python extra
- ✅ Log separati per ogni servizio
- ✅ Facile da customizzare

**Log files:**
- MCP: `/tmp/oxide-mcp.log`
- Web: `/tmp/oxide-web.log`

**Quando usare:**
- Server di produzione
- Automazione con systemd/cron
- Preferisci script shell

---

## 🎯 Confronto Rapido

| Caratteristica | `oxide-all` | Auto-Start MCP | `start_all.sh` |
|----------------|-------------|----------------|----------------|
| Semplicità | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Integrazione Claude | ❌ | ✅ | ❌ |
| Log separati | ❌ | ✅ | ✅ |
| Customizzabile | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Cleanup automatico | ✅ | ✅ | ✅ |

---

## 🚀 Quick Start per Caso d'Uso

### Caso 1: "Voglio sviluppare e testare localmente"

```bash
uv run oxide-all --open-browser
```

Apre tutto + browser automaticamente.

---

### Caso 2: "Uso Claude Code quotidianamente"

**Setup una volta:**

Aggiungi a `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": ["--directory", "/path/to/oxide", "run", "oxide-mcp"],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

**Poi sempre:**
- Apri Claude Code
- Oxide MCP + Web UI partono automaticamente
- Vai a http://localhost:8000 per vedere la dashboard

---

### Caso 3: "Voglio produzione/server"

```bash
# Usa systemd service o
./scripts/start_all.sh
```

---

## 📖 Dettagli Tecnici

### Come Funziona `oxide-all`

```python
# Launcher Python che:
1. Avvia MCP server come subprocess
2. Avvia Web backend come subprocess
3. Monitora entrambi i processi
4. Gestisce Ctrl+C cleanup
```

### Come Funziona Auto-Start

```python
# Nel server MCP:
if os.environ.get("OXIDE_AUTO_START_WEB") == "true":
    # Avvia web backend come subprocess in background
    subprocess.Popen([...uvicorn...])
```

### Variabili d'Ambiente Supportate

```bash
# Auto-start Web UI dall'MCP
OXIDE_AUTO_START_WEB=true    # "true", "1", "yes"

# Config path custom
OXIDE_CONFIG_PATH=/path/to/config.yaml

# Log level
OXIDE_LOG_LEVEL=DEBUG        # DEBUG, INFO, WARNING, ERROR
```

---

## 🔧 Troubleshooting

### "Port 8000 already in use"

```bash
# Trova processo sulla porta 8000
lsof -ti:8000

# Killalo
kill -9 $(lsof -ti:8000)
```

### Web UI non si ferma automaticamente

Se usi `oxide-all`, dovrebbe fermarsi automaticamente.

Se usi auto-start dall'MCP, assicurati di chiudere Claude Code completamente.

### Controllare se i servizi sono running

```bash
# Check MCP (stdio - non ha porta)
ps aux | grep oxide-mcp

# Check Web UI
lsof -ti:8000
# oppure
curl http://localhost:8000/health
```

### Log del Web UI quando auto-start

I log vanno in `/tmp/oxide.log` (configurabile in `config/default.yaml`).

Per vedere log real-time:
```bash
tail -f /tmp/oxide.log
```

---

## 🎯 Esempi Pratici

### Sviluppo Locale

```bash
# Terminal 1 - Backend + MCP
uv run oxide-all

# Terminal 2 - Frontend dev
cd oxide/web/frontend
npm run dev

# Browser: http://localhost:3000
```

### Uso con Claude Code

```json
// ~/.claude/settings.json
{
  "mcpServers": {
    "oxide": {
      "command": "uv",
      "args": ["--directory", "/path/to/oxide", "run", "oxide-mcp"],
      "env": {
        "OXIDE_AUTO_START_WEB": "true"
      }
    }
  }
}
```

Poi:
1. Apri Claude Code
2. Usa Oxide MCP tools
3. Apri http://localhost:8000 in browser per monitorare

### Produzione con systemd

Crea `/etc/systemd/system/oxide.service`:

```ini
[Unit]
Description=Oxide LLM Orchestrator
After=network.target

[Service]
Type=simple
User=oxide
WorkingDirectory=/opt/oxide
ExecStart=/opt/oxide/scripts/start_all.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable oxide
sudo systemctl start oxide
sudo systemctl status oxide
```

---

## ❓ FAQ

**Q: Posso usare sia `oxide-all` che auto-start insieme?**

No, scegli uno dei due per evitare conflitti di porta.

**Q: Come faccio a disabilitare auto-start dopo averlo abilitato?**

Rimuovi o cambia `OXIDE_AUTO_START_WEB` da `true` a `false` nelle settings di Claude.

**Q: Il frontend React va avviato separatamente?**

Sì, questi metodi avviano solo il **backend API**. Per il frontend dev:
```bash
cd oxide/web/frontend && npm run dev
```

Per produzione, fai il build e servi gli static files.

**Q: Posso cambiare la porta della Web UI?**

Sì, modifica gli script o passa `--port` a uvicorn.

---

## 📚 Risorse

- [QUICK_START.md](QUICK_START.md) - Guida rapida generale
- [WEB_UI_GUIDE.md](WEB_UI_GUIDE.md) - Guida completa Web UI
- [INSTALLATION.md](INSTALLATION.md) - Setup MCP per Claude Code

---

## ✨ Riepilogo Comandi

```bash
# Opzione 1: Comando unificato
uv run oxide-all                    # Tutto
uv run oxide-all --open-browser     # Con browser

# Opzione 2: Solo MCP (auto-start in settings.json)
uv run oxide-mcp                    # Web UI parte se OXIDE_AUTO_START_WEB=true

# Opzione 3: Script shell
./scripts/start_all.sh              # Bash launcher

# Servizi separati (old way)
uv run oxide-mcp                    # Solo MCP
uv run oxide-web                    # Solo Web
```

---

**Buon orchestrazione automatica! 🚀**
