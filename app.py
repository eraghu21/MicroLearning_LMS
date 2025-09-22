import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import json
import datetime
from io import BytesIO
from email.message import EmailMessage
import smtplib
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -------------------- Configuration --------------------
BUFFER_SIZE = 64 * 1024
AES_FILE = "Students_List.xlsx.aes"
PROGRESS_FILE = "progress.json"
YOUTUBE_VIDEO_URL = "https://youtu.be/Tva_sr4BUfk?si=GukUUa-tY-VvYo73"

# -------------------- Load Secrets --------------------
password = None
email_sender = None
email_password = None

try:
    password = st.secrets["encryption"]["password"]
    email_sender = st.secrets["email"]["sender"]
    email_password = st.secrets["email"]["password"]
except Exception:
    password = "yourpassword"
    email_sender = "youremail@gmail.com"
    email_password = "your-email-app-password"

# -------------------- Helper Functions --------------------
@st.cache_data(show_spinner=False)
def load_students_list():
    try:
        with open(AES_FILE, "rb") as fIn:
            decrypted = BytesIO()
            pyAesCrypt.decryptStream(
                fIn, decrypted, password, BUFFER_SIZE, os.path.getsize(AES_FILE)
            )
            decrypted.seek(0)
            df = pd.read_excel(decrypted)
    except Exception:
        df = pd.read_excel(AES_FILE)

    df["RegNo"] = df["RegNo"].astype(str).str.strip()
    return df

def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {}
    with open(PROGRESS_FILE, "r") as f:
        return json.load(f)

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=4)

def generate_certificate(name, regno, dept, year, section):
    """Generate PDF certificate with department, year, section"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>Certificate of Completion</b>", styles['Title']))
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        f"This is to certify that <b>{name}</b> ({regno}), "
        f"Department of <b>{dept}</b>, Year: <b>{year}</b>, Section: <b>{section}</b> "
        f"has successfully completed the video.", styles['Normal']
    ))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Date: {datetime.date.today()}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def send_email(to, name, regno, cert_bytes):
    if not email_sender or not email_password:
        st.warning("⚠️ Email credentials not configured. Skipping email send.")
        return
    msg = EmailMessage()
    msg['Subject'] = "Your Certificate of Completion"
    msg['From'] = email_sender
    msg['To'] = to
    msg.set_content(f"Dear {name},\n\nCongratulations! Your certificate is attached.\n\nRegards,\nAdmin")
    msg.add_attachment(cert_bytes, maintype='application',
                       subtype='pdf',
                       filename=f"{regno}_certificate.pdf")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_sender, email_password)
        smtp.send_message(msg)

# -------------------- Streamlit App --------------------
st.title("🎓 Microlearning Certificate Portal")

regno = st.text_input("Enter your Registration Number").strip().upper()

if regno:
    students_df = load_students_list()
    student = students_df[students_df["RegNo"] == regno]
    if not student.empty:
        name = student.iloc[0]["Name"]
        email = student.iloc[0]["Email"]
        dept = student.iloc[0]["Department"]
        year = student.iloc[0]["Year"]
        section = student.iloc[0]["Section"]

        st.success(f"Welcome, {name} ({dept}, Year {year}, Section {section})")
        progress = load_progress()
        record = progress.get(regno, {})

        if record.get("video_completed"):
            st.info("✅ You have already completed the video.")
            if st.button("Download Certificate Again"):
                cert_bytes = generate_certificate(name, regno, dept, year, section)
                st.download_button("⬇️ Download Certificate", cert_bytes, file_name=f"{regno}_certificate.pdf")
        else:
            st.video(YOUTUBE_VIDEO_URL)

            # Timer setup (3 minutes = 180 seconds)
            if "start_time" not in st.session_state:
                st.session_state.start_time = datetime.datetime.now()

            elapsed = (datetime.datetime.now() - st.session_state.start_time).seconds
            remaining = max(0, 180 - elapsed)

            # Countdown with progress bar
            progress_percent = int(((180 - remaining) / 180) * 100)
            st.progress(progress_percent)
            st.write(f"⏳ Please watch the video. Button will appear in {remaining} seconds.")

            if remaining <= 0:
                if st.button("I have watched the complete video"):
                    cert_bytes = generate_certificate(name, regno, dept, year, section)

                    # Auto-download hack (show download immediately)
                    st.download_button("⬇️ Download Certificate", cert_bytes, file_name=f"{regno}_certificate.pdf")

                    # Auto-send email
                    try:
                        send_email(email, name, regno, cert_bytes)
                        st.success(f"📩 Certificate sent to {email}")
                    except:
                        st.warning("⚠️ Failed to send email.")

                    # Save progress
                    progress[regno] = {
                        "name": name,
                        "email": email,
                        "department": dept,
                        "year": year,
                        "section": section,
                        "video_completed": True,
                        "certificate_sent": True,
                        "timestamp": str(datetime.datetime.now())
                    }
                    save_progress(progress)
    else:
        st.error("Registration number not found.")
