import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# === Config ===
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your YouTube embed link
AES_FILE = "students.xlsx.aes"  # Encrypted student list
AES_PASSWORD = "your_aes_password_here"  # ⚠️ keep in st.secrets in production!

# === Decrypt Excel File ===
def load_students():
    try:
        decrypted = io.BytesIO()
        with open(AES_FILE, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_len = f.tell()
            f.seek(0)
            pyAesCrypt.decryptStream(f, decrypted, AES_PASSWORD, BUFFER_SIZE, file_len)
        decrypted.seek(0)
        df = pd.read_excel(decrypted)
        return df
    except Exception as e:
        st.error("❌ Failed to decrypt student file.")
        return None

# === Certificate Generator ===
def generate_certificate(name, regno):
    file_path = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(300, 750, "Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 700, f"This is to certify that {name}")
    c.drawCentredString(300, 675, f"Reg No: {regno}")
    c.drawCentredString(300, 640, "has successfully completed the video session.")
    c.drawCentredString(300, 610, f"Date: {datetime.today().strftime('%Y-%m-%d')}")
    c.save()
    return file_path

# === Main App ===
def main():
    st.title("🎓 Student LMS")

    # Load student list once
    student_df = load_students()
    if student_df is None:
        return

    regno = st.text_input("Enter your Registration Number:")

    if regno:
        student = student_df[student_df["RegNo"] == regno]
        if student.empty:
            st.error("❌ Invalid Registration Number")
            return

        name = student.iloc[0]["Name"]
        st.success(f"Welcome {name} (RegNo: {regno})")

        cert_file = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")

        if os.path.exists(cert_file):
            st.info("✅ You already watched the video. Download your certificate below.")
            with open(cert_file, "rb") as f:
                st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))
        else:
            st.video(VIDEO_URL)
            if st.button("✅ I have watched the video"):
                cert_file = generate_certificate(name, regno)
                st.success("🎉 Certificate generated! You can download it now.")
                with open(cert_file, "rb") as f:
                    st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))

if __name__ == "__main__":
    main()
