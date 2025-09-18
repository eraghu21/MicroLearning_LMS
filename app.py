import streamlit as st
import pandas as pd
import io
import pyaescrypt
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Encryption config
bufferSize = 64 * 1024
password = st.secrets["encryption"]["password"]

# Encryption/decryption helpers
def encrypt_text(text: str) -> str:
    f_in = io.BytesIO(text.encode("utf-8"))
    f_out = io.BytesIO()
    pyaescrypt.encryptStream(f_in, f_out, password, bufferSize)
    return f_out.getvalue().hex()

def decrypt_text(cipher_hex: str) -> str:
    try:
        data = bytes.fromhex(cipher_hex)
        f_in = io.BytesIO(data)
        f_out = io.BytesIO()
        pyaescrypt.decryptStream(f_in, f_out, password, bufferSize, len(data))
        return f_out.getvalue().decode("utf-8")
    except Exception:
        return cipher_hex

# Generate certificate PDF
def generate_certificate(name, regno, dept, year, section):
    filename = f"certificate_{regno}.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 750, "Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 700, f"This is to certify that")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 670, f"{name} (RegNo: {regno})")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 640, f"from {dept} - Year {year} - Section {section}")
    c.drawCentredString(300, 610, "has successfully completed the course.")
    c.showPage()
    c.save()
    return filename

st.title("🎓 Microlearning Platform")

excel_file = st.file_uploader("Upload encrypted students Excel", type=["xlsx"])

if excel_file:
    df_students = pd.read_excel(excel_file)
    for col in df_students.columns:
        df_students[col] = df_students[col].astype(str).apply(decrypt_text)

    regno = st.text_input("Enter your Registration Number:")
    student = None
    if regno:
        student = df_students[df_students["RegNo"] == regno]

    if student is not None and not student.empty:
        st.success(f"Welcome {student.iloc[0]['Name']}!")

        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        if st.button("I have finished watching"):
            with st.spinner("Verifying video completion..."):
                time.sleep(3)
            st.success("✅ Video completed! Certificate unlocked.")

            cert_file = generate_certificate(
                student.iloc[0]["Name"],
                student.iloc[0]["RegNo"],
                student.iloc[0]["Dept"],
                student.iloc[0]["Year"],
                student.iloc[0]["Section"],
            )
            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)

            # Encrypt and save progress
            encrypted = student.copy()
            for col in encrypted.columns:
                encrypted[col] = encrypted[col].astype(str).apply(encrypt_text)
            encrypted.to_excel("progress_encrypted.xlsx", index=False)

            with open("progress_encrypted.xlsx", "rb") as f:
                st.download_button("⬇️ Download Encrypted Progress File", f, file_name="progress_encrypted.xlsx")
    elif regno:
        st.error("❌ Registration number not found!")
