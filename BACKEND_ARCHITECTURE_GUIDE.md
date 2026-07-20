# FinSight AI — Comprehensive Backend Engineering & Architecture Masterclass
> A complete, interview-ready guide covering FastAPI, Async I/O, OOP, ACID, SOLID principles, Celery background workers, multi-tier data pipelines, and AI semi-agent guardrails.

---

## Table of Contents
1. [Executive System Overview](#1-executive-system-overview)
2. [FastAPI & Async Python Fundamentals](#2-fastapi--async-python-fundamentals)
3. [Database Architecture & ACID Properties](#3-database-architecture--acid-properties)
4. [Object-Oriented Programming (OOP) & SQLAlchemy 2.0](#4-object-oriented-programming-oop--sqlalchemy-20)
5. [Async Task Queue: Celery + Redis Worker Architecture](#5-async-task-queue-celery--redis-worker-architecture)
6. [Multi-Tier Data & AI Semi-Agent Pipeline](#6-multi-tier-data--ai-semi-agent-pipeline)
7. [SOLID Software Design Principles in FinSight AI](#7-solid-software-design-principles-in-finsight-ai)
8. [Authentication, Security & JWT Flow](#8-authentication-security--jwt-flow)
9. [File-by-File Codebase Walkthrough](#9-file-by-file-codebase-walkthrough)
10. [Backend Interview Prep Q&A](#10-backend-interview-prep-qa)

---

## 1. Executive System Overview

FinSight AI is a **production-grade financial report generation system** built for retail investors in India. 

### Why is this built asynchronously?
Generating an AI financial report involves:
1. Fetching live prices and OHLC candles from external APIs (**Finnhub, Groww**).
2. Fetching macroeconomic indicators (**FRED: US 10Y Yield, DXY, VIX, Fed Rates**).
3. Fetching Indian equity market flows (**nsepython: FII/DII net flows, Nifty 50**).
4. Gathering recent market news (**NewsAPI**).
5. Passing structured JSON to an LLM (**OpenRouter Llama 3.3 70B**) to write financial analysis.
6. Rendering a 5-page formatted Word document (**python-docx**).
7. Uploading the file to cloud storage (**Supabase Storage**).

If this were built synchronously in a standard Web server (like Django or Flask without Celery), a single report request would block the server thread for 15–30 seconds, leading to **HTTP timeouts, server crashes, and horrible user experience**.

### System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         FastAPI Web Server                       │
│  - POST /auth/register   - POST /auth/login                      │
│  - POST /reports/generate (Queues Celery task & returns immediately)│
│  - GET  /reports/{id}      (Polls database for completion status)│
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ 1. Enqueue Task (JSON Payload)
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Upstash Redis (Task Broker)                  │
│                     Queue: "celery" (SSL encrypted)              │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ 2. Dequeue Task & Process Concurrently
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Celery Worker Process                       │
│  - Executes run_async(get_commodity_data / get_equity_data)      │
│  - Calls OpenRouter (Llama 3.3 70B) via OpenAI SDK               │
│  - Builds styled .docx file in-memory using BytesIO              │
│  - Uploads .docx to Supabase Storage                             │
│  - Updates PostgreSQL database status to "completed"             │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 │ 3. Query & Cache Data
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                Supabase PostgreSQL Database                      │
│  - Tables: users, reports, watchlists, cached_data               │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. FastAPI & Async Python Fundamentals

### What is FastAPI and why did we choose it?
FastAPI is a modern, high-performance Python web framework based on **ASGI (Asynchronous Server Gateway Interface)**, **Pydantic v2**, and **Starlette**.

Key Reasons:
- **ASGI Native**: Unlike WSGI frameworks (like Flask or Django 2.x), FastAPI runs natively on an asynchronous event loop (`uvicorn`), allowing thousands of concurrent idle connections.
- **Pydantic Data Validation**: Automatic request parsing, type validation, and serialization. If a client sends `"asset_type": 123` instead of a string, Pydantic automatically rejects it with HTTP `422 Unprocessable Entity`.
- **Automatic OpenAPI (Swagger) Docs**: Intersecting Python type hints generates interactive API documentation at `/docs`.
- **Built-in Dependency Injection System**: `Depends()` allows clean code reuse for DB sessions (`Depends(get_db)`) and JWT Auth (`Depends(get_current_user)`).

### `async` / `await` and Non-Blocking I/O
In Python, synchronous requests (like `requests.get()`) freeze the CPU thread while waiting for a network response (IO-bound).

In FinSight AI, we use `httpx.AsyncClient` and `asyncio.gather()`:
```python
# Synchronous (SLOW: 1 + 1 + 1 = 3 seconds total)
quote = fetch_quote()
candles = fetch_candles()
news = fetch_news()

# Asynchronous with asyncio.gather (FAST: runs concurrently in ~1 second)
quote, candles, news = await asyncio.gather(
    _fh_quote(symbol),
    _fh_candles(symbol, days=365),
    get_news(f"{symbol} commodity price", page_size=6)
)
```
- **`async def`**: Declares a coroutine function that can be paused when waiting for I/O.
- **`await`**: Hands control back to the event loop while waiting for external I/O (network calls, database queries).

---

## 3. Database Architecture & ACID Properties

FinSight AI uses **PostgreSQL** hosted on **Supabase**, connected asynchronously using **SQLAlchemy 2.0** and the `asyncpg` driver.

### ACID Properties & How We Enforce Them

| ACID Principle | Definition | Implementation in FinSight AI (`models/database.py` & `main.py`) |
| :--- | :--- | :--- |
| **Atomicity** | All operations in a transaction succeed together, or all fail together. | Enforced in `get_db()` generator via `async with session:` and `try...except`. If any database error occurs during report creation or user signup, `await session.rollback()` undoes all partial writes. |
| **Consistency** | Data must move from one valid state to another, obeying table constraints. | Foreign keys (`ForeignKey("users.id")`), `unique=True` on `users.email` and `cached_data.cache_key`, and Pydantic validation before SQL execution. |
| **Isolation** | Concurrent transactions execute without interfering with each other. | Enforced by PostgreSQL MVCC (Multi-Version Concurrency Control) and SQLAlchemy's `async_sessionmaker(expire_on_commit=False)`. |
| **Durability** | Once committed, data persists even during server crashes. | Enforced when `await db.commit()` sends changes to PostgreSQL's Write-Ahead Log (WAL). |

### Code Example: Atomicity in `main.py`
```python
@app.post("/reports/generate")
async def generate(body: GenerateReportRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    report_id = str(uuid.uuid4())
    report = Report(
        id=report_id,
        user_id=current_user.id,
        asset_type=body.asset_type,
        asset_symbol=body.asset_symbol.upper(),
        status="queued"
    )
    db.add(report)
    await db.flush()   # Flushes record to SQL session (allocating locks & checking constraints)

    # Queue Celery task
    task = generate_report.delay(report_id, body.asset_type, ...)
    report.celery_task_id = task.id
    
    await db.commit()  # Atomic Commit: Both report row AND celery_task_id are permanently written
```

---

## 4. Object-Oriented Programming (OOP) & SQLAlchemy 2.0

SQLAlchemy 2.0 uses modern Python 3.10+ class annotations for Object-Relational Mapping (ORM).

### The Declarative Base & Entity Classes (`backend/models/database.py`)

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func

class Base(DeclarativeBase):
    """Abstract Base Class for all Database Models"""
    pass

class User(Base):
    __tablename__ = "users"

    # Encapsulation & Type Mapping
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    tier: Mapped[str] = mapped_column(String(50), default="free")

    # One-to-Many Relationship (OOP Navigation Property)
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="user")
```

### OOP Core Principles Applied:
1. **Encapsulation**: Models (`User`, `Report`, `Watchlist`, `CachedData`) bundle data attributes and database behavior together.
2. **Inheritance**: All models inherit from `Base` (`DeclarativeBase`), giving them SQLAlchemy ORM query powers, table metadata, and schema generation capabilities.
3. **Abstraction**: `main.py` query logic does not write raw SQL strings like `SELECT * FROM users WHERE email = '...'`. Instead, it uses type-safe Python abstractions:
   ```python
   result = await db.execute(select(User).where(User.email == body.email))
   user = result.scalar_one_or_none()
   ```

---

## 5. Async Task Queue: Celery + Redis Worker Architecture

### Why do we need Celery?
FastAPI handles incoming web requests. If a request handler spends 20 seconds doing LLM generation, the HTTP client connection remains hanging. Celery allows us to **decouple request acceptance from heavy background computation**.

### Key Components

1. **Producer (`main.py`)**:
   - The FastAPI endpoint creates a report entry in PostgreSQL (`status="queued"`).
   - Calls `generate_report.delay(...)`, which pushes a JSON payload onto the Redis queue.
   - Immediately returns HTTP 200 with `{ "report_id": "...", "status": "queued" }`. Response time is **< 50 milliseconds**.

2. **Message Broker (Upstash Redis)**:
   - In-memory data store acting as the message bus between FastAPI and Celery.
   - Uses TLS/SSL (`rediss://...`) in production.

3. **Consumer Worker (`tasks/report_task.py`)**:
   - Background Python process running `celery -A tasks.celery_app.celery_app worker`.
   - Constantly polls Redis for incoming tasks.
   - When a task is dequeued:
     1. Updates report status to `"processing"`.
     2. Fetches market data asynchronously.
     3. Calls OpenRouter LLM.
     4. Generates `.docx` file using `docx_builder.py`.
     5. Uploads `.docx` file to Supabase Storage.
     6. Updates report status to `"completed"` with public file URL.

---

## 6. Multi-Tier Data & AI Semi-Agent Pipeline

To prevent hallucination, save cost, and avoid API rate limits, FinSight AI uses a **3-Tier Data & Agent Architecture**:

```
 ┌─────────────────────────────────────────────────────────────┐
 │  Tier 1: Live APIs (Finnhub, Groww TOTP, FRED, nsepython)   │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Cache Write
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  Tier 2: Postgres/Supabase Cache (cached_data table)        │
 │          - Commodity TTL: 6h  - Equity TTL: 1h               │
 │          - FRED TTL: 24h      - News TTL: 30m                │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Structured JSON Output Only
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  Tier 3: OpenRouter LLM (Meta Llama 3.3 70B Instruct)       │
 │          - Anti-hallucination prompt prefix                  │
 │          - If metric is None → Writes "Data unavailable"    │
 └─────────────────────────────────────────────────────────────┘
```

### Why Semi-Agent / Deterministic AI?
Full autonomous agents (which search the web freely or generate code dynamically) are prone to financial hallucinations. FinSight AI uses a **Semi-Agent Architecture**:
- **Deterministic Tool Layer (`data_fetcher.py`)**: Fetches exact numbers (RSI-14, 52W High, DXY, US 10Y Yield) from trusted financial APIs.
- **LLM Reasoning Layer (`llm_analyst.py`)**: Acts purely as a senior financial analyst writing commentary on the **exact numbers provided in prompt context**.

### Anti-Hallucination Guardrail Prompt (`llm_analyst.py`)
```python
STRICT_PREFIX = """
STRICT DATA RULES (follow without exception):
- Only use the exact numbers provided below. Do not estimate or infer any value.
- If a metric shows None or is missing, write "Data unavailable" for that point.
- Do not use your training knowledge to fill in prices, ratios, or economic figures.
- All numbers in your report must come directly from the data provided below.
"""
```

---

## 7. SOLID Software Design Principles in FinSight AI

| SOLID Principle | Meaning | How It Is Applied in FinSight AI |
| :--- | :--- | :--- |
| **Single Responsibility (SRP)** | A module should have one, and only one, reason to change. | - `auth.py`: Handles ONLY password hashing & JWT tokens.<br>- `data_fetcher.py`: Handles ONLY raw data retrieval & caching.<br>- `llm_analyst.py`: Handles ONLY prompt formatting & OpenRouter calls.<br>- `docx_builder.py`: Handles ONLY Word document layout rendering.<br>- `report_task.py`: Handles ONLY Celery worker execution. |
| **Open/Closed (OCP)** | Software entities should be open for extension, but closed for modification. | The system supports multi-asset reports (`commodity`, `equity`). Adding a 3rd asset type (e.g. `options` or `crypto`) only requires adding a new builder function without altering auth, routing, database schemas, or Celery task definitions. |
| **Liskov Substitution (LSP)** | Subtypes must be substitutable for their base types. | SQLAlchemy models (`User`, `Report`, `Watchlist`) inherit from `Base` (`DeclarativeBase`) and can be passed seamlessly into generic session operations like `db.add()`, `db.delete()`, or `db.flush()`. |
| **Interface Segregation (ISP)** | Clients shouldn't be forced to depend on methods they do not use. | Data fetcher helper functions are isolated (`get_commodity_data()`, `get_equity_data()`, `get_macro_snapshot()`) so reports only load the exact data footprint they need. |
| **Dependency Inversion (DIP)** | High-level modules should depend on abstractions, not concrete implementations. | FastAPI routes (`main.py`) do not instantiate database connections directly. They depend on abstract generator functions injected via `Depends(get_db)` and `Depends(get_current_user)`. |

---

## 8. Authentication, Security & JWT Flow

FinSight AI uses **OAuth2 with Password Bearer Tokens** and **JSON Web Tokens (JWT)** for stateless authentication.

### Security Stack:
- **Password Hashing**: `passlib[bcrypt]`. Passwords are salted and hashed before hitting the database. Plain text passwords are NEVER stored.
- **JWT Signature**: `python-jose` creates signed tokens using `HS256` algorithm and `SECRET_KEY`.
- **Stateless Verification**: Every protected route (`/reports/generate`, `/reports`, `/auth/me`) includes `current_user: User = Depends(get_current_user)`.

```
Client (Frontend)                   FastAPI Server                     PostgreSQL
      │                                   │                                 │
      │ 1. POST /auth/login (email, pass) │                                 │
      ├──────────────────────────────────►│                                 │
      │                                   │ 2. Query user by email          │
      │                                   ├────────────────────────────────►│
      │                                   │◄────────────────────────────────┤
      │                                   │ 3. Verify password hash (bcrypt)│
      │                                   │ 4. Encode JWT (sub=user_id, exp)│
      │ 5. Return access_token            │                                 │
      │◄──────────────────────────────────┤                                 │
      │                                   │                                 │
      │ 6. GET /reports (Header: Bearer)  │                                 │
      ├──────────────────────────────────►│                                 │
      │                                   │ 7. Decode JWT & query user_id   │
      │                                   ├────────────────────────────────►│
      │                                   │◄────────────────────────────────┤
      │ 8. Return user's reports          │                                 │
      │◄──────────────────────────────────┤                                 │
```

---

## 9. File-by-File Codebase Walkthrough

```
backend/
├── main.py              # FastAPI app initialization, routes (Auth & Reports), CORS, Rate Limiting
├── core/
│   ├── config.py        # Pydantic BaseSettings loading environment variables from .env
│   └── auth.py          # Password hashing (bcrypt), JWT creation & get_current_user dependency
├── models/
│   └── database.py      # SQLAlchemy 2.0 async engine, AsyncSession factory, ORM Models (User, Report, etc.)
├── agents/
│   ├── data_fetcher.py  # Tier 1 Live APIs (Finnhub, Groww, FRED, nsepython) + Tier 2 Cache Layer
│   └── llm_analyst.py   # Tier 3 OpenRouter LLM analysis & multi-model fallback execution
├── report_builder/
│   └── docx_builder.py  # python-docx document styling, cover page, tables & disclaimers
├── tasks/
│   ├── celery_app.py    # Celery app initialization with Upstash Redis SSL configuration
│   └── report_task.py   # Background worker task logic (fetches data, calls LLM, builds docx, uploads to Supabase)
├── alembic/             # Alembic database migration scripts (001_initial.py)
├── requirements.txt     # Python production dependencies
└── Procfile             # Railway web & worker process commands
```

---

## 10. Backend Interview Prep Q&A

### Q1: Why did you use Celery instead of FastAPI background tasks (`BackgroundTasks`)?
> **Answer**: FastAPI `BackgroundTasks` run inside the same Python process and event loop as the web server. If 50 users request reports at once, CPU-intensive tasks like document formatting and long LLM calls would saturate the web server's event loop and block HTTP request handling. Celery offloads work to a separate, horizontally scalable worker process communicating over a dedicated message queue (Redis).

### Q2: How do you handle database connection pooling in an async Python environment?
> **Answer**: We use SQLAlchemy 2.0's `create_async_engine` with `asyncpg` as the driver. We configure a pool size of 10 connections with a `max_overflow` of 20. In route handlers, we use an async generator (`get_db`) with `async_sessionmaker(expire_on_commit=False)`, ensuring each HTTP request gets its own isolated session that is automatically committed or rolled back and closed.

### Q3: How do you prevent AI hallucinations in a financial product?
> **Answer**: We enforce a strict 3-tier architecture. Tier 1 fetches verified numerical data from APIs (Finnhub, FRED, Groww). Tier 2 caches the data. Tier 3 (the LLM) is provided with an explicit system prompt prefix forbidding it from using internal memory for numbers or estimating missing data. If a field is `None`, the LLM is instructed to explicitly output "Data unavailable".

### Q4: How do you handle database connection string differences between environments?
> **Answer**: Supabase and Railway supply PostgreSQL URLs starting with `postgresql://` or `postgres://`. SQLAlchemy's async engine requires `postgresql+asyncpg://`. In `database.py`, we automatically sanitize and convert the incoming URI string before passing it to `create_async_engine`.
