# Truenex Promoter

Autonomous AI marketing agent for open-source projects. Monitors your repo, discovers promotion opportunities, generates content drafts, and **asks for your approval before taking action**.

> **Human-in-the-loop by design.** The agent proposes, you decide. No automated posts, no spam, no surprises.

## Product Strategy: Open Core + Freemium UI

| Edition | Interface | What's included | Price |
|---|---|---|---|
| **OSS** | **CLI** (this repo) | Monitoring, queue, generators, LLM local/remote, hardware analyzer | **Free** |
| **Pro** | **Desktop UI** (Tauri) | System tray, dashboard, analytics, auto-executors | **$19/mo** |
| **Team** | **Desktop + Cloud** | Multi-repo, multi-user, sync | **$49/mo** |
| **Enterprise** | **SaaS Web** | Zero install, white-label, API, support | **Custom** |

The CLI is and will remain **open-source forever**. The UI is a closed-source paid add-on.

## Current Status

Alpha — dogfooding on [Truenex Memory](https://github.com/marcomnit/truenex-memory).

## What it does

1. **Monitors GitHub** — stars, issues, releases
2. **Detects milestones** — celebrates star milestones (10, 25, 50...)
3. **Discovers Awesome Lists** — finds relevant curated lists for your project
4. **Generates drafts** — PR descriptions, social posts, release announcements
5. **Queues for approval** — every action waits for your `approve` or `reject`

## Quick Start

```bash
# Install
pipx install truenex-promoter

# Configure (optional)
export TRUENEX_PROMOTER_OWNER=your-org
export TRUENEX_PROMOTER_REPO=your-repo

# Check once
python -m truenex_promoter

# Run continuously
python -m truenex_promoter --loop

# View pending actions
python -m truenex_promoter --queue

# Approve an action
python -m truenex_promoter --approve <action-id>

# Reject an action
python -m truenex_promoter --reject <action-id> --reason "not relevant"
```

## LLM Configuration

The promoter can use a local LLM (llama.cpp) or remote API.

### Local LLM (recommended: Nemotron 3 Nano 4B)

```bash
# Download Nemotron 4B Q4 (~3GB)
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF', filename='NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf', local_dir='./models')"

# Configure
export TRUENEX_PROMOTER_LLM_PROVIDER=llamacpp
export TRUENEX_PROMOTER_LLM_MODEL_PATH="./models/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf"
export TRUENEX_PROMOTER_LLM_N_GPU_LAYERS=-1

# Test
python -m truenex_promoter --llm-check
```

### Remote API (OpenAI, DeepSeek, Kimi)

```bash
export TRUENEX_PROMOTER_LLM_PROVIDER=deepseek
export TRUENEX_PROMOTER_LLM_API_KEY=sk-...
export TRUENEX_PROMOTER_LLM_MODEL=deepseek-chat
python -m truenex_promoter --llm-check
```

## Example Output

```
[2026-05-14 08:38:46 UTC] EVENT: NEW_RELEASE
Title: New release: v0.1.0-alpha.1
URL: https://github.com/marcomnit/truenex-memory/releases/tag/v0.1.0-alpha.1

[2026-05-14 08:38:46 UTC] ACTION PROPOSED (ID: 6696a400)
Title: Announce release v0.1.0-alpha.1
Approve:  trnx-promoter --approve 6696a400
Reject:   trnx-promoter --reject 6696a400

[2026-05-14 08:38:49 UTC] ACTION PROPOSED (ID: f15b266a)
Title: Propose addition to awesome-mcp-servers
Target: https://github.com/punkpeye/awesome-mcp-servers
```

## Architecture

```
trnx-promoter check
    -> github_monitor.check()      # fetch repo state
    -> content_generator           # draft posts/PRs
    -> action_queue.add()          # queue for approval
    -> notifier.action_proposed()  # notify user

User: trnx-promoter --approve ID
    -> action_queue.approve()      # mark approved
    -> (execution in future versions)
```

## License

Apache 2.0
