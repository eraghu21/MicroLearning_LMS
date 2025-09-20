import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
import json
import smtplib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from email.message import EmailMessage
from github import Github

# === CONFIG ===
VIDEO_DURATION = 180  # in seconds (This will now be dynamically updated by YouTube API)
bufferSize = 64 * 1024
REPO_NAME = "eraghu21/MicroLearning_LMS"
PROGRESS_FILE = "progress.json.aes"
STUDENT_LIST_FILE = "Students_List.xlsx.aes"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/"
YOUTUBE_VIDEO_ID = "dQw4w9WgXcQ" # The ID of the video to play

# === SECRETS ===
def get_secret(key):
    try:
        return st.secrets[key]
    except KeyError:
        st.error(f"❌ Missing secret: {key}. Please configure it in Streamlit secrets.")
        st.stop()

password = get_secret("encryption_password")
github_token = get_secret("github_token")
email_sender = get_secret("email_sender")
email_password = get_secret("email_password")

# === LOAD ENCRYPTED EXCEL ===
@st.cache_data
def load_encrypted_excel(filename):
    url = GITHUB_RAW_BASE + filename
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"❌ Failed to fetch file from GitHub. Status: {response.status_code}")
        st.stop()
    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()
    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        return df
    except Exception:
        st.error("❌ Failed to decrypt student list. Check encryption password.")
        st.stop()

# === LOAD PROGRESS ===
def load_encrypted_progress():
    url = GITHUB_RAW_BASE + PROGRESS_FILE
    response = requests.get(url)
    if response.status_code != 200:
        return {}
    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()
    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        return json.load(decrypted_stream)
    except Exception:
        st.error("❌ Failed to decrypt progress data. Check encryption password.")
        return {}

# === SAVE PROGRESS ===
def save_progress_to_github(progress_dict):
    content = json.dumps(progress_dict, indent=4)
    content_bytes = content.encode("utf-8")
    f_in = io.BytesIO(content_bytes)
    f_out = io.BytesIO()
    pyAesCrypt.encryptStream(f_in, f_out, password, bufferSize)
    f_out.seek(0)
    g = Github(github_token)
    repo = g.get_repo(REPO_NAME)
    try:
        contents = repo.get_contents(PROGRESS_FILE)
        repo.update_file(contents.path, "Update progress", f_out.read(), contents.sha)
    except Exception:
        f_out.seek(0)
        repo.create_file(PROGRESS_FILE, "Create progress file", f_out.read())

# === CERTIFICATE GENERATION ===
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
    c.drawCentredString(300, 570, f"Issued on: {datetime.today().strftime("%d-%m-%Y")}")
    c.showPage()
    c.save()
    return filename

# === EMAIL SENDER ===
def send_certificate(email, name, regno, cert_path):
    msg = EmailMessage()
    msg["Subject"] = "Your Microlearning Certificate"
    msg["From"] = email_sender
    msg["To"] = email
    msg.set_content(f"Dear {name},\n\nCongratulations on completing the microlearning module!\n\nAttached is your certificate.\n\nRegards,\nTeam")

    with open(cert_path, "rb") as f:
        cert_data = f.read()
    msg.add_attachment(cert_data, maintype="application", subtype="pdf", filename=f"certificate_{regno}.pdf")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_sender, email_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Failed to send email: {e}")
        return False

# === STREAMLIT APP ===
st.set_page_config(page_title="🎓 Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

df_students = load_encrypted_excel(STUDENT_LIST_FILE)
df_students["RegNo"] = df_students["RegNo"].astype(str).str.strip().str.upper()
progress_data = load_encrypted_progress()

# === LOGIN ===
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]
    if student.empty:
        st.error("❌ Registration number not found!")
    else:
        student = student.iloc[0]
        st.success(f"Welcome **{student["Name"]}**!")

        already_completed = progress_data.get(regno, {}).get("completed", False)

        if not already_completed:
            # Embed YouTube video using iframe and JavaScript API
            st.components.v1.html(f"""
                <div id=\'player\'></div>
                <script>
                  var tag = document.createElement(\'script\');
                  tag.src = "https://www.youtube.com/iframe_api";
                  var firstScriptTag = document.getElementsByTagName(\'script\')[0];
                  firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

                  var player;
                  function onYouTubeIframeAPIReady() {{
                    player = new YT.Player(\'player\', {{
                      height: \'360\',
                      width: \'640\',
                      videoId: \'{YOUTUBE_VIDEO_ID}\,',
                      events: {{
                        \'onReady\': onPlayerReady,
                        \'onStateChange\': onPlayerStateChange
                      }}
                    }});
                  }}

                  function onPlayerReady(event) {{
                    // You can add any on-ready logic here if needed
                  }}

                  function onPlayerStateChange(event) {{
                    if (event.data == YT.PlayerState.ENDED) {{
                      // Send a message to Streamlit when the video ends
                      window.parent.postMessage({{
                        type: \'streamlit:setComponentValue\',
                        value: {{ video_ended: true }}
                      }}, \'*
                      \');
                    }}
                  }}
                </script>
                """.format(YOUTUBE_VIDEO_ID=YOUTUBE_VIDEO_ID), height=400)

            # Check for the video ended message from JavaScript
            video_ended = st.session_state.get("video_ended", False)

            if video_ended:
                cert_file = generate_certificate(
                    student["Name"], regno, student["Dept"], student["Year"], student["Section"]
                )
                sent = send_certificate(student["Email"], student["Name"], regno, cert_file)
                if sent:
                    progress_data[regno] = {
                        "name": student["Name"],
                        "completed": True,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    save_progress_to_github(progress_data)
                    st.success("🎉 Video completed! Certificate emailed and ready to download.")
                    with open(cert_file, "rb") as f:
                        st.download_button("⬇️ Download Certificate", f, file_name=cert_file)
        else:
            st.info("✅ Already completed. You can download your certificate.")
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )
            with open(cert_file, "rb") as f:
                st.download_button("⬇️ Download Certificate", f, file_name=cert_file)


