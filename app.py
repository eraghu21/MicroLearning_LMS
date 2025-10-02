import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import os
from datetime import datetime
import base64

# ====================== EMBEDDED CERTIFICATE BACKGROUND ======================
certificate_base64 = """
PASTE_YOUR_BASE64_STRING_HERE
"""

def save_certificate_background():
    """Decode the embedded Base64 image and save as a JPEG file."""
    try:
        img_bytes = base64.b64decode(certificate_base64)
        CERT_DIR = "certificates"
        os.makedirs(CERT_DIR, exist_ok=True)
        file_path = os.path.join(CERT_DIR, "certificate_bg.jpeg")
        with open(file_path, "wb") as f:
            f.write(img_bytes)
        return file_path
    except Exception as e:
        st.warning(f"⚠️ Failed to save background image: {e}")
        return None

# Save background image and get path
BG_IMAGE_PATH = save_certificate_background()

# ====================== CONFIG ======================
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your video
AES_FILE = st.secrets["aes"]["file"]           # AES encrypted student file
AES_PASSWORD = st.secrets["aes"]["password"]   # AES password

# ====================== LOAD STUDENTS ======================
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
        st.error(f"❌ Failed to load/decrypt student file: {e}")
        return None

# ====================== GENERATE CERTIFICATE ======================
def generate_certificate(name, regno):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")

    # Try using FPDF first
    try:
        from fpdf import FPDF
        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        if BG_IMAGE_PATH:
            pdf.image(BG_IMAGE_PATH, x=0, y=0, w=297, h=210)
        pdf.set_font("Helvetica", 'B', 32)
        pdf.cell(0, 50, "Certificate of Completion", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("Helvetica", '', 24)
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

    except ModuleNotFoundError:
        # Fallback to ReportLab
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from PIL import Image
        from reportlab.lib.utils import ImageReader

        width, height = A4
        c = canvas.Canvas(file_path, pagesize=A4)
        if BG_IMAGE_PATH:
            img = Image.open(BG_IMAGE_PATH)
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

# ====================== MAIN APP ======================
def main():
    st.title("🎓 Student LMS")

    student_df = load_students()
    if student_df is None:
        return

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
                cert_file = generate_certificate(name, regno)
                st.success("🎉 Certificate generated! You can download it now.")
                with open(cert_file, "rb") as f:
                    st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))

if __name__ == "__main__":
    main()
