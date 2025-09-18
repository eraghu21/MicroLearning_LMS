import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# === AES Decryption Config ===
bufferSize = 64 * 1024
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"  # fallback if secrets not set

# === Load & Decrypt Encrypted Excel from GitHub ===
@st.cache_data
def load_student_data():
    aes_url = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/Students_List.xlsx.aes" 
    response = requests.get(aes_url)

    if response.status_code != 200:
        st.error("❌ Failed to fetch encrypted file from GitHub.")
        st.stop()

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()

    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize, len(response.content))
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        df["RegNo"] = df["RegNo"].astype(str).str.strip().str.upper()
        return df
    except Exception as e:
        st.error("❌ Failed to decrypt or process student list.")
        st.exception(e)
        st.stop()

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

# === App Config ===
st.set_page_config(page_title="Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

# === Load Data ===
df_students = load_student_data()

# === Login ===
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]

    if not student.empty:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        # === Video Section ===
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # Replace with your video
        VIDEO_DURATION = 180  # In seconds (e.g., 3 mins)

        # === Timer Logic ===
        if "start_time" not in st.session_state:
            st.session_state.start_time = time.time()
            st.session_state.cert_ready = False

        elapsed = time.time() - st.session_state.start_time
        progress = min(elapsed / VIDEO_DURATION, 1.0)
        st.progress(progress, text="⏳ Watching...")

        if elapsed >= VIDEO_DURATION:
            if not st.session_state.cert_ready:
                st.success("✅ Video completed!")
                st.session_state.cert_ready = True

        # === Certificate ===
        if st.session_state.cert_ready:
            st.success("🎉 Your certificate is ready!")

            cert_file = generate_certificate(
                student["Name"],
                regno,
                student["Dept"],
                student["Year"],
                student["Section"]
            )

            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)

        else:
            remaining = int(VIDEO_DURATION - elapsed)
            st.info(f"⏳ Please wait {remaining} more seconds to unlock your certificate.")

    else:
        st.error("❌ Registration number not found!")
