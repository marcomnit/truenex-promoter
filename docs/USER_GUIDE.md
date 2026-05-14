# Truenex Promoter — Guida Utente

> **Interfaccia: CLI (riga di comando).** Non ha GUI web né app desktop. Si usa dal terminale.

---

## 1. Cos'è Truenex Promoter

Un agente di marketing per progetti open-source che:
1. **Monitora** il tuo repo GitHub (stelle, issue, release)
2. **Trova** occasioni di promozione (Awesome Lists, social media)
3. **Genera** bozze di contenuto (post, PR, risposte)
4. **Chiede approvazione** prima di ogni azione
5. **Esegue** l'azione approvata (genera file pronto, apre browser)

---

## 2. Requisiti

- Python 3.11+
- Windows, macOS, o Linux
- Per LLM locale: NVIDIA GPU con 6GB+ VRAM (consigliata)
- Per LLM remoto: API key (OpenAI, DeepSeek, Kimi, ecc.)

---

## 3. Installazione

```bash
# Clona il repo
git clone https://github.com/marcomnit/truenex-promoter.git
cd truenex-promoter

# Installa in modalità editable
pip install -e .
```

---

## 4. Configurazione

Tutte le impostazioni si fanno con **variabili d'ambiente** (o valori di default).

### Configurazione base (obbligatoria)

```bash
# Il tuo repo da promuovere (default: Truenex Memory)
export TRUENEX_PROMOTER_OWNER=marcomnit
export TRUENEX_PROMOTER_REPO=truenex-memory
export TRUENEX_PROMOTER_GITHUB_TOKEN=ghp_xxx   # opzionale, per rate limit più alti
```

### Configurazione LLM locale (consigliata — Nemotron 4B)

```bash
# Scarica il modello (~3GB, una tantum)
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF', filename='NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf', local_dir='./models')"

# Configura
export TRUENEX_PROMOTER_LLM_PROVIDER=llamacpp
export TRUENEX_PROMOTER_LLM_MODEL_PATH="./models/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
export TRUENEX_PROMOTER_LLM_N_GPU_LAYERS=-1   # tutti i layer su GPU
```

### Configurazione LLM remoto (alternativa)

```bash
export TRUENEX_PROMOTER_LLM_PROVIDER=deepseek
export TRUENEX_PROMOTER_LLM_API_KEY=sk-xxx
export TRUENEX_PROMOTER_LLM_MODEL=deepseek-chat
```

---

## 5. Primo avvio (3 comandi)

### 5.1 Analizza hardware
```bash
python -m truenex_promoter --hardware
```
**Output:** rileva GPU, VRAM, RAM. Ti dice se puoi usare LLM locale o devi usare API.

### 5.2 Verifica LLM
```bash
python -m truenex_promoter --llm-check
```
**Output:** carica il modello, testa una generazione. Se ok, sei pronto.

### 5.3 Primo check GitHub
```bash
python -m truenex_promoter
```
**Output:** controlla il repo, genera azioni, mostra bozze.

---

## 6. Il flusso giornaliero (tipico)

### Mattina — Check
```bash
python -m truenex_promoter
```
Il promoter controlla GitHub e trova occasioni. Genera azioni in coda.

### Vedi cosa ha trovato
```bash
python -m truenex_promoter --queue
```
Mostra:
- **Pending**: azioni da approvare/rifiutare
- **Approved**: azioni pronte per l'esecuzione

### Approva una bozza
```bash
python -m truenex_promoter --approve abc12345 --reason "Mi piace"
```

### Esegui l'azione approvata
```bash
python -m truenex_promoter --execute abc12345
```
**Cosa fa:**
1. Genera un file con tutto il materiale pronto
2. Apre il browser sulla pagina giusta (LinkedIn, GitHub, ecc.)
3. Ti dice cosa copiare e dove incollarlo

### Rifiuta un'azione
```bash
python -m truenex_promoter --reject abc12345 --reason "Non pertinente"
```

---

## 7. Esempio pratico completo

### Scenario: hai rilasciato v0.1.0-alpha.1

**Passo 1 — Check**
```bash
$ python -m truenex_promoter
[09:41] INFO: Checking GitHub...
[09:41] EVENT: NEW_RELEASE — New release: v0.1.0-alpha.1
[09:41] ACTION PROPOSED (ID: d33fdda1)
  Title: Announce release v0.1.0-alpha.1
  Approve:  trnx-promoter --approve d33fdda1
  Reject:   trnx-promoter --reject d33fdda1
```

**Passo 2 — Vedi la coda**
```bash
$ python -m truenex_promoter --queue
Pending actions (1):
  ID:       d33fdda1
  Type:     social_post
  Title:    Announce release v0.1.0-alpha.1
  Approve:  trnx-promoter --approve d33fdda1
```

**Passo 3 — Approva**
```bash
$ python -m truenex_promoter --approve d33fdda1
[09:44] INFO: Approved action d33fdda1: Announce release v0.1.0-alpha.1
```

**Passo 4 — Esegui**
```bash
$ python -m truenex_promoter --execute d33fdda1
Executing: Announce release v0.1.0-alpha.1

✅ Done!
File: C:\Users\marco\.truenex-promoter\executions\social_post_d33fdda1.md
Browser opened to LinkedIn post composer
```

**Passo 5 — Copia e incolla**
Apri il file generato, copia il testo, incollalo su LinkedIn, posta.

---

## 8. Comandi CLI completi

| Comando | Cosa fa |
|---------|---------|
| `python -m truenex_promoter` | Check una volta |
| `python -m truenex_promoter --loop` | Check ogni ora (continuo) |
| `python -m truenex_promoter --status` | Stato ultimo check |
| `python -m truenex_promoter --queue` | Mostra azioni pending/approved |
| `python -m truenex_promoter --approve ID` | Approva azione |
| `python -m truenex_promoter --reject ID` | Rifiuta azione |
| `python -m truenex_promoter --execute ID` | Esegue azione approvata |
| `python -m truenex_promoter --llm-check` | Testa connettività LLM |
| `python -m truenex_promoter --hardware` | Analizza hardware |

---

## 9. Dove vengono salvati i dati

Tutto in `~/.truenex-promoter/`:
- `github_state.json` — stato monitoraggio
- `action_queue.json` — coda azioni
- `activity.log` — log attività
- `executions/` — file generati dagli esecutori

---

## 10. Interfaccia: solo CLI

**Non c'è GUI.** Il promoter è pensato per:
- Girare in background (`--loop`)
- Essere usato da terminale
- Integrarsi in script e CI/CD

In futuro (Pro/SaaS) potrebbe avere una dashboard web.

---

## 11. FAQ

**Q: Devo avere una GPU?**  
A: No. Puoi usare API remote (DeepSeek, OpenAI). La GPU serve solo per LLM locale.

**Q: Quanto costa?**  
A: Il core è gratis (open source). Se usi API remote, paghi il provider. Nemotron 4B locale è gratis.

**Q: Posso automatizzare completamente?**  
A: No (by design). L'agente propone, tu approvi. Questo evita spam e ban.

**Q: Supporta altri modelli?**  
A: Sì. Qualsiasi modello GGUF (Llama, Mistral, ecc.) o API OpenAI-compatibile.
