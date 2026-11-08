# PROJECT AURA — FREE & OPEN-SOURCE AI GIRLFRIEND WHATSAPP BOT

<div align="center">

![Project AURA Banner](static/images/aura_canonical_reference.jpg)

**An intelligent, realistic, emotionally attuned AI companion for WhatsApp built entirely with 100% free and open-source technologies.**

[![Python](https://img.shields.io/badge/Python-3.14%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API%20Official-25D366.svg)](https://developers.facebook.com/)
[![TTS](https://img.shields.io/badge/Voice-Edge--TTS%20Neural-purple.svg)](https://github.com/rany2/edge-tts)
[![STT](https://img.shields.io/badge/Speech--to--Text-Faster--Whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 🌟 Table of Contents

1. [Executive Summary](#-executive-summary)
2. [Permanent Character Identity (Aura)](#-permanent-character-identity-aura)
3. [Zero-Cost & Free/Open-Source Architecture](#-zero-cost--freeopen-source-architecture)
4. [WhatsApp Business Cloud API Integration](#-whatsapp-business-cloud-api-integration)
5. [Voice Conversation Engine](#-voice-conversation-engine)
6. [Consistent Image Generation System](#-consistent-image-generation-system)
7. [Long-Term Memory Engine](#-long-term-memory-engine)
8. [Multi-Provider AI Fallback Intelligence](#-multi-provider-ai-fallback-intelligence)
9. [Proactive Automation & Schedulers](#-proactive-automation--schedulers)
10. [Admin Dashboard & Live Simulator](#-admin-dashboard--live-simulator)
11. [Privacy & Security](#-privacy--security)
12. [Quickstart & Installation](#-quickstart--installation)
13. [Testing & Verification](#-testing--verification)

---

## 📖 Executive Summary

**Project AURA** is an end-to-end companion system connecting the official **WhatsApp Business Cloud API** to an intelligent multimodal AI engine.

Unlike traditional robotic support chatbots or brittle web-scraping wrappers, Project AURA:
- **Speaks Roman Urdu, English, Urdu, and natural code-switched mixes** fluently.
- **Maintains a single consistent, photorealistic visual identity** across all generated pictures, selfies, mirror selfies, and outfits.
- **Sends and understands voice notes** using open-source Whisper STT and Microsoft Edge-TTS neural speech synthesized into native WhatsApp OPUS audio.
- **Retains long-term memories** of the user's name, preferences, life stories, favorite things, and relationship milestones.
- **Proactively initiates conversations** with good morning greetings, sweet goodnight notes, and thoughtful check-ins when idle.
- **Eliminates mandatory subscription costs** by pairing official WhatsApp free-tier allocations (1,000 free service conversations per month) with free inference tiers (Groq, Google Gemini Flash, OpenRouter) and 100% offline local inference (Ollama).

---

## 👤 Permanent Character Identity (Aura)

Aura is a 21-year-old fictional young woman designed with emotional intelligence, affection, humor, and depth:

- **Archetype**: Loving, caring, playfully teasing, emotionally perceptive romantic companion.
- **Languages**: Roman Urdu (*"Kaisi ho jaan? Main kab se tumhara wait kar rahi thi..."*), English (*"I was just thinking about you, honestly. How was your day?"*), and natural Urdu/English code-switching.
- **Visual Features**:
  - Warm hazel-brown almond eyes.
  - Natural wavy dark brown hair.
  - Subtle, delicate beauty mark on her left cheekbone.
  - Radiant, natural South Asian glowing complexion with visible natural skin texture (never plastic).
  - Effortless contemporary aesthetic (floral dresses, casual cozy sweaters, traditional kurtis).
- **Identity Preservation System**:
  - Fixed seed anchor (`789234`) with micro-variation deltas for pose/outfit adjustments.
  - Fixed facial anchor descriptor injected into every rendering request.
  - Dedicated negative prompt shields against cartoonish, plastic, deformed, or multi-person renders.
  - Reference image cache saved at `static/images/aura_canonical_reference.jpg`.

---

## 🏗️ Zero-Cost & Free/Open-Source Architecture

```
Project_AURA/
├── .env.example                     # Environment template
├── config/
│   ├── settings.py                  # Pydantic BaseSettings & environment loader
│   └── persona.json                 # Aura's default persona & facial identity config
├── core/
│   ├── database.py                  # SQLite3 WAL database with connection manager
│   ├── models.py                    # Pydantic validation schemas
│   ├── security.py                  # Meta HMAC SHA-256 validation & Admin JWT
│   └── scheduler.py                 # APScheduler proactive greeting engine
├── services/
│   ├── ai/                          # Multi-Provider AI Abstraction
│   │   ├── base.py                  # BaseLLMProvider abstract interface
│   │   ├── groq_provider.py         # Groq Free Tier (Llama-3.3-70b-versatile)
│   │   ├── gemini_provider.py       # Google Gemini 2.0 / 1.5 Flash Free Tier
│   │   ├── ollama_provider.py       # Local Ollama 100% offline inference
│   │   ├── openrouter_provider.py   # OpenRouter Free Models fallback
│   │   └── router.py                # AI Router with fallback cascade & context builder
│   ├── voice/
│   │   ├── tts_service.py           # Microsoft Edge-TTS + FFmpeg OPUS converter
│   │   └── stt_service.py           # Faster-Whisper local speech-to-text
│   ├── image/
│   │   ├── generator.py             # Free Flux/SDXL image synthesis
│   │   ├── identity.py              # Identity consistency & facial anchor engine
│   │   └── scenes.py                # Scene preset dictionary (selfie, beach, outfit, etc.)
│   ├── memory/
│   │   └── memory_service.py        # Long-term semantic & episodic memory extraction
│   └── whatsapp/
│       ├── cloud_api.py             # WhatsApp Cloud API client (text, voice, image)
│       └── webhook_handler.py       # Webhook dispatcher & automation pipeline
├── api/
│   ├── whatsapp_routes.py           # Webhook verification & incoming event routes
│   └── admin_routes.py              # Admin Dashboard REST endpoints & Live Simulator
├── static/
│   ├── index.html                   # Modern glassmorphism SPA dashboard
│   ├── css/dashboard.css            # Dark mode glass styling
│   └── js/dashboard.js              # Interactive dashboard controller
├── tests/                           # 100% Passing automated test suite
├── main.py                          # FastAPI server entry point
└── requirements.txt                 # Dependencies
```

---

## 📱 WhatsApp Business Cloud API Integration

Project AURA strictly uses the **Official WhatsApp Business Cloud API** (Meta Graph API v21.0) rather than fragile, ban-prone unofficial WhatsApp Web browser scraping.

### 💰 Cost Clarification (100% Free Allocation)
- **Meta provides 1,000 free service conversations per month** for every WhatsApp Business Account.
- When a user sends a message to Aura on WhatsApp, it initiates a **24-hour service conversation window**. Within this window, all incoming and outgoing messages are completely free.
- No paid credit card is required to set up and run a developer test number on Meta for Developers.

### Webhook Verification & HMAC Signature
- **GET `/webhook`**: Handles Meta's webhook verification challenge (`hub.mode`, `hub.verify_token`, `hub.challenge`).
- **POST `/webhook`**: Secures inbound events by validating the `X-Hub-Signature-256` HMAC-SHA256 digest against `WHATSAPP_APP_SECRET`.

---

## 🎙️ Voice Conversation Engine

1. **Inbound Speech-to-Text (STT)**:
   - Powered by **Faster-Whisper** (CTranslate2-optimized local Whisper model).
   - Accurately transcribes spoken Roman Urdu, Urdu, Hindi, and English voice notes locally on CPU or GPU with zero API calls.
2. **Outbound Text-to-Speech (TTS)**:
   - Powered by **Microsoft Edge-TTS** (completely free, zero API key required, ultra-realistic human voices).
   - **Language-Aware Voice Selection**:
     - Automatically selects `ur-PK-UzmaNeural` or `hi-IN-SwaraNeural` when Roman Urdu or Urdu script is detected.
     - Automatically selects `en-US-AvaNeural`, `en-US-JennyNeural`, or `en-US-EmmaNeural` for English.
3. **WhatsApp Native OPUS Encoding**:
   - Meta WhatsApp Cloud API voice notes require OGG containers encoded with the **OPUS codec** at 16,000 Hz mono.
   - Built-in FFmpeg pipeline converts output into compliant voice notes automatically.

---

## 📸 Consistent Image Generation System

Aura understands requests for pictures naturally:
- *"Send me your selfie"* → Close-up front camera selfie with warm lighting.
- *"Show me your full outfit"* / *"Send me a picture in a beautiful dress"* → Full-body fashion portrait.
- *"Send me a picture at the beach"* → Golden hour sunset on the beach.
- *"Take a mirror selfie"* → Smartphone mirror selfie in cozy bedroom with fairy lights.
- *"Send me a smiling picture"* → Joyful candid close-up.

### Identity Preservation Engine:
1. **Facial Anchor Conditioning**: Every prompt automatically prepends Aura's immutable facial descriptors (warm hazel-brown eyes, wavy lustrous brown hair, subtle beauty mark on left cheekbone, glowing South Asian skin texture).
2. **Photographic Realism**: Composed with 85mm f/1.4 lens emulation, authentic raw camera profiles, natural lighting, and fine pore texture.
3. **Seed Anchoring**: Uses seed `789234` with controlled offsets to preserve bone structure while generating fresh poses and backgrounds.
4. **Backend Support**: Integrates with zero-cost Pollinations Flux / SDXL, HuggingFace Inference API, or local SD WebUI / ComfyUI.

---

## 🧠 Long-Term Memory Engine

Aura does not treat conversations as isolated ephemeral sessions:
- **Episodic & Semantic Memory**: Remembers user facts (name, nickname, profession, location), personal favorites (favorite foods, hobbies, songs), emotional milestones, and relationship intimacy.
- **Natural Weaving**: Memories are dynamically retrieved via keyword-relevance matching and injected into prompt context without awkward phrases like *"According to my memory"*.
- **User Control & Privacy**: Full CRUD operations in the Admin Dashboard to search, edit, or delete any memory item, plus a complete GDPR data wipe button.

---

## 🤖 Multi-Provider AI Fallback Intelligence

Project AURA never locks you into a single proprietary or paid provider:

| Provider | Model | Tier / Cost | Best For |
| :--- | :--- | :--- | :--- |
| **Groq** | `llama-3.3-70b-versatile` | Free Tier (console.groq.com) | Ultra-fast token generation, deep romance, Roman Urdu |
| **Google Gemini** | `gemini-2.0-flash` | Free Tier (aistudio.google.com) | Large context, multilingual code-switching |
| **Ollama** | `llama3:latest` | 100% Free / Self-Hosted | 100% offline, private, zero internet reliance |
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct:free` | Free Models | Backup cloud fallback |
| **Aura Offline Engine** | Built-in Heuristic | Zero Dependencies | Always available even if all external APIs are down |

**Automatic Fallback Cascade**: If the primary provider hits a rate limit (HTTP 429) or connection error, AIRouter instantly tries the next configured fallback seamlessly.

---

## ⏰ Proactive Automation & Schedulers

Aura feels like an attentive companion through scheduled background jobs powered by **APScheduler**:
- **Morning Greetings (9:00 AM)**: Sends a sweet, affectionate morning message in Roman Urdu or English.
- **Night Check-in (11:00 PM)**: Sends a tender bedtime message wishing sweet dreams.
- **Daytime Idle Ping**: If a user has been inactive for > 6 hours during daytime hours (11:00 AM – 8:00 PM), Aura gently checks in (*"Suno jaan... bohat der se baat nahi hui. Busy ho kya? Bas aise hi tumhari yaad aa rahi thi ❤️"*).

---

## 💻 Admin Dashboard & Live Simulator

Access the modern glassmorphism SPA dashboard at **`http://localhost:8000`**:

1. **Overview & Analytics**: Live counts of messages, voice notes, photos generated, remembered facts, and real-time activity stream.
2. **Live WhatsApp Simulator**: Chat directly with Aura in your browser with interactive message bubbles, inline generated photos, and playable voice note previews!
3. **Persona Studio**: Edit Aura's name, age, system prompt directives, facial anchor prompt, and negative prompt in real time.
4. **Memory Ledger**: View, filter, add, edit, or delete memories remembered about any user.
5. **Voice Studio**: Test and preview Edge-TTS female voices with speech rate and pitch sliders.
6. **Image Lab**: Test selfie, outfit, and beach prompts and inspect generated character photos.
7. **AI Provider Manager**: Switch primary AI provider with a single click and check provider health.
8. **Privacy Center**: Instantly purge any user's records with one click.

---

## 🔒 Privacy & Security

- **No Data Resale**: All conversation history and memories remain strictly inside your local SQLite database (`data/aura.db`).
- **Cryptographic Webhook Validation**: Verifies Meta's `X-Hub-Signature-256` HMAC header on every single webhook event.
- **Admin Authentication**: Protected by HS256 JWT tokens.
- **Rate Limiting**: Built-in sliding window rate limiter protects endpoints against brute-force attacks.
- **GDPR Compliant Data Purge**: `DELETE /api/admin/users/{user_id}/purge` permanently removes all messages, memories, and records for a user.

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.14)
- **FFmpeg** installed and accessible on PATH (for OPUS audio encoding)

### 2. Clone and Setup Environment
```bash
git clone https://github.com/your-username/Project_AURA.git
cd Project_AURA

# Create virtual environment (optional but recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Open `.env` and fill in:
- `GROQ_API_KEY` (Free from [console.groq.com](https://console.groq.com)) or `GEMINI_API_KEY` (Free from [aistudio.google.com](https://aistudio.google.com))
- If connecting WhatsApp: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`

*(Note: If no API keys are provided initially, Aura runs on her built-in companion fallback engine and the web simulator works immediately!)*

### 4. Start Project AURA Server
```bash
python main.py
```
Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will start at:
- **Admin Dashboard & Live Simulator**: [http://localhost:8000](http://localhost:8000)
- **API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Default Admin Credentials**: Username: `admin` | Password: `aura2026_change_me`

---

## 🧪 Testing & Verification

Project AURA includes a comprehensive automated test suite covering database operations, memory extraction, AI action parsing, Edge-TTS audio synthesis, image identity anchoring, and webhook security.

Run all tests with:
```bash
python -m unittest discover tests
```

---

<div align="center">
<b>Project AURA — Designed & Built with ❤️ for Natural, Respectful AI Companionship</b>
</div>
