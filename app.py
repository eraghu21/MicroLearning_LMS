import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# === CONFIG ===
bufferSize = 64 * 1024
VIDEO_DURATION = 180  # seconds (3 mins)
STUDENT_LIST_URL = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/Students_List.xlsx.aes"

# === Password from secrets or fallback
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"

# === Load Encrypted Excel from GitHub ===
@st.cache_data
def load_encrypted_excel(url):
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"❌ Failed to fetch file from GitHub. Status code: {response.status_code}")
        st.stop()

    if len(response.content) < 32 or response.content[:4] == b'<htm':
        st.error("❌ GitHub file format invalid. Use raw.githubusercontent.com URL.")
        st.stop()

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()

    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        return df
    except Exception as e:
        st.error("❌ Decryption failed. Check password or file format.")
        st.stop()

# === Certificate Generator ===
def generate_certificate(name, regno, dept, year, section):
    filename = f"certificate_{regno}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 750, "Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 700, "This is to certify that")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 670, f"{name} (RegNo: {regno})")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 640, f"from {dept} - Year {year} - Section {section}")
    c.drawCentredString(300, 610, "has successfully completed the microlearning module.")
    c.setFont("Helvetica", 12)
    c.drawCentredString(300, 570, f"Issued on: {datetime.today().strftime('%d-%m-%Y')}")
    c.showPage()
    c.save()
    return filename

# === App UI Setup ===
st.set_page_config(page_title="🎓 Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

df_students = load_encrypted_excel(STUDENT_LIST_URL)
df_students["RegNo"] = df_students["RegNo"].astype(str).str.strip().str.upper()

# === Student Login ===
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

# Session Setup
if "progress" not in st.session_state:
    st.session_state.progress = {}

# === Auth Logic ===
if regno:
    student = df_students[df_students["RegNo"] == regno]
    if student.empty:
        st.error("❌ Registration number not found!")
    else:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        # Initialize progress
        if regno not in st.session_state.progress:
            st.session_state.progress[regno] = {
                "start_time": time.time(),
                "video_completed": False
            }

        progress = st.session_state.progress[regno]

        # === Video Display ===
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        # === Timer Logic ===
        elapsed = time.time() - progress["start_time"]
        remaining = max(0, int(VIDEO_DURATION - elapsed))
        progress_percent = min(elapsed / VIDEO_DURATION, 1.0)

        if not progress["video_completed"]:
            st.progress(progress_percent, text="⏳ Watching video...")
            mins, secs = divmod(remaining, 60)
            st.markdown(f"⏱️ Time left to unlock certificate: **{mins:02d}:{secs:02d}**")

            if remaining == 0:
                progress["video_completed"] = True
                st.success("✅ Video completed! Certificate is now available.")
            else:
                st.info("🔄 Please refresh this page after video finishes to get your certificate.")

        else:
            st.info("ℹ️ You’ve already completed the video. Certificate is available.")

        # === Certificate Button ===
        if progress["video_completed"]:
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )
            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)
