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
    password = "your-default-password"  # fallback

# === Load & Decrypt Full AES Excel File ===
@st.cache_data
def load_student_data():
    # Replace with your raw GitHub .aes file link
    aes_url = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/Students_List.xlsx.aes"

    # Download the AES file
    response = requests.get(aes_url)
    if response.status_code != 200:
        st.error("❌ Failed to fetch encrypted file from GitHub.")
        st.stop()

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()

    try:
        # Decrypt in memory
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize, len(response.content))
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        df["RegNo"] = df["RegNo"].str.strip().str.upper()
        return df
    except Exception as e:
        st.error("❌ Failed to decrypt student list.")
        st.exception(e)
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

# === Streamlit App ===
st.set_page_config(page_title="Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

df_students = load_student_data()

# --- Login Section ---
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]

    if not student.empty:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        # Learning video section
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        if st.button("🎯 I have finished watching the video"):
            with st.spinner("Verifying..."):
                time.sleep(3)

            st.success("✅ Video watched! Your certificate is ready.")

            # Generate certificate
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )

            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)

    else:
        st.error("❌ Registration number not found!")
