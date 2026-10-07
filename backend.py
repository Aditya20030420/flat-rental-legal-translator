"""Flat Rental Document Legal Translator - Flask API + LangGraph audit pipeline + RAG.

Run:  put GROQ_API_KEY=... in .env   then   python backend.py
"""
import io
import logging
import os
import threading
import uuid
from typing import Dict, List, TypedDict

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
import chromadb
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

# ---------------------------------------------------------------- LangSmith (placeholders)
# Uncomment and fill in to enable tracing.
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_API_KEY"] = "<YOUR_LANGSMITH_API_KEY>"
# os.environ["LANGCHAIN_PROJECT"] = "flat-rental-legal-translator"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
load_dotenv()
log = logging.getLogger("rental-auditor")

MAX_CHUNKS = 200
RISK_SEP = " ||COUNTER|| "  # separates risk text from its counter-proposal inside identified_risks


# ---------------------------------------------------------------- State
class AgentState(TypedDict):
    raw_agreement: str
    text_chunks: List[str]
    current_chunk_index: int
    identified_risks: List[str]
    final_report: str


# ---------------------------------------------------------------- RAG baseline
TENANT_PROTECTIONS = [
    "Security deposit: a landlord should not demand more than 1 to 3 months of rent as a refundable security deposit. "
    "Demands of 4+ months, or non-refundable 'deposits', are predatory.",
    "Exit notice: the standard notice period for terminating a residential tenancy is 30 days by either party. "
    "Long lock-in periods with heavy exit penalties, or notice periods well beyond 30 days imposed only on the tenant, are unfair.",
    "Repairs: major structural repairs (roof, walls, plumbing mains, wiring, waterproofing) fall exclusively on the landlord. "
    "Shifting structural repair costs to the tenant is illegal. Tenants only cover minor day-to-day upkeep and damage they cause.",
    "Rent hikes: rent cannot be increased arbitrarily mid-agreement. Increases are limited to what the agreement fixes in advance "
    "(typically a modest annual percentage, commonly 5-10%) and only at renewal. Unilateral mid-term hikes are not allowed.",
    "Penalties: penalty clauses must be proportionate. Forfeiting the whole deposit, charging multiple months' rent for minor breaches, "
    "or daily late fees far above reasonable interest are unfair.",
    "Entry and privacy: a landlord must give reasonable prior notice (usually 24 hours) before entering the premises except in emergencies.",
    "Eviction: a tenant cannot be evicted or locked out without due process and notice; clauses allowing immediate eviction at the landlord's whim are void.",
    "Deposit refund: the security deposit must be returned within about 30 days of vacating, less only documented damage or unpaid dues.",
]


def build_vectorstore():
    # Chroma's default embedder is a free local ONNX MiniLM model (downloads ~80MB on first use).
    col = chromadb.EphemeralClient().get_or_create_collection("tenant_protections")
    col.add(documents=TENANT_PROTECTIONS, ids=[f"p{i}" for i in range(len(TENANT_PROTECTIONS))])
    return col


_vectorstore = None
_llm = None


def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = build_vectorstore()
    return _vectorstore


class ClauseVerdict(BaseModel):
    is_risky: bool = Field(description="True if the clause contains unfair tenant conditions, hidden penalties or non-standard maintenance shifts")
    risk: str = Field(default="", description="Plain-language explanation (1-2 sentences) of what is unfair and why, for a student with no legal background")
    counter_proposal: str = Field(default="", description="A concrete, polite counter-proposal the tenant can ask the landlord for")


AUDIT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You audit residential rental agreements on behalf of the tenant. Compare the clause with the reference tenant protections. "
     "Flag it ONLY if it is genuinely unfair, predatory, illegal or non-standard (excess deposit, harsh lock-in/exit penalty, "
     "structural repairs pushed to the tenant, mid-term rent hikes, hidden fees, one-sided termination). "
     "Ordinary clauses (names, dates, rent amount, address) are NOT risky. Write in simple language.\n\n"
     "Reference protections:\n{context}"),
    ("human", "Clause:\n{clause}"),
])


def get_chain():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    return AUDIT_PROMPT | _llm.with_structured_output(ClauseVerdict)


# ---------------------------------------------------------------- Graph nodes
def upload_node(state: AgentState) -> dict:
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=0, separators=["\n\n", "\n", ". ", " "])
    chunks = [c.strip() for c in splitter.split_text(state["raw_agreement"]) if c.strip()][:MAX_CHUNKS]
    return {"text_chunks": chunks, "current_chunk_index": 0, "identified_risks": [], "final_report": ""}


def clause_auditor_node(state: AgentState) -> dict:
    idx = state["current_chunk_index"]
    chunk = state["text_chunks"][idx]
    docs = get_vectorstore().query(query_texts=[chunk], n_results=3)["documents"][0]
    context = "\n".join(f"- {d}" for d in docs)
    verdict: ClauseVerdict = get_chain().invoke({"context": context, "clause": chunk})
    risks = list(state["identified_risks"])
    if verdict.is_risky and verdict.risk:
        risks.append(f"Paragraph {idx + 1}: {verdict.risk}{RISK_SEP}{verdict.counter_proposal}")
    return {"identified_risks": risks, "current_chunk_index": idx + 1}


def reporter_node(state: AgentState) -> dict:
    n, risks = len(state["text_chunks"]), state["identified_risks"]
    if risks:
        summary = f"Audited **{n}** paragraph(s) and flagged **{len(risks)}** potential problem(s). Review them before signing."
    else:
        summary = f"Audited **{n}** paragraph(s). No predatory clauses were detected, but still read the full agreement."
    flagged = "\n".join(f"- {r.split(RISK_SEP)[0]}" for r in risks) or "- None detected."
    counters = "\n".join(
        f"{i}. {r.split(RISK_SEP)[0].split(':')[0]}: {r.split(RISK_SEP)[1]}"
        for i, r in enumerate(risks, 1) if RISK_SEP in r and r.split(RISK_SEP)[1].strip()
    ) or "_Nothing to negotiate._"
    report = (f"## Summary Check\n{summary}\n\n## Predatory Risks Flagged\n{flagged}\n\n"
              f"## Actionable Counter-Proposals\n{counters}\n\n"
              "_This is an automated screening, not legal advice._")
    return {"final_report": report}


def route_after_audit(state: AgentState) -> str:
    return "clause_auditor_node" if state["current_chunk_index"] < len(state["text_chunks"]) else "reporter_node"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("upload_node", upload_node)
    g.add_node("clause_auditor_node", clause_auditor_node)
    g.add_node("reporter_node", reporter_node)
    g.set_entry_point("upload_node")
    g.add_conditional_edges("upload_node", route_after_audit, ["clause_auditor_node", "reporter_node"])
    g.add_conditional_edges("clause_auditor_node", route_after_audit, ["clause_auditor_node", "reporter_node"])
    g.add_edge("reporter_node", END)
    return g.compile()


GRAPH = build_graph()

# ---------------------------------------------------------------- Job registry
JOBS: Dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _set(token: str, **kw):
    with JOBS_LOCK:
        JOBS[token].update(kw)


def run_job(token: str, text: str):
    try:
        init: AgentState = {"raw_agreement": text, "text_chunks": [], "current_chunk_index": 0,
                            "identified_risks": [], "final_report": ""}
        final = init
        for state in GRAPH.stream(init, {"recursion_limit": MAX_CHUNKS * 2 + 10}, stream_mode="values"):
            final = state
            n, i = len(state["text_chunks"]), state["current_chunk_index"]
            if not n:
                _set(token, status="Uploading", progress=0.0)
            elif i < n:
                _set(token, status=f"Auditing Paragraph {i + 1}/{n}", progress=i / n)
            else:
                _set(token, status="Compiling Report", progress=0.97)
        _set(token, status="Completed", progress=1.0, report=final["final_report"],
             risks=final["identified_risks"])
    except Exception as exc:  # noqa: BLE001
        log.exception("Job %s failed", token)
        _set(token, status="Failed", error=str(exc))


def extract_text(file) -> str:
    data = file.read()
    if file.filename.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    return data.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------- Flask
app = Flask(__name__)
CORS(app)


@app.before_request
def _log_request():
    log.info("%s %s", request.method, request.path)


@app.errorhandler(Exception)
def _handle_error(exc):
    log.exception("Unhandled error")
    code = getattr(exc, "code", 500)
    return jsonify(error=str(exc)), code if isinstance(code, int) else 500


@app.post("/api/upload")
def upload():
    if "file" in request.files:
        text = extract_text(request.files["file"])
    else:
        text = (request.get_json(silent=True) or {}).get("text") or request.form.get("text", "")
    text = text.strip()
    if not text:
        return jsonify(error="No agreement text provided."), 400
    if not os.environ.get("GROQ_API_KEY"):
        return jsonify(error="GROQ_API_KEY is not set on the backend."), 500
    token = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[token] = {"status": "Uploading", "progress": 0.0, "report": "", "risks": [], "error": ""}
    threading.Thread(target=run_job, args=(token, text), daemon=True).start()
    return jsonify(token=token), 202


@app.get("/api/status/<token>")
def status(token):
    with JOBS_LOCK:
        job = JOBS.get(token)
        if job is None:
            return jsonify(error="Unknown token."), 404
        return jsonify(job)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
