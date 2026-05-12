# Nutrition AI

Production-ready MVP backend for a nutrition intelligence mobile app that analyzes food-label images, compares products against a user's health profile, and persists explainable AI chat history.

## Problem Statement

Nutrition labels are dense, inconsistent, and hard to interpret quickly. A user may care about very different signals depending on their health context: sugar for diabetes, sodium for hypertension, allergens for dietary safety, or protein for fitness goals. Most food scanner apps extract generic nutrition values but do not connect those values to the user's profile or preserve the reasoning as a conversational history.

Nutrition AI solves this by turning nutrition-label images into structured nutrition data, combining it with a health profile, and returning practical recommendations through a clean FastAPI backend designed for mobile clients.

## Solution Overview

The system exposes authenticated APIs for:

- Creating and updating a health profile.
- Analyzing one nutrition-label image.
- Comparing multiple nutrition-label images.
- Persisting AI interactions as chat sessions and messages.

The backend is built around a service-oriented pipeline:

1. Validate authenticated user and profile.
2. Validate uploaded image inputs.
3. Extract text with OCR.
4. Parse nutrition values into structured JSON.
5. Retrieve optional RAG context.
6. Call an external inference service, with safe rule-based fallback.
7. Persist the user request and assistant response.

The result is an MVP that is simple enough to understand, but production-minded enough to deploy and scale.

## Architecture

```text
Mobile client
  |
  | multipart/form-data + Bearer JWT
  v
FastAPI backend
  |
  |-- Auth dependency
  |     validates Supabase JWT and loads local user
  |
  |-- Profile service
  |     loads health context for recommendations
  |
  |-- Analyse / Compare services
  |     validate image -> OCR -> parse nutrition -> RAG -> inference
  |
  |-- Chat service
  |     stores sessions and messages atomically
  |
  v
Postgres + pgvector
  users, health_profiles, chat_sessions, chat_messages, rag_chunks

Optional infrastructure:
  Redis for distributed rate limiting
  Supabase Storage for private image storage and signed URLs
  External OCR, embedding, and inference services
```

### OCR -> Parsing -> RAG -> Inference Pipeline

The analyse pipeline starts with a nutrition-label image. The backend validates file type, size, and image integrity before OCR runs. OCR can use an external service when configured, otherwise local Tesseract is available as an MVP fallback.

The nutrition parser converts OCR text into normalized fields:

- calories
- fat
- protein
- sugar
- sodium
- serving size
- ingredients

The RAG service can retrieve relevant `rag_chunks` from Postgres/pgvector when an embedding service is configured. If embeddings are unavailable, it falls back to deterministic keyword matching rather than random context.

The inference client receives:

- parsed nutrition JSON
- user health profile
- optional question
- retrieved RAG context

If the external inference service fails, the backend returns a safe rule-based fallback instead of failing the user flow.

### How The Health Profile Influences Results

Health profiles include age, weight, height, activity level, goal, allergies, diseases, and dietary preferences. This context changes the response. For example:

- Diabetes increases sensitivity to high sugar.
- Hypertension increases sensitivity to high sodium.
- Allergies are matched against parsed ingredients.
- Protein and calorie tradeoffs influence general recommendations.

### How Compare Reuses Analyse Logic

The compare flow does not duplicate OCR or parsing. It calls the same reusable `ocr_and_parse_nutrition` path used by analyse for each uploaded image, then compares the resulting nutrition objects. This keeps parsing behavior consistent and reduces maintenance risk.

### Why Services Are Separated

Routers handle HTTP only. Business logic is kept in services:

- `ocr_service`: text extraction
- `nutrition_parser`: text-to-JSON normalization
- `rag_service`: retrieval and embedding-aware search
- `inference_client`: external AI calls and fallback behavior
- `chat_service`: session/message persistence
- `storage_service`: optional Supabase Storage integration

This separation makes the code easier to test, replace, and scale.

## Features

### Analyse

Upload one nutrition-label image and optional question. The backend extracts nutrition data, evaluates it against the user's health profile, returns recommendations, and saves the interaction.

### Compare

Upload two to five product-label images. The backend extracts nutrition for each product, chooses the best option using AI or rule-based fallback, explains reasons and tradeoffs, and stores the comparison as chat history.

### AI Pipeline

- OCR with local and remote support.
- Nutrition text parsing.
- Optional RAG context with pgvector.
- External inference client with timeout/retry.
- Rule-based safe fallback for resilience.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API | FastAPI | HTTP API and routing |
| Validation | Pydantic | Request/response schemas |
| Database | PostgreSQL | Relational persistence |
| Vector Search | pgvector | RAG chunk similarity search |
| ORM | SQLAlchemy async | Async database access |
| Auth | Supabase JWT | Mobile authentication boundary |
| OCR | Tesseract / external OCR | Label text extraction |
| AI | External REST inference service | Nutrition recommendations and comparison |
| Rate Limiting | Redis with in-memory fallback | Horizontal-safe request limiting |
| Storage | Supabase Storage optional | Private image storage and signed URLs |
| Deployment | Docker, Docker Compose | Local and cloud deployment |
| Testing | pytest | Backend behavior and reliability tests |

## System Design Highlights

- **Bounded retries:** Remote OCR, inference, storage, and embedding calls use limited retries with exponential backoff for transient failures.
- **Timeouts:** External service calls have explicit timeouts to avoid hanging requests.
- **Request tracing:** Each request receives or propagates a `request_id`.
- **Structured logs:** JSON logs include request id, user id, endpoint, method, and latency.
- **Rate limiting:** Redis-backed limiter supports horizontal scaling, with in-memory fallback for local development.
- **Safe fallbacks:** Inference failures degrade to deterministic recommendations instead of crashing.
- **Atomic chat persistence:** Sessions and messages are committed together.
- **Image storage strategy:** Images remain in-memory by default. When Supabase Storage is enabled, upload happens after successful processing, and cleanup is attempted if persistence fails.
- **Config validation:** Startup validates required environment variables and rejects wildcard CORS in production mode.

## API Documentation

All protected routes require:

```http
Authorization: Bearer <supabase_jwt>
```

### `PUT /api/v1/profile`

Creates or updates the authenticated user's health profile.

Request:

```json
{
  "age": 30,
  "weight_kg": "72.50",
  "height_cm": "175.00",
  "sex": "other",
  "activity_level": "moderate",
  "goal": "weight_maintenance",
  "allergies": ["peanuts"],
  "diseases": ["diabetes"],
  "dietary_preferences": ["vegetarian"]
}
```

Response:

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "age": 30,
  "weight_kg": "72.50",
  "height_cm": "175.00",
  "sex": "other",
  "activity_level": "moderate",
  "goal": "weight_maintenance",
  "allergies": ["peanuts"],
  "diseases": ["diabetes"],
  "dietary_preferences": ["vegetarian"],
  "created_at": "2026-05-03T00:00:00Z",
  "updated_at": "2026-05-03T00:00:00Z"
}
```

### `POST /api/v1/analyse`

Multipart request:

- `image`: required JPEG, PNG, or WEBP
- `question`: optional text

Response:

```json
{
  "session_id": "uuid",
  "nutrition": {
    "calories": 220,
    "fat_g": 9,
    "protein_g": 6,
    "sugar_g": 18,
    "sodium_mg": 320,
    "serving_size": "45g",
    "ingredients": ["oats", "sugar", "cocoa", "peanuts"]
  },
  "answer": {
    "summary": "Parsed label highlights: 220 calories, 18g sugar, 320mg sodium.",
    "recommendations": ["Consider a lower-sugar option or reduce the serving size."],
    "warnings": ["Contains possible allergen: peanuts."]
  },
  "confidence": 0.6
}
```

### `POST /api/v1/compare`

Multipart request:

- `images`: required list of 2 to 5 JPEG, PNG, or WEBP images
- `question`: optional text

Response:

```json
{
  "session_id": "uuid",
  "products": [
    {
      "index": 0,
      "nutrition": {
        "calories": 240,
        "fat_g": 8,
        "protein_g": 5,
        "sugar_g": 22,
        "sodium_mg": 380,
        "serving_size": "45g",
        "ingredients": ["oats", "sugar", "cocoa"]
      }
    }
  ],
  "best_product_index": 0,
  "verdict": {
    "best_product": "Product 1",
    "reasons": ["Lowest sugar among the parsed products."],
    "tradeoffs": [],
    "warnings": []
  }
}
```

### Error Format

Errors use FastAPI's standard shape:

```json
{
  "detail": "Create your health profile before analysing images."
}
```

Common errors:

| Status | Meaning |
|---|---|
| 400 | Invalid image or invalid compare image count |
| 401 | Missing or invalid token |
| 404 | Authenticated user not registered locally |
| 409 | Health profile missing |
| 413 | Request payload too large |
| 429 | Rate limit exceeded |
| 502 | OCR service failure |
| 503 | Health/readiness dependency unavailable |

## Setup Instructions

### Docker

```powershell
cd C:\Users\vigne\OneDrive\Desktop\nutrition-ai
Copy-Item .env.example .env
```

Edit `.env` and set at least:

```text
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
```

Start the stack:

```powershell
docker compose up --build
```

API:

```text
http://localhost:8000
```

Docs:

```text
http://localhost:8000/docs
```

### Local Backend Development

```powershell
cd C:\Users\vigne\OneDrive\Desktop\nutrition-ai\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Set environment variables or create `.env`:

```text
DATABASE_URL=postgresql+asyncpg://nutrition_ai:nutrition_ai_password@localhost:5432/nutrition_ai
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
SUPABASE_JWT_AUDIENCE=authenticated
```

Run:

```powershell
uvicorn app.main:app --reload
```

Run tests:

```powershell
pytest -q
```

## Environment Variables

| Variable | Required | Description |
|---|---:|---|
| `DATABASE_URL` | yes | Async Postgres URL |
| `SUPABASE_JWT_SECRET` | yes | Secret used to validate Supabase JWTs |
| `SUPABASE_JWT_AUDIENCE` | no | Defaults to `authenticated` |
| `SUPABASE_JWT_ALGORITHM` | no | Defaults to `HS256` |
| `CORS_ORIGINS` | production | JSON list of allowed origins |
| `PRODUCTION_MODE` | no | Enables stricter config validation |
| `REDIS_URL` | recommended | Shared limiter for horizontal scaling |
| `OCR_SERVICE_URL` | optional | Remote OCR endpoint |
| `INFERENCE_SERVICE_URL` | optional | Remote AI inference endpoint |
| `EMBEDDING_SERVICE_URL` | optional | Embedding endpoint for RAG |
| `STORAGE_ENABLED` |   | Enables Supabase Storage uploads |
| `SUPABASE_URL` | storage only | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | storage only | Storage upload/signing key |
| `SUPABASE_STORAGE_BUCKET` | storage only | Private bucket name |
| `RATE_LIMIT_REQUESTS` | no | Request limit per window |
| `RATE_LIMIT_WINDOW_SECONDS` | no | Rate-limit window |
| `MAX_REQUEST_BYTES` | no | Request payload cap |
| `MAX_COMPARE_IMAGES` | no | Compare image limit |

## Demo

1. Start the backend with Docker Compose.
2. Register or authenticate a user through Supabase and obtain a JWT.
3. Call `/api/v1/auth/register` once to create the local user record.
4. Create a health profile with diabetes/allergy context.
5. Upload a nutrition label to `/api/v1/analyse`.
6. Show the parsed nutrition, warnings, recommendations, and saved session id.
7. Upload two product labels to `/api/v1/compare`.
8. Show how the backend picks the better product and explains tradeoffs.
9. Open logs to show JSON request tracing and latency.

See [demo/DEMO_SCRIPT.md](demo/DEMO_SCRIPT.md) for a polished walkthrough.

## Resume Bullets

- Built a production-ready FastAPI backend for a nutrition AI mobile app, implementing JWT auth, health profiles, image analysis, product comparison, chat persistence, and pgvector-backed RAG storage.
- Designed a reusable OCR-to-nutrition parsing pipeline that powers both single-product analysis and multi-product comparison without duplicated business logic.
- Integrated production resilience patterns including Redis rate limiting, bounded retries, external-service timeouts, structured JSON logs, request-id tracing, Docker deployment, and startup config validation.
- Implemented AI fallback behavior for OCR/inference failures, preserving user-facing reliability while supporting external REST inference and optional Supabase Storage.

## Interview Explanation

### One-Minute Answer

Nutrition AI is a production-ready backend for a mobile nutrition assistant. A user uploads a nutrition-label image, and the system extracts label text with OCR, parses calories and nutrients into structured JSON, combines that with the user's health profile, and returns personalized recommendations. It also supports comparing multiple products, for example choosing the lower-sugar option for a diabetic user. I built it with FastAPI, Postgres, pgvector, Redis rate limiting, Docker, request tracing, retries, and safe AI fallbacks, so it is not just a prototype but a deployable MVP backend.

### Five-Minute Deep Dive

The backend is organized around service boundaries. Routers only handle HTTP concerns, while services own OCR, parsing, RAG retrieval, inference, chat persistence, and optional storage.

The analyse flow starts by validating the Supabase JWT and loading the local user. It requires a health profile because recommendations depend on health context. The uploaded image is validated for MIME type, size, and image integrity. OCR extracts text, and the parser normalizes label text into fields like calories, sugar, sodium, protein, serving size, and ingredients.

Then the RAG service optionally retrieves relevant nutrition guidance from `rag_chunks`. If an embedding service is configured, it uses pgvector similarity ordering. If not, it uses deterministic keyword matching, avoiding random context.

The inference client sends nutrition data, profile data, the user's question, and RAG context to an external AI service. If the external service fails, the backend uses a safe rule-based fallback. For example, diabetes makes sugar more important, hypertension makes sodium more important, and allergens are matched against ingredients.

The compare flow reuses the exact same OCR and parser path for each image, then compares the resulting nutrition objects. This is an important design decision because it prevents the analyse and compare features from drifting.

Finally, the chat service saves the interaction as a session with user and assistant messages. The system includes production concerns: Redis-backed rate limiting, request-size limits, structured JSON logs, request ids, retries, timeouts, Docker packaging, and startup config validation.

### Key Design Decisions

- Use Supabase JWTs as the auth boundary, but keep local user/profile tables for app-specific state.
- Keep OCR, parser, RAG, inference, and chat persistence as separate services.
- Reuse analyse extraction logic inside compare instead of duplicating OCR/parsing.
- Return safe fallback responses when external AI services fail.
- Make Redis optional but preferred for horizontal scaling.
- Keep Supabase Storage optional so local development remains simple.

## Future Improvements

- Add Alembic migrations instead of a single SQL schema file.
- Move rate-limit state exclusively to Redis in production.
- Add a full ingestion pipeline for WHO, FDA, FSSAI, PubMed, and Open Food Facts.
- Add first-class OpenAPI examples for every endpoint.
- Add Flutter client source in `frontend/` with secure token storage and API integration.
- Add CI/CD for tests, Docker image build, and deploy previews.
- Add observability integration with OpenTelemetry or a managed log platform.
#   N u t r i L a b e l _ v 1  
 