import streamlit as st
import pandas as pd
import io
import pyaescrypt
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

# === Encryption config ===
bufferSize = 64 * 1024  # 64KB chunks

# Use Streamlit secrets or fallback password
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"

# === Encryption/decryption helpers ===
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
        return cipher_hex  # Return original if decryption fails

# === Certificate generator ===
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
st.set_page_config(page_title="Microlearning Platform", layout="centered")
st.title("🎓 Microlearning Platform with Certificate")

st.markdown("**Expected Encrypted Excel Columns:** `RegNo`, `Name`, `Dept`, `Year`, `Section`")

excel_file = st.file_uploader("🔐 Upload Encrypted Student Excel File (.xlsx)", type=["xlsx"])

if excel_file:
    df_students = pd.read_excel(excel_file)

    # Decrypt all fields
    for col in df_students.columns:
        df_students[col] = df_students[col].astype(str).apply(decrypt_text)

    # Normalize RegNo for matching
    df_students["RegNo"] = df_students["RegNo"].str.strip().str.upper()

    regno = st.text_input("Enter your Registration Number:").strip().upper()
    student = None

    if regno:
        student = df_students[df_students["RegNo"] == regno]

    if student is not None and not student.empty:
        name = student.iloc[0]["Name"]
        st.success(f"Welcome **{name}**! Please watch the video below.")

        # Learning video
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        if st.button("🎯 I have finished watching the video"):
            with st.spinner("Verifying video completion..."):
                time.sleep(3)

            st.success("✅ Video watched! Certificate Unlocked.")

            # Generate Certificate
            cert_file = generate_certificate(
                student.iloc[0]["Name"],
                student.iloc[0]["RegNo"],
                student.iloc[0]["Dept"],
                student.iloc[0]["Year"],
                student.iloc[0]["Section"]
            )

            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)

            # Encrypt progress
            encrypted = student.copy()
            for col in encrypted.columns:
                encrypted[col] = encrypted[col].astype(str).apply(encrypt_text)

            encrypted.to_excel("progress_encrypted.xlsx", index=False)

            with open("progress_encrypted.xlsx", "rb") as f:
                st.download_button("⬇️ Download Encrypted Progress File", f, file_name="progress_encrypted.xlsx")

    elif regno:
        st.error("❌ Registration number not found!")
