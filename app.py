import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import os
from datetime import datetime

# Try FPDF, fallback to ReportLab
try:
    from fpdf import FPDF
    USE_FPDF = True
except ModuleNotFoundError:
    USE_FPDF = False
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from PIL import Image

# === Config ===
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your YouTube video
AES_FILE = st.secrets["aes"]["file"]             # Student list AES
AES_PASSWORD = st.secrets["aes"]["password"]
AES_BG_IMAGE = st.secrets["aes"]["bg_image"]     # Background image AES

# === Load and decrypt student list ===
@st.cache_data(show_spinner=True)
def load_students():
    try:
        decrypted = io.BytesIO()
        with open(AES_FILE, "rb") as f:
            f.seek(0, 2)
            file_len = f.tell()
            f.seek(0)
            pyAesCrypt.decryptStream(f, decrypted, AES_PASSWORD, BUFFER_SIZE, file_len)
        decrypted.seek(0)
        df = pd.read_excel(decrypted)
        df["RegNo"] = df["RegNo"].astype(str).str.strip()
        df["Name"] = df["Name"].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Failed to decrypt student file: {e}")
        return None

# === Decrypt background image to BytesIO ===
@st.cache_data(show_spinner=True)
def load_bg_image():
    try:
        decrypted = io.BytesIO()
        with open(AES_BG_IMAGE, "rb") as f:
            f.seek(0, 2)
            file_len = f.tell()
            f.seek(0)
            pyAesCrypt.decryptStream(f, decrypted, AES_PASSWORD, BUFFER_SIZE, file_len)
        decrypted.seek(0)
        return decrypted
    except Exception as e:
        st.warning(f"⚠️ Failed to decrypt background image: {e}")
        return None

# === Generate certificate ===
def generate_certificate(name, regno, bg_bytesio=None):
    file_path = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if USE_FPDF:
        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        if bg_bytesio:
            # Save temp image from BytesIO for FPDF
            temp_img_path = os.path.join(CERT_DIR, "temp_bg.jpg")
            with open(temp_img_path, "wb") as f:
                f.write(bg_bytesio.read())
            pdf.image(temp_img_path, x=0, y=0, w=297, h=210)
            bg_bytesio.seek(0)
        pdf.set_font("Helvetica", 'B', 32)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 50, "Certificate of Completion", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Helvetica", '', 24)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 20, "This is to certify that", ln=True, align="C")
        pdf.set_font("Helvetica", 'B', 28)
        pdf.cell(0, 20, name, ln=True, align="C")
        pdf.set_font("Helvetica", '', 20)
        pdf.cell(0, 15, f"Registration No: {regno}", ln=True, align="C")
        pdf.ln(5)
        pdf.cell(0, 15, "has successfully completed the video session.", ln=True, align="C")
        pdf.ln(20)
        pdf.set_font("Helvetica", '', 16)
        pdf.cell(0, 10, f"Date & Time: {timestamp}", ln=True, align="R")
        pdf.output(file_path)

    else:
        # ReportLab fallback
        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4
        if bg_bytesio:
            img = Image.open(bg_bytesio)
            img_reader = ImageReader(img)
            c.drawImage(img_reader, 0, 0, width=width, height=height)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height-100, "Certificate of Completion")
        c.setFont("Helvetica", 14)
        c.drawCentredString(width/2, height-140, f"This is to certify that {name}")
        c.drawCentredString(width/2, height-160, f"Reg No: {regno}")
        c.drawCentredString(width/2, height-190, "has successfully completed the video session.")
        c.drawCentredString(width/2, height-210, f"Date & Time: {timestamp}")
        c.save()

    return file_path

# === Main App ===
def main():
    st.title("🎓 Student LMS")

    student_df = load_students()
    if student_df is None:
        return

    bg_image_bytes = load_bg_image()

    regno = st.text_input("Enter your Registration Number:").strip()
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
                cert_file = generate_certificate(name, regno, bg_image_bytes)
                st.success("🎉 Certificate generated! You can download it now.")
                with open(cert_file, "rb") as f:
                    st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))

if __name__ == "__main__":
    main()
