import os
import pandas as pd
import streamlit as st
import requests
import threading
import time

# -----------------------------------------------------
# ⚙️ CONFIG
# -----------------------------------------------------
DEFAULT_BACKEND = os.getenv("BACKEND_BASE_URL", "https://paperpal-backend1.onrender.com")

# -----------------------------------------------------
# ⚙️ PAGE CONFIG
# -----------------------------------------------------
st.set_page_config(
    page_title="🚀 PaperPal 2.0",
    page_icon="🧠",
    layout="wide",
)

# -----------------------------------------------------
# 🧩 SIDEBAR SETTINGS
# -----------------------------------------------------
with st.sidebar.expander("⚙️ Backend Settings"):
    BACKEND_BASE_URL = st.text_input(
        "Backend URL", DEFAULT_BACKEND,
        help="Switch between local and Render backend (e.g. http://localhost:8000)"
    )

UPLOAD_URL = f"{BACKEND_BASE_URL}/api/v1/papers/upload"
SUMMARIZE_URL = f"{BACKEND_BASE_URL}/api/v1/papers/summarize"
KEYWORDS_URL = f"{BACKEND_BASE_URL}/api/v1/papers/keywords"
HEALTH_URL = f"{BACKEND_BASE_URL}/api/v1/health/"

# Restore paper state
if "paper_id" in st.session_state:
    st.sidebar.success(f"📄 Active paper: {st.session_state['paper_name']}")
else:
    st.sidebar.info("📁 Upload a paper to get started.")

# -----------------------------------------------------
# 🧩 BACKEND KEEP-ALIVE
# -----------------------------------------------------
def keep_backend_alive(interval=300):
    """Ping backend every 5 minutes to prevent Render sleep."""
    while True:
        try:
            res = requests.get(HEALTH_URL, timeout=10)
            if res.status_code == 200:
                print("💚 Backend alive")
        except Exception as e:
            print("⚠️ Keep-alive ping failed:", e)
        time.sleep(interval)

if "keep_alive_thread" not in st.session_state:
    st.session_state.keep_alive_thread = threading.Thread(
        target=keep_backend_alive, args=(300,), daemon=True
    )
    st.session_state.keep_alive_thread.start()

# -----------------------------------------------------
# 🧠 HEADER
# -----------------------------------------------------
st.markdown(
    """
    <div style='text-align:center;'>
        <h1>🚀 <b>PaperPal 2.0</b></h1>
        <p style='color:gray;'>Upload, summarize and extract keywords from research papers effortlessly.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------
# 📤 UPLOAD SECTION
# -----------------------------------------------------
st.markdown("## 📤 Upload Your Paper")
st.markdown("**⚠️ Max file size: 1 MB (typical research paper length)**")

uploaded_file = st.file_uploader("Choose a PDF research paper", type=["pdf"])

if uploaded_file:
    if uploaded_file.size > 1 * 1024 * 1024:
        st.error("❌ File too large (limit 1 MB). Please upload a smaller paper.")
        st.stop()

@st.cache_data(show_spinner=False)
def upload_pdf_cached(file_obj):
    files = {"file": (file_obj.name, file_obj.getvalue(), file_obj.type)}
    r = requests.post(UPLOAD_URL, files=files, timeout=(10, 120))
    r.raise_for_status()
    return r.json()

if uploaded_file:
    if st.button("🚀 Upload Paper", use_container_width=True):
        with st.spinner("Uploading..."):
            try:
                res = upload_pdf_cached(uploaded_file)
                paper_id = res.get("paper_id") or res.get("data", {}).get("paper_id")
                st.session_state["paper_id"] = paper_id
                st.session_state["paper_name"] = uploaded_file.name
                st.success(f"✅ Uploaded successfully: {uploaded_file.name}")
                st.caption(f"🆔 Paper ID: `{paper_id}`")
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")

if "paper_id" not in st.session_state:
    st.info("⬆️ Please upload a paper first.")
    st.stop()

# -----------------------------------------------------
# 🧭 TABS
# -----------------------------------------------------
tab1, tab2 = st.tabs(["🧠 Summarize", "🔑 Keywords"])

# -----------------------------------------------------
# 🧠 SUMMARIZATION TAB
# -----------------------------------------------------
with tab1:
    st.markdown("### ✍️ Generate Summary")

    summary_type = st.radio(
        "Select summary level:",
        ["short", "medium", "detailed"],
        horizontal=True,
    )
    use_cache = st.toggle("Use cached summary (if available)", value=True)

    progress = st.progress(0)
    status_text = st.empty()

    def summarize_paper(paper_id, summary_type, use_cache=True):
        payload = {"paper_id": paper_id, "summary_type": summary_type, "use_cache": use_cache}
        r = requests.post(SUMMARIZE_URL, json=payload, timeout=(10, 400))
        r.raise_for_status()
        return r.json()

    if st.button("🚀 Summarize Paper", use_container_width=True):
        start_time = time.time()
        try:
            for i in range(0, 90, 10):
                progress.progress(i)
                status_text.text(f"⏳ Summarizing... ({i}%)")
                time.sleep(0.3)

            res = summarize_paper(st.session_state["paper_id"], summary_type, use_cache)

            progress.progress(100)
            status_text.text("✅ Done!")

            st.markdown(f"### 🧾 {summary_type.capitalize()} Summary")
            st.info(res.get("summary", "No summary returned."))

            st.caption(
                f"🕒 {res.get('duration_ms',0)/1000:.2f}s • "
                f"🔢 {res.get('chunks',0)} chunks • "
                f"{'⚡ Cached' if res.get('cached') else '🧮 Freshly generated'}"
            )

        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. Try again or shorten the PDF.")
        except Exception as e:
            st.error(f"❌ Summarization failed: {e}")

# -----------------------------------------------------
# 🔑 KEYWORDS TAB
# -----------------------------------------------------
with tab2:
    st.markdown("### 🧩 Keyword Ranking")

    top_k = st.slider("How many top keywords to show?", 5, 40, 15, step=1)

    def extract_keywords(paper_id, top_k=15):
        payload = {"paper_id": paper_id, "top_k": top_k}
        r = requests.post(KEYWORDS_URL, json=payload, timeout=(10, 120))
        r.raise_for_status()
        return r.json()

    if st.button("🚀 Extract Keywords", use_container_width=True):
        with st.spinner("Extracting keywords... ⏳"):
            try:
                res = extract_keywords(st.session_state["paper_id"], top_k)
                st.success("✅ Keywords extracted successfully!")

                kws = res.get("keywords", [])
                if not kws:
                    st.info("No keywords found.")
                else:
                    df = pd.DataFrame(kws)
                    if "score" in df.columns:
                        df = df.sort_values("score", ascending=True).reset_index(drop=True)
                    df["rank"] = df.index + 1
                    df = df[["rank", "text", "score"]]

                    st.markdown("#### 🏅 Ranked Keywords")
                    for _, row in df.iterrows():
                        st.markdown(
                            f"<div style='display:flex;justify-content:space-between;align-items:center;"
                            f"padding:8px 12px;margin:6px 0;border-radius:10px;background:#1f1f1f;'>"
                            f"<div><b>#{int(row['rank'])}</b> — {row['text']}</div>"
                            f"<div style='font-size:12px;color:#9aa0a6;'>score: {row['score']:.5f}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    with st.expander("See as table"):
                        st.dataframe(df, hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Keyword extraction failed: {e}")

# -----------------------------------------------------
# 🧩 FOOTER
# -----------------------------------------------------
st.markdown("---")
st.caption("🚀 PaperPal 2.0 — Powered by FastAPI & Streamlit • 2025")
