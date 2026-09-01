# Fitness Front Desk Agent

Runnable V1 scaffold for the front-desk fitness agent described in `Front Desk Agent.pdf`.

The current implementation covers the blueprint's early phases:

- Mock gym system of record with realistic edge cases and exact fixture dates, loaded from separated facility, member, billing, class, booking, and trainer fixtures.
- Principal-scoped member reads: the model never supplies `member_id` for personal data.
- Role-filtered tool set for member vs staff callers.
- Policy search as a tool with citations.
- Structured refusals for booking proposals.
- Deterministic preference capture gate with a separate preference store.
- LLM-centred agent path with an offline CLI demo mode that works without an API key.

Booking writes are persisted in the running mock store after explicit confirmation. Cancellation, waitlist, and staff overrides should be added behind confirmation interrupts in the next phase. Preference writes are allowed only through a closed-vocabulary capture gate.

The default preference store is JSON-backed at `fitness_agent.preferences.local.json` so local preferences survive app restarts. Replace it with a database-backed implementation before deploying across multiple workers or concurrent writes.

## Structure

```text
fitness_agent/
  agent/      # Agent prompt, tools, deterministic demo router, LangChain graph, service boundary
  api/        # FastAPI app, route modules, auth/session dependencies, request/response schemas
  data/       # Mock gym fixtures, trainer profiles, policy clauses, preference store boundary
  models.py   # Shared domain models
frontend/
  index.html
  styles.css
  src/        # Modular browser API, session, and message UI code
```

See [docs/architecture.md](docs/architecture.md) for the current system summary and architecture diagram.

## Run

```powershell
python main.py --demo
$env:OPENAI_API_KEY = "..."
python main.py --temperature 0.3 "What classes are suitable for cardio?"
python main.py --role guest "What classes are open tomorrow?"
python main.py --role member --member-id mem_001 "What classes are open tomorrow?"
python main.py --role member --member-id mem_001 "I prefer morning classes"
python main.py --role staff --staff-id staff_001 "Find member Daniel"
```

Unauthenticated web chat uses a guest principal. Guest users only receive green-tier public tools: policy search, facility info, class schedule, and human escalation. Membership, billing, bookings, preferences, and staff tools still require login.

## Run the web app

The web app and CLI load local environment variables from `.env` on startup. Use `.env.example` as the key list:

```env
OPENAI_API_KEY=...
FITNESS_DEMO_USERNAME=Avery-Tan
FITNESS_DEMO_PASSWORD_HASH=pbkdf2_sha256$600000$fitness-agent-demo-salt$97f0377f54d76db17d04ec54bddd88ff07df7eb91cc728a3a80a701c2195f4bb
FITNESS_DEMO_ROLE=member  # login account role: member or staff
FITNESS_DEMO_MEMBER_ID=mem_001
FITNESS_DEMO_STAFF_ID=staff_001
```

The `.env` file is ignored by git. On app startup, values in `.env` override inherited terminal values so the project file is the local source of truth.

The web app can also read local demo credentials from `fitness_agent.local.ini`.

```ini
[demo_users]
Avery-Tan = password_hash=pbkdf2_sha256$600000$fitness-agent-demo-salt$97f0377f54d76db17d04ec54bddd88ff07df7eb91cc728a3a80a701c2195f4bb, role=member, member_id=mem_001
Daniel-Lim = password_hash=pbkdf2_sha256$600000$fitness-agent-demo-salt$97f0377f54d76db17d04ec54bddd88ff07df7eb91cc728a3a80a701c2195f4bb, role=member, member_id=mem_002
Maya-Patel = password_hash=pbkdf2_sha256$600000$fitness-agent-demo-salt$97f0377f54d76db17d04ec54bddd88ff07df7eb91cc728a3a80a701c2195f4bb, role=member, member_id=mem_003
local-staff = password_hash=pbkdf2_sha256$600000$fitness-agent-demo-salt$97f0377f54d76db17d04ec54bddd88ff07df7eb91cc728a3a80a701c2195f4bb, role=staff, staff_id=staff_001
```

Do not configure `guest` as a login role. Guest access is the absence of a session; unauthenticated chat automatically receives a guest principal with only green-tier public tools.

For local demo credentials, prefer the multi-user `[demo_users]` section with `password_hash`. Plaintext `password` and the older single-user `[demo_auth]` section are still accepted as migration fallbacks for old local configs.

The checked-in example config includes these demo users:

```text
Avery-Tan / local-password  -> member mem_001
Daniel-Lim / local-password -> member mem_002
Maya-Patel / local-password -> member mem_003
local-staff / local-password -> staff staff_001
```

Then start the server:

```powershell
python -m fitness_agent.api.app
```

Then open `http://127.0.0.1:8000`.

FastAPI also exposes interactive API documentation at `http://127.0.0.1:8000/docs`.

Environment variables still work for values that are missing from `fitness_agent.local.ini`:

```powershell
$env:FITNESS_DEMO_USERNAME = "Avery-Tan"
$env:FITNESS_DEMO_PASSWORD_HASH = "pbkdf2_sha256$600000$..."
```

If port `8000` is already bound on Windows, find and stop the process:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Stop-Process -Id <OwningProcess> -Force
```

Optional session mapping can also be configured in `fitness_agent.local.ini` or environment variables:

```powershell
$env:FITNESS_DEMO_ROLE = "member"
$env:FITNESS_DEMO_MEMBER_ID = "mem_001"
```

By default the web app runs in `auto` mode: it uses the LangChain agent loop when `OPENAI_API_KEY` is set, and falls back to the deterministic offline demo router when no model credentials are available.

```powershell
$env:OPENAI_API_KEY = "..."
python -m fitness_agent.api.app --temperature 0.3
```

Use `--demo` only when you explicitly want the fixed offline demo behavior:

```powershell
python -m fitness_agent.api.app --demo
```

## API

```text
GET    /api/config
POST   /api/sessions
GET    /api/session
DELETE /api/session
POST   /api/chat/messages
```

Compatibility aliases are still available for the first frontend version:

```text
POST /api/login
GET  /api/me
POST /api/logout
POST /api/chat
```

The CLI also runs in `auto` mode. Set `OPENAI_API_KEY` and run the command normally; pass `--llm` only when you want the command to fail instead of falling back to demo mode if model credentials are missing:

```powershell
$env:OPENAI_API_KEY = "..."
python main.py --temperature 0.3 "Can I bring a guest?"
```

## Roadmap

1. Web wrapper: expose login, current user, logout, and chat endpoints around the existing agent.
2. Frontend: keep a separate `frontend/` directory with a sign-in screen, chat workspace, and quick prompts.
3. User database: replace environment mock credentials with a `users` table, password hashes, roles, member/staff mapping, and login audit timestamps.
4. Durable sessions: replace in-memory tokens with signed cookies or database-backed sessions with expiry and revocation.
5. Data stores: move bookings, audit events, sessions, and user records out of process memory into SQLite for local development, then Postgres/MySQL for deployment.
6. Write actions: add confirmation screens for booking, cancellation, waitlist, and staff override operations before committing writes.
7. Deployment: add production config, TLS, secret management, migrations, seed data, and CI tests for auth plus API contracts.

## Test

```powershell
python -m unittest discover
```
