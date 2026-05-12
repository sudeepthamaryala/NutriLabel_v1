# Nutrition AI Demo Script

Use this as a 5-7 minute walkthrough for GitHub, interviews, or project review.

## 1. Opening

"Nutrition AI is a production-ready backend for a mobile nutrition assistant. It helps users understand nutrition labels in the context of their own health profile. The key workflows are image analysis, product comparison, and persistent AI chat history."

Show:

- GitHub repository
- README architecture diagram
- Docker Compose file

## 2. Start The System

Say:

"The app is containerized for local and cloud deployment. Docker Compose starts the backend, Postgres with pgvector, and Redis for distributed rate limiting."

Run:

```powershell
docker compose up --build
```

Open:

```text
http://localhost:8000/docs
```

Highlight:

- FastAPI docs
- `/api/v1/health`
- `/api/v1/analyse`
- `/api/v1/compare`
- `/api/v1/profile`

## 3. Health And Readiness

Say:

"The health endpoint does more than return a static response. It checks database connectivity, which is important for deployment readiness."

Call:

```http
GET /api/v1/health
```

Expected:

```json
{"status":"ok"}
```

## 4. Auth And Profile

Say:

"The backend validates Supabase JWTs. Once authenticated, the app creates a local user record and stores app-specific health profile data."

Show profile fields:

- age
- weight
- height
- activity level
- goal
- allergies
- diseases
- dietary preferences

Say:

"This profile is what makes the AI personalized. A high-sugar label means something different for a diabetic user than for a generic user."

## 5. Analyse Demo

Say:

"Now I upload one nutrition-label image. The backend validates the image, extracts text with OCR, parses nutrition fields, optionally retrieves RAG context, calls inference, and persists the chat."

Call:

```http
POST /api/v1/analyse
Content-Type: multipart/form-data
Authorization: Bearer <jwt>

image=<label image>
question=Is this safe for me?
```

Point out response fields:

- `session_id`
- `nutrition`
- `answer.summary`
- `answer.recommendations`
- `answer.warnings`
- `confidence`

Say:

"The response shape stays stable even if external inference is unavailable. In that case, the system returns a safe rule-based fallback."

## 6. Compare Demo

Say:

"The compare flow reuses the analyse pipeline for every image. That was intentional: OCR and parsing logic should not exist in two places."

Call:

```http
POST /api/v1/compare
Content-Type: multipart/form-data
Authorization: Bearer <jwt>

images=<product 1 label>
images=<product 2 label>
question=Which is better for me?
```

Point out:

- parsed product list
- `best_product_index`
- reasons
- tradeoffs
- warnings

Say:

"For a diabetic profile, the fallback comparison prioritizes lower sugar. For hypertension, it prioritizes lower sodium."

## 7. Persistence

Say:

"Every analyse and compare request becomes a chat session with user and assistant messages. That makes the mobile app's history screen straightforward."

Show tables:

- `chat_sessions`
- `chat_messages`

Example query:

```sql
select type, title, created_at
from chat_sessions
order by created_at desc;
```

## 8. Production Readiness

Say:

"This is the part I focused on beyond the MVP feature set."

Highlight:

- Redis-backed rate limiting
- in-memory fallback for development
- bounded retries and timeouts
- structured JSON logs
- request id tracing
- request size limits
- startup config validation
- optional Supabase Storage with cleanup strategy
- Docker image and Compose stack

## 9. Closing

Say:

"The project demonstrates full backend ownership: API design, data modeling, AI service integration, reliability, deployment, and testing. The next step would be adding CI/CD, Alembic migrations, and a complete Flutter client in the `frontend/` directory."

## Quick Interview Sound Bites

- "Compare reuses analyse extraction, so OCR and nutrition parsing stay consistent."
- "External AI failures do not break the flow; they degrade to deterministic fallback logic."
- "Redis is used for horizontal-safe rate limiting, while local development still works without it."
- "The profile is not decoration; it changes the recommendation logic."
- "The architecture keeps routers thin and puts business behavior in testable services."
