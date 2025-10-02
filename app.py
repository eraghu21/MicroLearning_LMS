import streamlit as st
import streamlit.components.v1 as components
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

BG_IMAGE_PATH = save_certificate_background()

# ====================== CONFIG ======================
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your video
VIDEO_DURATION = 30  # Video duration in seconds

AES_FILE = st.secrets["aes"]["file"]           # AES encrypted student file
AES_PASSWORD = st.secrets["aes"]["password"]   # AES password

PROGRESS_FILE = "progress.csv"
ADMIN_PASSWORD = st.secrets["admin"]["password"]  # Admin view password

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

# ====================== PROGRESS LOG ======================
def update_progress(regno, name):
    if os.path.exists(PROGRESS_FILE):
        df = pd.read_csv(PROGRESS_FILE)
    else:
        df = pd.DataFrame(columns=["RegNo", "Name", "Video_Status", "Certificate_Status", "Timestamp"])
    df = df[df["RegNo"] != regno]
    new_row = {
        "RegNo": regno,
        "Name": name,
        "Video_Status": "Completed",
        "Certificate_Status": "Downloaded",
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(PROGRESS_FILE, index=False)

# ====================== VIDEO WITH TIMER ======================
def show_video_with_timer(video_url, duration_sec):
    html_code = f"""
    <div>
        <iframe width="800" height="450" src="{video_url}" frameborder="0" allowfullscreen></iframe>
        <p id="timer_text">⏳ Watch the video. Time left: {duration_sec} seconds</p>
        <script>
            var timeLeft = {duration_sec};
            var timerText = document.getElementById("timer_text");
            localStorage.removeItem("video_finished");
            var countdown = setInterval(function() {{
                if(timeLeft <= 0) {{
                    clearInterval(countdown);
                    timerText.innerHTML = "✅ You have finished the video. Button enabled.";
                    localStorage.setItem("video_finished", "true");
                    window.parent.postMessage({{video_done:true}}, "*");
                }} else {{
                    timerText.innerHTML = "⏳ Watch the video. Time left: " + timeLeft + " seconds";
                }}
                timeLeft -= 1;
            }}, 1000);
        </script>
    </div>
    """
    components.html(html_code, height=500, scrolling=True)

# ====================== MAIN APP ======================
def main():
    st.title("🎓 Student LMS")

    # Sidebar admin access
    st.sidebar.header("🔐 Admin Access")
    admin_pass = st.sidebar.text_input("Enter admin password", type="password")
    if admin_pass == ADMIN_PASSWORD:
        st.sidebar.success("✅ Admin access granted")
        if os.path.exists(PROGRESS_FILE):
            df_progress = pd.read_csv(PROGRESS_FILE)
            st.sidebar.subheader("📊 Student Progress")
            st.sidebar.dataframe(df_progress)
        else:
            st.sidebar.info("No progress data yet.")

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

        if st.session_state.get("current_student") != regno:
            st.session_state.video_finished = False
            st.session_state.current_student = regno

        # Show video
        if not st.session_state.video_finished:
            show_video_with_timer(VIDEO_URL, VIDEO_DURATION)

        # “I have watched video” button
        if not st.session_state.video_finished:
            if st.button("✅ I have watched the video"):
                st.session_state.video_finished = True

        # Show certificate download & update progress
        if st.session_state.video_finished or os.path.exists(cert_file):
            if not os.path.exists(cert_file):
                cert_file = generate_certificate(name, regno)
            update_progress(regno, name)
            with open(cert_file, "rb") as f:
                st.download_button(
                    label="📄 Download Certificate",
                    data=f,
                    file_name=os.path.basename(cert_file),
                    key=f"download_{regno}_final"
                )

if __name__ == "__main__":
    main()
