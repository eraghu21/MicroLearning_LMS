import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# === AES Config ===
bufferSize = 64 * 1024
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"

# === Video duration in seconds ===
VIDEO_DURATION = 180  # 3 mins

# === Load & Decrypt Excel from GitHub ===
@st.cache_data
def load_encrypted_excel(url):
    response = requests.get(url)
    if response.status_code != 200:
        st.error("❌ Failed to fetch encrypted file from GitHub.")
        st.stop()
    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()
try:
    pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
    decrypted_stream.seek(0)
    df = pd.read_excel(decrypted_stream)
except Exception as e:
    st.error("❌ Failed to decrypt or process file.")
    st.exception(e)
    st.stop()


# === Load Student List ===
STUDENT_LIST_URL = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/Students_List.xlsx.aes"
df_students = load_encrypted_excel(STUDENT_LIST_URL)
df_students["RegNo"] = df_students["RegNo"].astype(str).str.strip().str.upper()

# === Load Progress File (Create if not exists) ===
PROGRESS_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/progress_encrypted.xlsx.aes"

try:
    df_progress = load_encrypted_excel(PROGRESS_URL)
except:
    # If progress file doesn't exist, initialize
    df_progress = df_students[["RegNo", "Name"]].copy()
    df_progress["VideoCompleted"] = False
    df_progress["CertDownloaded"] = False

# === Generate Certificate ===
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

# === Streamlit UI ===
st.set_page_config(page_title="Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

# --- Login ---
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]
    if student.empty:
        st.error("❌ Registration number not found!")
    else:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        # Get progress for this student
        progress = df_progress[df_progress["RegNo"] == regno].iloc[0]

        # --- Video Section ---
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # Replace with your video

        # Unique session per student
        session_key = f"timer_{regno}"

        # First time watching
        if not progress["VideoCompleted"]:
            if session_key not in st.session_state:
                st.session_state[session_key] = {"start_time": time.time(), "cert_ready": False}

            elapsed = time.time() - st.session_state[session_key]["start_time"]
            progress_ratio = min(elapsed / VIDEO_DURATION, 1.0)
            st.progress(progress_ratio, text="⏳ Watching video...")

            # Time remaining
            remaining = max(int(VIDEO_DURATION - elapsed), 0)
            mins, secs = divmod(remaining, 60)
            st.markdown(f"⏱️ Time left to complete: **{mins:02d}:{secs:02d}**")

            # Unlock certificate
            if elapsed >= VIDEO_DURATION and not st.session_state[session_key]["cert_ready"]:
                st.session_state[session_key]["cert_ready"] = True
                st.success("✅ Video completed! Certificate is ready.")
                # Update progress
                df_progress.loc[df_progress["RegNo"] == regno, ["VideoCompleted", "CertDownloaded"]] = True

            # Certificate download button (once)
            if st.session_state[session_key]["cert_ready"]:
                cert_file = generate_certificate(
                    student["Name"], regno, student["Dept"], student["Year"], student["Section"]
                )
                with open(cert_file, "rb") as f:
                    st.session_state[session_key]["cert_downloaded"] = True
                    st.download_button(
                        "⬇️ Download Certificate",
                        f,
                        file_name=cert_file,
                        help="You can download your certificate only once this session."
                    )

        # Already watched video before
        else:
            st.info("✅ You have already completed this video. Certificate is available for download.")
            # Show download button anytime
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )
            with open(cert_file, "rb") as f:
                st.download_button(
                    "⬇️ Download Certificate",
                    f,
                    file_name=cert_file,
                    help="Certificate can be downloaded anytime."
                )
