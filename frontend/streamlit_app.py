import os
import pandas as pd
import streamlit as st
import requests
import threading
import time

# -----------------------------------------------------
# ⚙️ CONFIG
# -----------------------------------------------------
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "https://paperpal-backend1.onrender.com")

UPLOAD_URL = f"{BACKEND_BASE_URL}/api/v1/papers/upload"
SUMMARIZE_ASYNC_URL = f"{BACKEND_BASE_URL}/api/v1/papers/summarize_async"
JOB_STATUS_URL = f"{BACKEND_BASE_URL}/api/v1/jobs"
KEYWORDS_URL = f"{BACKEND_BASE_URL}/api/v1/papers/keywords"
HEALTH_URL = f"{BACKEND_BASE_URL}/api/v1/health/"

# -----------------------------------------------------
# ⚙️ PAGE CONFIG
# -----------------------------------------------------
st.set_page_config(
    page_title="🚀 PaperPal 2.0",
    page_icon="🧠",
    layout="wide",
)

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
    unsafe_allow_html=True
)

# -----------------------------------------------------
# 📤 UPLOAD SECTION
# -----------------------------------------------------
st.markdown("## 📤 Upload Your Paper")

uploaded_file = st.file_uploader("Choose a PDF research paper", type=["pdf"])

def upload_pdf(file_obj):
    files = {"file": (file_obj.name, file_obj.getvalue(), file_obj.type)}
    r = requests.post(UPLOAD_URL, files=files, timeout=(10, 180))
    r.raise_for_status()
    return r.json()

if uploaded_file:
    if st.button("🚀 Upload Paper", use_container_width=True):
        with st.spinner("Uploading..."):
            try:
                res = upload_pdf(uploaded_file)
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
        help="Choose how detailed you want the summary to be.",
    )

    use_cache = st.toggle("Use cached summary (if available)", value=True)

    # --- Helpers ---
    def summarize_paper_async(paper_id, summary_type="medium", use_cache=True):
        payload = {"paper_id": paper_id, "summary_type": summary_type, "use_cache": use_cache}
        r = requests.post(SUMMARIZE_ASYNC_URL, json=payload, timeout=(10, 30))
        r.raise_for_status()
        return r.json()["job_id"]

    def poll_job(job_id, max_wait_s=900, interval_s=2):
        """Poll backend until job completes or times out."""
        start = time.time()
        with st.spinner("Summarizing in background..."):
            while True:
                r = requests.get(f"{JOB_STATUS_URL}/{job_id}", timeout=(5, 20))
                if r.status_code == 404:
                    time.sleep(interval_s)
                    continue
                r.raise_for_status()
                data = r.json()
                status = data.get("status")
                if status in ("done", "error"):
                    return data
                if time.time() - start > max_wait_s:
                    return {"status": "error", "error": "Polling timed out"}
                time.sleep(interval_s)

    # --- Button ---
    if st.button("🚀 Summarize Paper", use_container_width=True):
        try:
            with st.spinner("Queueing summarization job..."):
                job_id = summarize_paper_async(
                    st.session_state["paper_id"],
                    summary_type,
                    use_cache
                )
            st.info(f"📦 Job queued: `{job_id}`")

            res = poll_job(job_id)

            if res.get("status") == "done":
                st.markdown(f"### 🧾 {summary_type.capitalize()} Summary")
                st.info(res.get("summary", "No summary returned."))

                st.caption(
                    f"🕒 {res.get('duration_ms', 0)/1000:.2f}s • "
                    f"🔢 {res.get('chunks', 0)} chunks • "
                    f"{'⚡ Cached' if res.get('cached') else '🧮 Freshly generated'} • "
                    f"🧠 {res.get('model_name','')}"
                )

            else:
                st.error(f"❌ Job failed: {res.get('error', 'Unknown error')}")
        except requests.exceptions.Timeout:
            st.error("⏰ Backend request timed out while starting job.")
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
                            unsafe_allow_html=True
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
