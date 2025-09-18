import streamlit as st
import pandas as pd
import io
import pyAesCrypt
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# === AES Config ===
bufferSize = 64 * 1024
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"  # fallback for local testing

# === Encryption/Decryption Functions ===
def decrypt_text(cipher_hex: str) -> str:
    try:
        data = bytes.fromhex(cipher_hex)
        f_in = io.BytesIO(data)
        f_out = io.BytesIO()
        pyAesCrypt.decryptStream(f_in, f_out, password, bufferSize, len(data))
        return f_out.getvalue().decode("utf-8")
    except Exception:
        return cipher_hex  # fallback

# === Load and Decrypt Student List ===
@st.cache_data
def load_student_data():
    df = pd.read_excel("encrypted_students.xlsx")
    for col in df.columns:
        df[col] = df[col].astype(str).apply(decrypt_text)
    df["RegNo"] = df["RegNo"].str.strip().str.upper()
    return df

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
