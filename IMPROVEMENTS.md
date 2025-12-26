# Oxide - Ollama & LM Studio Integration Improvements

## 🎯 Obiettivo Completato

Miglioramento dell'integrazione con Ollama locale e LM Studio usando Service Manager avanzato.

---

## ✨ Nuove Features Implementate

### 1. **Service Manager** (`src/oxide/utils/service_manager.py`)

Gestione intelligente del lifecycle dei servizi LLM locali:

#### Features:
- ✅ **Auto-Start Ollama**: Avvio automatico se non in esecuzione
  - Supporto multi-piattaforma (macOS, Linux, Windows)
  - Usa Ollama.app su macOS se disponibile
  - Fallback a `ollama serve` come processo background
  - Supporto systemd su Linux

- ✅ **Auto-Detection Modelli**: Rileva automaticamente i modelli disponibili
  - Ollama: via `/api/tags`
  - LM Studio: via `/v1/models` (OpenAI-compatible)
  - Selezione intelligente del miglior modello disponibile
  - Supporto lista preferenze (es: ["qwen2.5-coder", "codellama"])

- ✅ **Health Monitoring**: Verifica salute servizi con auto-recovery
  - Health checks periodici configurabili
  - Tentativo auto-restart su failure
  - Tracking stato servizi in tempo reale

- ✅ **Smart Model Selection**:
  - Match esatto su nome modello
  - Match parziale (es: "qwen" → "qwen2.5-coder:7b")
  - Fallback al primo modello disponibile

#### API Principali:

```python
from oxide.utils.service_manager import get_service_manager

service_manager = get_service_manager()

# Ensure Ollama running
await service_manager.ensure_ollama_running(
    base_url="http://localhost:11434",
    auto_start=True,
    timeout=30
)

# Get available models
models = await service_manager.get_available_models(
    base_url="http://localhost:11434",
    api_type="ollama"
)

# Auto-detect best model
best_model = await service_manager.auto_detect_model(
    base_url="http://localhost:11434",
    api_type="ollama",
    preferred_models=["qwen2.5-coder", "codellama"]
)

# Comprehensive health check
health = await service_manager.ensure_service_healthy(
    service_name="ollama_local",
    base_url="http://localhost:11434",
    api_type="ollama",
    auto_start=True,
    auto_detect_model=True
)

# Start background health monitoring
await service_manager.start_health_monitoring(
    service_name="ollama_local",
    base_url="http://localhost:11434",
    interval=60,
    auto_recovery=True
)
```

---

### 2. **Enhanced HTTP Adapter** (`src/oxide/adapters/ollama_http.py`)

Adapter HTTP potenziato con features enterprise:

#### Nuove Configurazioni:

```yaml
ollama_local:
  type: http
  base_url: "http://localhost:11434"
  api_type: ollama
  default_model: "qwen2.5-coder:7b"

  # Enhanced features
  auto_start: true              # Auto-start service if down
  auto_detect_model: true       # Auto-detect best model
  max_retries: 2                # Retry attempts on failure
  retry_delay: 2                # Seconds between retries
  preferred_models:             # Priority list for auto-detection
    - "qwen2.5-coder"
    - "codellama"
```

#### Features:
- ✅ **Lazy Initialization**: Servizio avviato solo al primo uso
- ✅ **Smart Retry**: Retry automatico con backoff su errori temporanei
- ✅ **Model Fallback**: Se default_model non disponibile, auto-detect
- ✅ **Auto-Recovery**: Tenta restart servizio su connection failure
- ✅ **Caching**: Modello rilevato viene cachato per performance

#### Behavior:

1. **Prima Chiamata**:
   - Verifica se servizio è healthy
   - Auto-start se configurato e non running
   - Auto-detect modello se `default_model: null`
   - Cache risultati per chiamate successive

2. **Durante Execution**:
   - Retry automatico su errori (configurable)
   - Tenta restart servizio tra retry (solo Ollama)
   - Log dettagliati per debugging

3. **Gestione Errori**:
   - `ServiceUnavailableError` → retry con auto-start
   - `HTTPAdapterError` → errore immediato (non recuperabile)
   - `TimeoutError` → retry con timeout aumentato

---

### 3. **LM Studio Support Migliorato**

LM Studio ora funziona **out-of-the-box** senza configurazione manuale:

```yaml
lmstudio:
  type: http
  base_url: "http://192.168.1.33:1234/v1"
  api_type: openai_compatible
  enabled: true
  default_model: null           # Auto-detected on first use
  auto_detect_model: true       # CRITICAL for LM Studio
  preferred_models:
    - "qwen"
    - "coder"
    - "codellama"
    - "deepseek"
```

#### Problemi Risolti:

**PRIMA:**
```
❌ Error: No model specified and no default_model configured
❌ LM Studio model names change based on loaded model
❌ Manual model name configuration required
```

**ADESSO:**
```
✅ Auto-detect via /v1/models endpoint
✅ Seleziona automaticamente il miglior modello tra quelli disponibili
✅ Usa preferred_models per priorità intelligente
✅ Zero configurazione manuale necessaria
```

---

## 📊 Test Results

Tutti i test passati con successo:

```bash
$ uv run python scripts/test_ollama_integration.py

✅ PASSED - service_manager        (Auto-start e health check)
✅ PASSED - ollama_execution        (Task execution con retry)
✅ PASSED - model_detection         (Auto-detection modelli)
✅ PASSED - lmstudio                (LM Studio integration)
✅ PASSED - retry_logic             (Smart retry verification)

Result: 5/5 tests passed 🎉
```

### Output Dettagliato:

**Ollama:**
- Service: healthy ✅
- Models Found: 3 (qwen3-coder, qwen2.5-coder×2)
- Auto-detected: qwen2.5-coder:7b
- Execution: Successful in ~16s

**LM Studio:**
- Service: healthy ✅
- Models Found: 5
  - mistralai/codestral-22b-v0.1
  - openai/gpt-oss-20b
  - deepseek/deepseek-r1-0528-qwen3-8b
  - qwen/qwen2.5-coder-14b
  - text-embedding-nomic-embed-text-v1.5
- Auto-detected: qwen/qwen2.5-coder-14b (matched "qwen")

---

## 🚀 Usage Examples

### Esempio 1: Ollama Auto-Start

```python
from oxide.core.orchestrator import Orchestrator
from oxide.config.loader import load_config

config = load_config()
orchestrator = Orchestrator(config)

# Ollama si avvierà automaticamente se non running
async for chunk in orchestrator.execute_task(
    prompt="Write a Python function",
    preferences={"preferred_service": "ollama_local"}
):
    print(chunk, end="")
```

### Esempio 2: LM Studio Zero-Config

```python
# Nessuna configurazione necessaria - auto-detect tutto
async for chunk in orchestrator.execute_task(
    prompt="Explain quantum computing",
    preferences={"preferred_service": "lmstudio"}
):
    print(chunk, end="")
```

### Esempio 3: Service Health Check

```python
from oxide.utils.service_manager import get_service_manager

sm = get_service_manager()

# Check se Ollama è healthy, auto-start se necessario
health = await sm.ensure_service_healthy(
    service_name="ollama_local",
    base_url="http://localhost:11434",
    api_type="ollama",
    auto_start=True
)

print(f"Healthy: {health['healthy']}")
print(f"Models: {health['models']}")
print(f"Recommended: {health['recommended_model']}")
```

---

## 🔧 Configuration Guide

### Configurazione Minima (Ollama)

```yaml
services:
  ollama_local:
    type: http
    base_url: "http://localhost:11434"
    api_type: ollama
    enabled: true
    auto_start: true          # Solo questo è necessario!
    auto_detect_model: true
```

### Configurazione Avanzata (LM Studio)

```yaml
services:
  lmstudio:
    type: http
    base_url: "http://192.168.1.33:1234/v1"
    api_type: openai_compatible
    enabled: true

    # Nessun default_model - auto-detect
    default_model: null
    auto_detect_model: true

    # Preferenze per smart selection
    preferred_models:
      - "qwen"           # Match: qwen/qwen2.5-coder-14b
      - "coder"          # Match: mistralai/codestral-22b
      - "deepseek"       # Match: deepseek/deepseek-r1

    # Retry configuration
    max_retries: 3
    retry_delay: 3
```

---

## 📁 Files Modified/Created

### New Files:
- `src/oxide/utils/service_manager.py` - Service lifecycle manager
- `scripts/test_ollama_integration.py` - Comprehensive integration tests
- `IMPROVEMENTS.md` - This documentation

### Modified Files:
- `src/oxide/adapters/ollama_http.py` - Enhanced adapter with auto-features
- `src/oxide/utils/logging.py` - Added get_logger() function
- `config/default.yaml` - Updated with new configuration options

---

## 🎯 Benefits

### Per Sviluppatori:

1. **Zero Setup Friction**:
   - No manual Ollama start
   - No model name configuration
   - Works out-of-the-box

2. **Resilience**:
   - Auto-recovery on failures
   - Smart retry logic
   - Service health monitoring

3. **Flexibility**:
   - Works con modelli diversi senza riconfigurare
   - Support per servizi remoti e locali
   - Facile aggiungere nuovi servizi

### Per Users:

1. **Seamless Experience**:
   - Servizi si avviano automaticamente
   - Nessun errore "service not available"
   - Sempre usa il miglior modello disponibile

2. **Performance**:
   - Caching riduce latenza
   - Parallel health checks
   - Lazy initialization

3. **Reliability**:
   - Automatic failover
   - Background monitoring
   - Smart recovery

---

## 🔮 Future Enhancements

### Prossimi Step Suggeriti:

1. **Multi-Service Load Balancing**
   - Distribuire tasks tra multiple istanze Ollama
   - Round-robin o least-loaded selection

2. **Model Performance Metrics**
   - Track latency per model
   - Auto-select modello più veloce

3. **Advanced Caching**
   - Cache responses per prompt comuni
   - Redis integration per cache distribuita

4. **Service Discovery**
   - Auto-detect servizi LLM sulla rete locale
   - mDNS/Avahi integration

5. **Webhook Notifications**
   - Alert quando servizio va down
   - Slack/Discord integration per monitoring

---

## 📞 Support

Per issues o domande:
- GitHub Issues: [oxide/issues](https://github.com/yourusername/oxide/issues)
- Email: esoglobine@gmail.com

---

**Last Updated**: 2025-12-26
**Version**: 0.2.0
**Author**: yayoboy + Claude Sonnet 4.5
