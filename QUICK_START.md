# 🚀 Oxide - Quick Start Guide

Partenza rapida per l'implementazione completa di Oxide con Web UI e servizi di rete.

## ✅ Implementazione Completata

L'intero sistema Oxide è stato implementato con successo! Include:

### 🎯 Funzionalità Completate

1. **✅ Backend FastAPI**
   - REST API completa (Services, Tasks, Monitoring)
   - WebSocket per streaming real-time
   - Gestione task asincrona
   - Metriche di sistema

2. **✅ Frontend React**
   - Dashboard real-time
   - Monitoraggio servizi
   - Task history
   - Live updates via WebSocket

3. **✅ Supporto Servizi di Rete**
   - Ollama Remote adapter (completo)
   - LM Studio adapter (completo)
   - Script di setup automatici
   - Network scanner

4. **✅ Script Utility**
   - `setup_ollama_remote.sh` - Configura Ollama remoto
   - `setup_lmstudio.sh` - Configura LM Studio
   - `test_network.py` - Test connessioni di rete
   - `test_connection.py` - Test servizi locali
   - `validate_config.py` - Valida configurazione

---

## 🏃 Avvio Rapido (3 Passi)

### Passo 1: Installa Dipendenze

```bash
cd /Users/yayoboy/Documents/GitHub/oxide

# Python backend
uv sync

# Frontend React
cd oxide/web/frontend
npm install
cd ../..
```

### Passo 2: Avvia i Servizi

**Terminal 1 - Backend API:**
```bash
uv run oxide-web
```

**Terminal 2 - Frontend:**
```bash
cd oxide/web/frontend
npm run dev
```

### Passo 3: Apri Dashboard

Vai a: **http://localhost:3000**

---

## 📊 Cosa Puoi Fare Ora

### 1. Monitorare i Servizi

La dashboard mostra:
- ✅ Servizi LLM attivi e disponibili
- 📊 Metriche di sistema (CPU, RAM)
- 📝 Cronologia task
- 🔴 Live updates via WebSocket

### 2. Testare i Servizi Locali

```bash
# Test tutti i servizi configurati
uv run python scripts/test_connection.py

# Test servizio specifico
uv run python scripts/test_connection.py --service gemini
uv run python scripts/test_connection.py --service qwen
uv run python scripts/test_connection.py --service ollama_local
```

### 3. Configurare Servizi di Rete

#### Setup Ollama Remoto

Se hai Ollama su un altro PC/server:

```bash
# Automatic setup
./scripts/setup_ollama_remote.sh --ip 192.168.1.100

# Sul server remoto, avvia Ollama con:
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

#### Setup LM Studio

Se hai LM Studio sul laptop:

```bash
# Automatic setup
./scripts/setup_lmstudio.sh --ip 192.168.1.50

# In LM Studio:
# 1. Settings → Server → Enable Local Server
# 2. Enable Network Access
# 3. Load a model
```

### 4. Scansionare la Rete

Trova automaticamente servizi LLM sulla tua LAN:

```bash
# Scan network 192.168.1.x
uv run python scripts/test_network.py --scan 192.168.1.0/24

# Test servizi di rete configurati
uv run python scripts/test_network.py --all
```

---

## 📁 Struttura File Implementata

```
oxide/
├── oxide/
│   ├── web/
│   │   ├── backend/
│   │   │   ├── main.py                 ✅ FastAPI app
│   │   │   ├── websocket.py            ✅ WebSocket manager
│   │   │   └── routes/
│   │   │       ├── services.py         ✅ Services API
│   │   │       ├── tasks.py            ✅ Tasks API
│   │   │       └── monitoring.py       ✅ Monitoring API
│   │   └── frontend/
│   │       ├── package.json            ✅ Dependencies
│   │       ├── vite.config.js          ✅ Build config
│   │       ├── index.html              ✅ Entry point
│   │       └── src/
│   │           ├── App.jsx             ✅ Main component
│   │           ├── api/client.js       ✅ API client
│   │           ├── hooks/              ✅ Custom hooks
│   │           └── components/         ✅ UI components
│   ├── core/                           ✅ Già implementato
│   ├── adapters/                       ✅ Tutti i 4 adapters
│   └── mcp/                            ✅ MCP server
├── scripts/
│   ├── setup_ollama_remote.sh          ✅ Setup Ollama
│   ├── setup_lmstudio.sh               ✅ Setup LM Studio
│   ├── test_network.py                 ✅ Network tester
│   ├── test_connection.py              ✅ Service tester
│   └── validate_config.py              ✅ Config validator
├── config/
│   └── default.yaml                    ✅ Configurazione
├── WEB_UI_GUIDE.md                     ✅ Guida Web UI
├── INSTALLATION.md                     ✅ Guida installazione
└── README.md                           ✅ Aggiornato
```

---

## 🔧 Comandi Principali

### Gestione Servizi

```bash
# Avvia backend API
uv run oxide-web

# Avvia MCP server (per Claude Code)
uv run oxide-mcp

# Avvia frontend dev
cd oxide/web/frontend && npm run dev

# Build frontend per produzione
cd oxide/web/frontend && npm run build
```

### Testing

```bash
# Test servizi locali
uv run python scripts/test_connection.py --all

# Test servizi di rete
uv run python scripts/test_network.py --all

# Valida configurazione
uv run python scripts/validate_config.py

# Scan rete per servizi
uv run python scripts/test_network.py --scan 192.168.1.0/24
```

### Setup Network

```bash
# Ollama remote
./scripts/setup_ollama_remote.sh --ip IP_ADDRESS

# LM Studio
./scripts/setup_lmstudio.sh --ip IP_ADDRESS
```

---

## 📖 API Documentation

Una volta avviato il backend, accedi a:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Endpoint Principali

```bash
# Services
GET  /api/services              # Lista tutti i servizi
GET  /api/services/{name}       # Info servizio
POST /api/services/{name}/test  # Test servizio

# Tasks
POST /api/tasks/execute         # Esegui task
GET  /api/tasks                 # Lista task
GET  /api/tasks/{id}            # Dettagli task

# Monitoring
GET /api/monitoring/metrics     # Metriche sistema
GET /api/monitoring/stats       # Statistiche task
GET /api/monitoring/health      # Health check

# WebSocket
WS  /ws                         # Real-time updates
```

---

## 🎯 Prossimi Passi

1. **Testa la Web UI**
   ```bash
   # Terminal 1
   uv run oxide-web

   # Terminal 2
   cd oxide/web/frontend && npm run dev

   # Browser
   open http://localhost:3000
   ```

2. **Configura Servizi di Rete** (opzionale)
   ```bash
   # Trova servizi sulla tua rete
   uv run python scripts/test_network.py --scan 192.168.1.0/24

   # Configura quelli trovati
   ./scripts/setup_ollama_remote.sh --ip FOUND_IP
   ```

3. **Integra con Claude Code**
   - La Web UI è complementare all'MCP server
   - Usa `uv run oxide-mcp` per l'integrazione Claude
   - Vedi [INSTALLATION.md](INSTALLATION.md) per i dettagli

4. **Esplora l'API**
   - Apri http://localhost:8000/docs
   - Prova gli endpoint interattivamente
   - Testa il WebSocket

---

## ❓ Troubleshooting

### Backend Non Parte

```bash
# Verifica dipendenze
uv sync

# Test imports
uv run python -c "from oxide.web.backend.main import app; print('OK')"

# Verifica porta libera
lsof -ti:8000
```

### Frontend Non Parte

```bash
cd oxide/web/frontend

# Reinstalla dipendenze
rm -rf node_modules package-lock.json
npm install

# Verifica Node.js version
node --version  # Deve essere 18+
```

### Servizi Non Disponibili

```bash
# Test servizio specifico
uv run python scripts/test_connection.py --service NOME_SERVIZIO

# Verifica configurazione
uv run python scripts/validate_config.py

# Per CLI tools, verifica PATH
which gemini
which qwen
```

### WebSocket Non Funziona

1. Verifica backend in ascolto: `curl http://localhost:8000/health`
2. Controlla console browser per errori
3. Disabilita estensioni browser
4. Prova browser diverso

---

## 📚 Documentazione Completa

- **[WEB_UI_GUIDE.md](WEB_UI_GUIDE.md)** - Guida completa Web UI
- **[INSTALLATION.md](INSTALLATION.md)** - Setup e integrazione MCP
- **[README.md](README.md)** - Panoramica progetto
- **http://localhost:8000/docs** - API Reference interattiva

---

## ✨ Funzionalità Chiave

### Web Dashboard
- ✅ Monitoraggio real-time di tutti i servizi
- ✅ Metriche CPU/RAM del sistema
- ✅ Cronologia task eseguiti
- ✅ WebSocket per live updates
- ✅ Interface responsive

### Network Support
- ✅ Ollama Remote (HTTP API)
- ✅ LM Studio (OpenAI-compatible API)
- ✅ Script setup automatici
- ✅ Network scanner
- ✅ Health checks

### API REST
- ✅ 15+ endpoints completi
- ✅ Documentazione interattiva
- ✅ Gestione task asincrona
- ✅ Streaming responses
- ✅ Validation con Pydantic

---

## 🎉 Conclusione

**L'implementazione è COMPLETA!**

Tutto il sistema è stato implementato:
- ✅ Backend FastAPI con WebSocket
- ✅ Frontend React con dashboard
- ✅ Supporto servizi di rete
- ✅ Script di setup e testing
- ✅ Documentazione completa

**Sei pronto per usare Oxide!**

```bash
# Avvia tutto in 2 comandi:
uv run oxide-web                           # Terminal 1
cd oxide/web/frontend && npm run dev       # Terminal 2

# Apri il browser
open http://localhost:3000
```

Buon orchestrazione! 🚀🔬
