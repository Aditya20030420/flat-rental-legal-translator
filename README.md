# Flat Rental Legal Translator

Paste or upload a rental agreement and get a paragraph-by-paragraph plain-English audit. Predatory deposits, harsh lock-in penalties, structural repairs pushed onto the tenant, and mid-term rent hikes are flagged, each with a counter-proposal you can send to the landlord.

Live demo: https://rental-auditor-ui.onrender.com (free tier: the first request after idle takes about a minute to wake up.)

> Automated screening only, not legal advice.

## How it works

```
Streamlit UI  --POST /api/upload-->  Flask API  --background thread-->  LangGraph
      ^                                  |                                  |
      +------ GET /api/status/<token> ---+        upload_node -> clause_auditor_node (loops) -> reporter_node
```

- **upload_node** splits the agreement into paragraphs with `RecursiveCharacterTextSplitter`.
- **clause_auditor_node** retrieves the 3 closest tenant protections from an in-memory ChromaDB collection (RAG), then asks the LLM for a structured verdict: risky or not, a plain-language risk, and a counter-proposal.
- A deterministic router loops the auditor until every paragraph is audited, then goes to **reporter_node**, which writes a markdown report (Summary Check, Predatory Risks Flagged, Actionable Counter-Proposals).
- The UI polls `/api/status/<token>` to drive the progress bar.

Stack: Flask, LangGraph, LangChain, ChromaDB (local ONNX embeddings, no API cost), Groq (`openai/gpt-oss-120b`), Streamlit.

## Run locally

```bash
pip install -r requirements.txt
```

Create a `.env` file with a free key from https://console.groq.com/keys:

```
GROQ_API_KEY=your-key-here
```

Start the backend, then the frontend in a second terminal:

```bash
python backend.py
streamlit run frontend.py
```

Open http://localhost:8501. The first scan downloads a small embedding model (about 80 MB).

## API

| Endpoint | Description |
|---|---|
| `POST /api/upload` | JSON `{"text": "..."}` or multipart `file` (.txt / .pdf). Returns `{"token": "..."}`. |
| `GET /api/status/<token>` | Returns `status`, `progress` (0 to 1), `report`, `risks`, `error`. |

## Deploy on Render

`render.yaml` defines two services, the API and the UI.

1. New, then Blueprint, then pick this repo.
2. Set `GROQ_API_KEY` on `rental-auditor-api`.
3. After the API is live, set `RENTAL_API_URL` on `rental-auditor-ui` to the API's `https://` URL and redeploy.

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `GROQ_API_KEY` | backend | Groq LLM access |
| `RENTAL_API_URL` | frontend | Backend URL (default `http://127.0.0.1:5000`) |
| `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` | backend | Optional LangSmith tracing (commented placeholders in `backend.py`) |

## Limitations

- Scan jobs live in the API's memory, so a restart loses in-flight scans.
- At most 200 paragraphs per agreement.
- Scanned PDFs without a text layer return no text.
- The seeded protections are general residential tenancy principles, not jurisdiction-specific law.
