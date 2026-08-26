# Hybrid Telegram Bot & Live Customer Support System - FastAPI Backend

Production-ready, enterprise-grade FastAPI backend built with **SQLModel (Async SQLAlchemy)**, **Redis (Async State & Pub/Sub)**, **Telegram Webhooks**, and **WebSockets** for Next.js support agent dashboard integrations.

---

## 🏗️ Architecture & Project Structure

The project strictly follows Clean Layered Architecture: **API (Controllers) → Services (Business Logic) → Repositories (Data Access) → SQLModel Entities**.

```
chat_bot_backend/
├── app/
│   ├── api/                   # Async API Layer (Controllers & WebSockets)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py          # Agent Authentication (JWT)
│   │   │   │   ├── telegram.py      # Telegram Webhook & Callback Router
│   │   │   │   ├── conversations.py # REST APIs for Agent Dashboard
│   │   │   │   └── websocket.py     # Real-time WebSocket streaming
│   │   │   └── router.py            # API v1 Router Aggregator
│   ├── core/                  # Core Infrastructure & Settings
│   │   ├── config.py                # Pydantic BaseSettings (.env loader)
│   │   ├── database.py              # Async SQLModel Engine & Session generator
│   │   ├── redis.py                 # Async Redis Connection Pool
│   │   └── security.py              # Password Hashing (bcrypt) & JWT Tokens
│   ├── middlewares/               # Custom FastAPI Middlewares
│   │   ├── cors.py                  # Next.js Dashboard Cross-Origin handler
│   │   ├── logging.py               # Request Logging & Execution timing header
│   │   └── telegram_auth.py         # Telegram Secret Token verification
│   ├── models/                # SQLModel Entities / Database Tables
│   │   ├── user.py                  # User (Telegram profile)
│   │   ├── agent.py                 # Support Agent
│   │   ├── conversation.py          # Conversation / Ticket Session
│   │   └── message.py               # Message History
│   ├── repositories/          # Async Repository Data Access Layer
│   │   ├── base.py                  # BaseRepository[T] generic Async CRUD
│   │   ├── user_repository.py       # User Data Access
│   │   ├── agent_repository.py      # Agent Data Access
│   │   ├── conversation_repository.py # Ticket Data Access
│   │   └── message_repository.py    # Message Data Access
│   ├── schemas/               # Pydantic DTOs & Webhook Payloads
│   │   ├── telegram.py              # Telegram payload schemas
│   │   ├── conversation.py          # REST & WebSocket DTOs
│   │   ├── agent.py                 # Auth DTOs
│   │   └── common.py              # Standard API response wrappers
│   ├── services/              # Async Business Services Layer
│   │   ├── state_manager.py         # Redis Session State Tracker
│   │   ├── telegram_service.py      # Telegram Bot API Client (httpx)
│   │   ├── conversation_service.py  # Ticket lifecycle & handoff logic
│   │   └── websocket_manager.py     # Realtime WebSocket & Redis PubSub relay
│   └── main.py                # FastAPI Application Entrypoint & Lifespan
├── tests/                     # Async Pytest Suite
├── .env.example               # Environment variable blueprint
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Full-stack orchestrator (Postgres + Redis + API)
└── requirements.txt           # Dependency requirements
```

---

## ⚡ Key Features

1. **State-Based Handoff**: Tracks Telegram user states in Redis (`BOT_ACTIVE` ↔ `PENDING_AGENT` ↔ `HUMAN_ACTIVE` ↔ `CLOSED`).
2. **Dual Agent Workflows**: Supports claiming tickets via **Telegram Staff Group** (`[Claim Ticket]` inline keyboard) AND **Next.js Web Dashboard** REST/WebSocket APIs.
3. **100% Async Stack**: Async SQLModel engine (`asyncpg` / `aiosqlite`), async Redis (`redis.asyncio`), and async HTTP requests (`httpx.AsyncClient`).
4. **Repository Pattern**: Decouples data fetching from business logic for testability and maintainability.
5. **Real-time WebSockets**: Streams messages to Next.js agents instantly with Redis Pub/Sub multi-node broadcasting.

---

## 🚀 Quickstart & Installation

### 1. Local Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

Default Admin Account seeded on startup:
- **Email:** `admin@support.com`
- **Password:** `AdminSecret123!`

### 2. Docker Setup
```bash
docker-compose up -d --build
```

---

## 📡 API Endpoints Summary

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Agent JWT Login | No |
| `POST` | `/api/v1/auth/register` | Register Support Agent | No |
| `GET` | `/api/v1/auth/me` | Current Agent Profile | Yes (Bearer) |
| `POST` | `/api/v1/telegram/webhook` | Telegram Webhook Handler | Secret Header |
| `GET` | `/api/v1/conversations` | List Support Tickets (Filterable) | Yes (Bearer) |
| `GET` | `/api/v1/conversations/{id}` | Conversation Details & Messages | Yes (Bearer) |
| `POST` | `/api/v1/conversations/{id}/claim` | Claim Support Ticket | Yes (Bearer) |
| `POST` | `/api/v1/conversations/{id}/close` | Close Support Ticket | Yes (Bearer) |
| `POST` | `/api/v1/conversations/{id}/messages` | Send Message to Telegram User | Yes (Bearer) |
| `WS` | `/api/v1/ws/chat/{id}` | Live Chat WebSocket Stream | Agent ID |
# chat-bot-backend
