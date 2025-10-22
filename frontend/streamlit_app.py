import os
import streamlit as st
from dotenv import load_dotenv
from api import BackendClient

# -------------------------------------------------------
# 🌍 Load environment variables
# -------------------------------------------------------
load_dotenv()  # Load .env from frontend folder

# -------------------------------------------------------
# 🎨 Page setup
# -------------------------------------------------------
st.set_page_config(page_title="PaperPal Frontend", page_icon="📄", layout="wide")

st.title("📄 Upload PDF → Extract Sections & Metadata")
st.write("Upload a PDF to send to the FastAPI backend and visualize the parsed output.")

# -------------------------------------------------------
# ⚙️ Sidebar: Settings
# -------------------------------------------------------
st.sidebar.header("⚙️ Settings")

backend_url = st.sidebar.text_input("Backend URL", os.getenv("BACKEND_BASE_URL", "http://localhost:8000"))
api_prefix = st.sidebar.text_input("API Prefix", os.getenv("API_PREFIX", "/api/v1"))
upload_route = st.sidebar.text_input("Upload Route", os.getenv("API_UPLOAD_ROUTE", "/papers/upload"))
token = st.sidebar.text_input("Bearer Token (optional)", os.getenv("API_BEARER_TOKEN", ""), type="password")

apply_btn = st.sidebar.button("Apply Changes")

# Create or update the backend client when settings change
if "client" not in st.session_state or apply_btn:
    os.environ["BACKEND_BASE_URL"] = backend_url
    os.environ["API_PREFIX"] = api_prefix
    os.environ["API_UPLOAD_ROUTE"] = upload_route
    os.environ["API_BEARER_TOKEN"] = token
    st.session_state.client = BackendClient(base_url=backend_url, api_prefix=api_prefix, token=token)

# -------------------------------------------------------
# 📂 File uploader
# -------------------------------------------------------
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], accept_multiple_files=False)

if uploaded_file and st.button("Upload & Process", type="primary"):
    try:
        st.info("📤 Uploading to backend… please wait.")
        bytes_data = uploaded_file.read()
        filename = uploaded_file.name
        result = st.session_state.client.upload_pdf(bytes_data, filename)
        st.success("✅ Upload successful!")

        # -------------------------------------------------------
        # 🧩 Display result
        # -------------------------------------------------------
        st.subheader("🧩 Parsed Metadata and Sections")

        # 🧠 Paper Title
        if "paper_title" in result:
            st.markdown("### 🧠 Paper Title")
            st.write(result["paper_title"])

        # 📇 Metadata (optional)
        if "metadata" in result:
            st.markdown("### 📇 Metadata")
            for k, v in result["metadata"].items():
                st.write(f"**{k}:** {v}")

        # 📘 Sections
        if "sections" in result:
            st.markdown("### 📘 Sections")
            for section in result["sections"]:
                st.markdown(f"#### {section.get('title', 'Untitled')}")
                st.write(section.get("content", ""))  # ✅ fixed key name

        # 🔍 Raw JSON
        with st.expander("🔍 Raw JSON response"):
            st.json(result)

    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
        st.exception(e)
