---
phase: 1
plan: foundation
type: standard
wave: 1
depends_on: []
files_modified: []
autonomous: false
requirements: []
---

# Phase 1: Foundation — Plan

**Goal:** Establish the test project foundation using Python, FastAPI, PostgreSQL, and Docker.

## Tasks

### 1. Python Project Scaffolding

**Wave:** 1
**Depends on:** —
**Files modified:** `pyproject.toml`, `.python-version`, `.venv/`

<read_first>
- `.planning/STATE.md`
- `.planning/REQUIREMENTS.md`
</read_first>

<acceptance_criteria>
- `pyproject.toml` exists with name, version, and Python dependency entries for fastapi, uvicorn, asyncpg, sqlalchemy, python-dotenv, pytest, pytest-asyncio
- `.python-version` contains `3.11`
- `.venv/` created via `python3.11 -m venv .venv`
- `pip install -e .` completes without error
- `python -c "import fastapi; import asyncpg"` succeeds inside venv
</acceptance_criteria>

<action>
Create the following files in the project root:

**`pyproject.toml`** — Poetry-style project metadata:
```toml
[project]
name = "test-project"
version = "0.1.0"
description = "Test project"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.110.0",
  "uvicorn[standard]>=0.27.0",
  "asyncpg>=0.29.0",
  "sqlalchemy[asyncio]>=2.0.25",
  "python-dotenv>=1.0.0",
  "pydantic>=2.0",
  "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "httpx>=0.27",
  "ruff>=0.3",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

**`.python-version`** — `3.11`

Run:
```bash
python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
```
</action>

---

### 2. FastAPI Application Initialization

**Wave:** 1
**Depends on:** 1
**Files modified:** `src/__init__.py`, `src/main.py`, `src/config.py`, `src/models/__init__.py`, `src/schemas/__init__.py`

<read_first>
- `pyproject.toml` (already created in task 1)
</read_first>

<acceptance_criteria>
- `src/main.py` contains `app = FastAPI()` and a root `/` route returning `{"status": "ok"}`
- `src/config.py` contains a `Settings` class using `pydantic-settings` with `DATABASE_URL`, `APP_NAME`, `DEBUG`
- `src/config.py` loads from `.env` via `python-dotenv`
- `uvicorn src.main:app --reload` starts without import errors
- `curl http://localhost:8000/` returns `{"status": "ok"}`
- `src/models/__init__.py` and `src/schemas/__init__.py` are empty (placeholder packages)
</acceptance_criteria>

<action>
Create the following files:

**`src/__init__.py`** — empty

**`src/config.py`**:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "TestProject"
    DEBUG: bool = False
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/testdb"
```

**`src/main.py`**:
```python
from fastapi import FastAPI
from src.config import Settings

settings = Settings()
app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)


@app.get("/")
def root():
    return {"status": "ok"}
```

**`src/models/__init__.py`** — empty

**`src/schemas/__init__.py`** — empty

Create `src/` directory structure and run the app to verify:
```bash
mkdir -p src/models src/schemas
touch src/__init__.py src/models/__init__.py src/schemas/__init__.py
uvicorn src.main:app --reload --port 8000 &
sleep 3
curl http://localhost:8000/
```
</action>

---

### 3. PostgreSQL Database Configuration

**Wave:** 1
**Depends on:** 2
**Files modified:** `src/database.py`, `.env.example`, `.env`

<read_first>
- `src/config.py` (already created in task 2)
</read_first>

<acceptance_criteria>
- `src/database.py` exports `engine`, `get_session`, `init_db`
- `engine` is an `AsyncEngine` from `sqlalchemy.ext.asyncio`
- `DATABASE_URL` is read from `settings.DATABASE_URL`
- `get_session` is an async context manager yielding an `AsyncSession`
- `init_db()` calls `async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)`
- `.env.example` contains `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/testdb`
- `python -c "from src.database import engine, get_session; print('OK')"` runs without error
</acceptance_criteria>

<action>
**`src/database.py`**:
```python
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import settings

Base = declarative_base()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**`.env.example`**:
```
APP_NAME=TestProject
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/testdb
```
</action>

---

### 4. Docker and Docker Compose Setup

**Wave:** 1
**Depends on:** —
**Files modified:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`

<read_first>
- `pyproject.toml` (already created in task 1)
</read_first>

<acceptance_criteria>
- `Dockerfile` builds without error (`docker build -t test-project .`)
- `docker-compose.yml` defines `app` and `db` services
- `db` service uses `postgres:16-alpine` image with env `POSTGRES_DB=testdb`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`
- `app` service: builds from `.`, exposes `8000:8000`, depends on `db`, runs `uvicorn src.main:app --host 0.0.0.0 --port 8000`
- `app` has `DATABASE_URL`, `DEBUG`, `APP_NAME` environment variables
- `docker-compose up -d` starts both services without error
- `docker-compose ps` shows both services `Up`
- `docker-compose down` stops cleanly
</acceptance_criteria>

<action>
**`Dockerfile`**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .python-version ./
RUN pip install --no-cache-dir -e .

COPY src/ ./src/

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`.dockerignore`**:
```
__pycache__
*.pyc
.venv/
.env
.git/
*.md
```

**`docker-compose.yml`**:
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/testdb
      - DEBUG=false
      - APP_NAME=TestProject
    volumes:
      - ./src:/app/src

volumes:
  pgdata:
```
</action>

---

### 5. Test Framework Setup

**Wave:** 1
**Depends on:** 3
**Files modified:** `tests/__init__.py`, `tests/conftest.py`, `tests/test_main.py`

<read_first>
- `src/main.py` (already created in task 2)
- `src/database.py` (already created in task 3)
</read_first>

<acceptance_criteria>
- `tests/conftest.py` defines a `pytest_asyncio.fixture` named `async_client` providing an `httpx.AsyncClient` hitting `app`
- `tests/test_main.py` contains `pytest.mark.asyncio` test `test_root()` that asserts `response.status_code == 200` and `response.json() == {"status": "ok"}`
- `pytest tests/` exits with code 0
- `ruff check .` exits with code 0 (no lint errors)
</acceptance_criteria>

<action>
**`tests/__init__.py`** — empty

**`tests/conftest.py`**:
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

**`tests/test_main.py`**:
```python
import pytest


@pytest.mark.asyncio
async def test_root(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

Run:
```bash
source .venv/bin/activate && pytest tests/ && ruff check .
```
</action>

---

### 6. Environment Variable Management

**Wave:** 1
**Depends on:** 3
**Files modified:** `.env.example`

<read_first>
- `src/config.py` (already created in task 2)
- `tests/conftest.py` (already created in task 5)
</read_first>

<acceptance_criteria>
- `.env.example` exists with all env vars: `APP_NAME`, `DEBUG`, `DATABASE_URL`
- `src/config.py` reads `.env` via `BaseSettings.model_config = SettingsConfigDict(env_file=".env", ...)`
- `.env` is listed in `.gitignore`
- `.env.example` is tracked in git
- `python -c "from src.config import Settings; s = Settings(); print(s.APP_NAME)"` works (uses .env or defaults)
</acceptance_criteria>

<action>
**`.env.example`**:
```
APP_NAME=TestProject
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/testdb
```

Append to existing `.gitignore`:
```
.env
```

Verify:
```bash
git check-ignore .env && echo "ignored" || echo "NOT ignored — add .env to .gitignore"
grep -q ".env" .gitignore && echo ".env in .gitignore" || echo ".env NOT in .gitignore"
```
</action>

---

## Verification Criteria

- [ ] `pyproject.toml` installs without error inside `.venv`
- [ ] `uvicorn src.main:app --reload` starts without import errors
- [ ] `curl http://localhost:8000/` returns `{"status": "ok"}`
- [ ] `src/database.py` exports `engine`, `get_session`, `init_db` and imports succeed
- [ ] `Dockerfile` builds: `docker build -t test-project .`
- [ ] `docker-compose up -d` starts `app` and `db` services
- [ ] `docker-compose ps` shows both services `Up`
- [ ] `docker-compose down` stops cleanly
- [ ] `pytest tests/` exits with code 0
- [ ] `ruff check .` exits with code 0
- [ ] `.env.example` is tracked in git; `.env` is ignored

## must_haves

- Python 3.11 virtual environment with `fastapi`, `uvicorn`, `asyncpg`, `sqlalchemy`, `pydantic-settings`
- FastAPI app with root `/` route returning `{"status": "ok"}`
- PostgreSQL async engine via `sqlalchemy.ext.asyncio.create_async_engine`
- `get_session` async context manager
- Docker + Docker Compose with `app` and `db` services; `db` healthcheck; `app` depends on `db` being healthy
- pytest + pytest-asyncio + httpx test with `test_root`
- ruff linting passing
- `.env.example` with `APP_NAME`, `DEBUG`, `DATABASE_URL`; `.env` in `.gitignore`

---

## Artifacts this phase produces

| Artifact | Type |
|----------|------|
| `pyproject.toml` | File |
| `.python-version` | File |
| `src/__init__.py` | File |
| `src/main.py` | File |
| `src/config.py` | File |
| `src/database.py` | File |
| `src/models/__init__.py` | File |
| `src/schemas/__init__.py` | File |
| `Dockerfile` | File |
| `docker-compose.yml` | File |
| `.dockerignore` | File |
| `.env.example` | File |
| `tests/__init__.py` | File |
| `tests/conftest.py` | File |
| `tests/test_main.py` | File |
| `Base` (sqlalchemy declarative base) | Symbol (imported from `src.database`) |
| `engine`, `get_session`, `init_db` | Symbols (exported from `src.database`) |
| `Settings` | Symbol (exported from `src.config`) |
| `app` (FastAPI instance) | Symbol (exported from `src.main`) |
