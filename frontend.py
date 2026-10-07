"""Streamlit client. Run: streamlit run frontend.py  (backend.py must be running)."""
import os
import time

import requests
import streamlit as st

API = os.environ.get("RENTAL_API_URL", "http://127.0.0.1:5000")
RISK_SEP = " ||COUNTER|| "


def icon(paths: str, color: str = "currentColor", size: int = 22) -> str:
    return (f'<svg class="ic" xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')


HOME = icon('<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>', "#b9a8ff", 40)
FLAG = lambda c="#ff6b88", z=20: icon('<path d="M5 21V4"/><path d="M5 4h12l-2 4 2 4H5"/>', c, z)
CHAT = icon('<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>', "#5ff0bd", 18)
CHECK = icon('<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>', "#5ff0bd", 20)
DOC = icon('<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h6"/>', "#8fd8ff", 22)

st.set_page_config(page_title="Flat Rental Legal Translator", page_icon=":material/home:", layout="centered",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, .stApp, [class*="css"] {font-family:'Inter', system-ui, sans-serif;}
[data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapsedControl"],
footer, #MainMenu {display:none !important;}
[data-testid="stHeader"] {background:transparent;}
.stApp {background:#0a0d1f; color:#eef1ff;}
.stApp::before, .stApp::after {content:""; position:fixed; z-index:0; border-radius:50%; filter:blur(110px); opacity:.55; pointer-events:none;}
.stApp::before {width:560px; height:560px; top:-160px; left:-120px; background:#6d4aff; animation:drift 18s ease-in-out infinite alternate;}
.stApp::after {width:480px; height:480px; bottom:-140px; right:-100px; background:#0fb5ff; animation:drift 22s ease-in-out infinite alternate-reverse;}
@keyframes drift {to {transform:translate(60px,40px) scale(1.15);}}
.block-container {position:relative; z-index:1; max-width:820px; padding-top:3rem; padding-bottom:5rem;}
h1, h2, h3, p, label, li, span {color:#eef1ff;}
h3 {font-weight:700; letter-spacing:-.01em; margin-top:1.8rem;}

.glass, [data-testid="stVerticalBlockBorderWrapper"] {background:linear-gradient(145deg, rgba(255,255,255,.11), rgba(255,255,255,.04));
        border:1px solid rgba(255,255,255,.16) !important; border-radius:22px !important;
        backdrop-filter:blur(22px) saturate(140%); -webkit-backdrop-filter:blur(22px) saturate(140%);
        box-shadow:0 10px 40px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.2);}
.glass {padding:1.8rem 2rem; margin:0 0 1.2rem 0;}
[data-testid="stVerticalBlockBorderWrapper"] {padding:.6rem .8rem;}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {box-shadow:none; background:none; border:none !important; padding:0;}

.hero {text-align:center;}
.hero .badge {display:inline-block; padding:.25rem .8rem; margin-bottom:.9rem; font-size:.78rem; font-weight:600; letter-spacing:.08em;
        text-transform:uppercase; border-radius:999px; background:rgba(124,92,255,.22); border:1px solid rgba(124,92,255,.55); color:#cfc4ff;}
.hero h1 {font-size:2.7rem; font-weight:800; line-height:1.1; margin:0 0 .7rem 0; letter-spacing:-.03em;
        background:linear-gradient(90deg,#ffffff,#b9a8ff 55%,#6fd8ff); -webkit-background-clip:text; background-clip:text;
        -webkit-text-fill-color:transparent;}
.hero p {font-size:1.05rem; line-height:1.6; color:#c3c9e6; margin:0 auto; max-width:620px;}

.stTextArea label, .stFileUploader label {font-weight:600; color:#dfe3ff;}
.stTextArea textarea {background:rgba(8,10,28,.55) !important; color:#fff !important; border:1px solid rgba(255,255,255,.18) !important;
        border-radius:14px !important; font-size:.98rem; line-height:1.55; transition:border-color .2s, box-shadow .2s;}
.stTextArea textarea:focus {border-color:#8c73ff !important; box-shadow:0 0 0 3px rgba(124,92,255,.3) !important;}
[data-testid="stFileUploaderDropzone"] {background:rgba(8,10,28,.45); border:1.5px dashed rgba(255,255,255,.3); border-radius:14px; transition:all .2s;}
[data-testid="stFileUploaderDropzone"]:hover {border-color:#8c73ff; background:rgba(124,92,255,.12);}

.stButton > button {width:100%; padding:.9rem; font-size:1.05rem; font-weight:700; color:#fff; border:none; border-radius:14px;
        background:linear-gradient(90deg,#7c5cff,#27c5ff); background-size:150% 100%; box-shadow:0 6px 26px rgba(124,92,255,.5);
        transition:transform .15s, box-shadow .2s, background-position .4s;}
.stButton > button:hover {transform:translateY(-2px); background-position:100% 0; box-shadow:0 10px 34px rgba(39,197,255,.6); color:#fff;}
.stButton > button:active {transform:translateY(0) scale(.99);}

[data-testid="stProgress"] > div > div {background:rgba(255,255,255,.1); height:.7rem; border-radius:999px;}
[data-testid="stProgress"] > div > div > div {background:linear-gradient(90deg,#7c5cff,#27c5ff); border-radius:999px; box-shadow:0 0 14px rgba(39,197,255,.7);}

@keyframes rise {from {opacity:0; transform:translateY(12px);} to {opacity:1; transform:none;}}
.risk {animation:rise .45s ease both; border-radius:16px; padding:1.1rem 1.3rem; margin:.9rem 0; line-height:1.55;
       background:linear-gradient(135deg, rgba(255,59,92,.22), rgba(255,59,92,.08)); border:1px solid rgba(255,59,92,.5);
       border-left:6px solid #ff3b5c; box-shadow:0 0 26px rgba(255,59,92,.2);}
.ic {vertical-align:-4px; margin-right:.45rem; flex:none;}
.hero-ic {margin-bottom:.6rem;} .hero-ic .ic {margin:0; filter:drop-shadow(0 0 12px rgba(124,92,255,.8));}
h3.sec {display:flex; align-items:center;}
.rhead {display:flex; align-items:flex-start;} .rhead > span {flex:1;}
.safe {display:flex; align-items:center;}
.stButton > button::before {content:""; display:inline-block; width:1.1em; height:1.1em; margin-right:.55rem; vertical-align:-.15em; background:#fff;
        -webkit-mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><path d='M20 20l-4-4'/></svg>") center/contain no-repeat;
        mask:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.4' stroke-linecap='round'><circle cx='11' cy='11' r='7'/><path d='M20 20l-4-4'/></svg>") center/contain no-repeat;}
.counter {margin-top:.8rem; padding:.75rem 1rem; border-radius:12px; color:#d9fff0;
          background:rgba(46,230,166,.14); border:1px solid rgba(46,230,166,.5); border-left:6px solid #2ee6a6;}
.counter b {color:#5ff0bd;}
.safe {animation:rise .45s ease both; border-radius:16px; padding:1.1rem 1.3rem; color:#d9fff0;
       background:rgba(46,230,166,.14); border:1px solid rgba(46,230,166,.5); box-shadow:0 0 24px rgba(46,230,166,.18);}
@media (max-width:640px) {.hero h1 {font-size:2rem;} .glass {padding:1.3rem;}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="glass hero"><span class="badge">Housing Compliance Auditor</span><div class="hero-ic">' + HOME + '</div><h1>Flat Rental Legal Translator</h1>'
            '<p>Upload or paste your lease. We translate it paragraph by paragraph into plain English and flag predatory '
            'penalties, unfair lock-ins and illegal maintenance shifts.</p></div>', unsafe_allow_html=True)

with st.container(border=True):
    text = st.text_area("Paste your rental agreement", height=260, placeholder="Paste the lease text here...")
    upload = st.file_uploader("...or drop a .txt / .pdf file", type=["txt", "pdf"])
    scan = st.button("Scan Agreement")


def start_job():
    if upload is not None:
        r = requests.post(f"{API}/api/upload", files={"file": (upload.name, upload.getvalue())}, timeout=60)
    else:
        r = requests.post(f"{API}/api/upload", json={"text": text}, timeout=60)
    r.raise_for_status()
    return r.json()["token"]


if scan:
    if not text.strip() and upload is None:
        st.warning("Paste some text or upload a file first.")
        st.stop()
    try:
        token = start_job()
    except requests.RequestException as exc:
        detail = exc.response.json().get("error") if getattr(exc, "response", None) is not None else str(exc)
        st.error(f"Could not start the scan: {detail}")
        st.stop()

    bar, label, job = st.progress(0.0), st.empty(), {}
    while True:
        try:
            job = requests.get(f"{API}/api/status/{token}", timeout=30).json()
        except requests.RequestException as exc:
            st.error(f"Lost connection to backend: {exc}")
            st.stop()
        bar.progress(min(float(job.get("progress", 0)), 1.0))
        label.markdown(f"**{job.get('status', '...')}**")
        if job.get("status") in ("Completed", "Failed"):
            break
        time.sleep(0.8)

    if job["status"] == "Failed":
        st.error(f"Audit failed: {job.get('error')}")
        st.stop()

    st.markdown(f'<h3 class="sec">{FLAG("#ff6b88", 24)} Flagged Risks</h3>', unsafe_allow_html=True)
    if not job["risks"]:
        st.markdown(f'<div class="safe">{CHECK} No predatory clauses detected.</div>', unsafe_allow_html=True)
    for r in job["risks"]:
        risk, _, counter = r.partition(RISK_SEP)
        block = f'<div class="risk"><div class="rhead">{FLAG()}<span>{risk}</span></div>'
        if counter.strip():
            block += f'<div class="counter">{CHAT} <b>Ask for:</b> {counter}</div>'
        st.markdown(block + "</div>", unsafe_allow_html=True)

    st.markdown(f'<h3 class="sec">{DOC} Full Report</h3>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(job["report"])
