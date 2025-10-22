import warnings
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)

import requests
import streamlit as st

# -------------------------------------------------------
# 🌍 Hard-coded backend endpoint
# -------------------------------------------------------
BACKEND_URL = "https://paperpal-pvqg.onrender.com/api/v1/papers/upload"

# -------------------------------------------------------
# 🎨 Page setup
# -------------------------------------------------------
st.set_page_config(
    page_title="PaperPal | AI PDF Parser",
    page_icon="🧠",
    layout="wide"
)

# -------------------------------------------------------
# 💎 Styles & Header
# -------------------------------------------------------
st.markdown(
    """
    <style>
        /* Layout cleanup */
        div[data-testid="stSidebar"] {display: none;}
        header[data-testid="stHeader"] {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding-top: 2rem;}

        .main-title {
            text-align: center;
            font-size: 3rem;
            font-weight: 800;
            background: -webkit-linear-gradient(90deg, #FF4B4B, #FFB347);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .sub-title {
            text-align: center;
            font-size: 1.1rem;
            color: #aaa;
            margin-bottom: 2rem;
        }
        .upload-box {
            border: 2px dashed #FF4B4B;
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            background-color: #111;
        }
        section[data-testid="stFileUploader"] small {display: none !important;}
        section[data-testid="stFileUploader"]::after {
            content: "💾 Limit 50MB per file • PDF";
            display: block;
            text-align: center;
            font-size: 0.9rem;
            color: #AAAAAA;
            margin-top: -12px;
        }
    </style>

    <h1 class="main-title">🚀 PaperPal</h1>
    <p class="sub-title">AI-powered research paper parser — extract sections, abstracts, and metadata in seconds.</p>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------
# 📂 File uploader
# -------------------------------------------------------
st.markdown("<div class='upload-box'>📄 Drop your PDF below</div>", unsafe_allow_html=True)
uploaded_file = st.file_uploader(
    "Upload your PDF (max 50 MB)",
    type=["pdf"],
    accept_multiple_files=False,
    label_visibility="collapsed"
)

# -------------------------------------------------------
# 🚀 Upload + process
# -------------------------------------------------------
if uploaded_file and st.button("✨ Analyze Paper", type="primary"):
    try:
        with st.spinner("📤 Uploading & analyzing your paper..."):
            file_bytes = uploaded_file.read()
            if len(file_bytes) > 50 * 1024 * 1024:
                st.error("❌ File too large. Please upload a file under 50 MB.")
                st.stop()

            files = {"file": (uploaded_file.name, file_bytes, "application/pdf")}
            resp = requests.post(BACKEND_URL, files=files, timeout=120)

        if resp.status_code != 200:
            st.error(f"❌ Upload failed (HTTP {resp.status_code})")
            st.text(resp.text)
        else:
            result = resp.json()
            st.success("✅ Paper processed successfully!")

            st.markdown("---")
            st.subheader("🧠 Extracted Paper Insights")


            if "metadata" in result:
                st.markdown("### 📇 Metadata")
                for k, v in result["metadata"].items():
                    st.write(f"**{k}:** {v}")

            if "sections" in result:
                st.markdown("### 📘 Sections")
                for s in result["sections"]:
                    with st.expander(f"📄 {s.get('title','Untitled')}"):
                        st.write(s.get("content",""))

            with st.expander("🧾 Raw JSON Response"):
                st.json(result)

    except requests.exceptions.RequestException as e:
        st.error(f"🌐 Network error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")
        st.exception(e)

# -------------------------------------------------------
# 🧠 Footer
# -------------------------------------------------------
st.markdown("---")
st.caption("Built  using FastAPI + Streamlit • PaperPal © 2025")
