
import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from github import Github

# === CONFIG ===
VIDEO_DURATION = 180  # seconds
bufferSize = 64 * 1024
REPO_NAME = "eraghu21/MicroLearning_LMS"
PROGRESS_FILE = "progress.json.aes"
STUDENT_LIST_FILE = "Students_List.xlsx.aes"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/"

# === Secrets ===
try:
    password = st.secrets["encryption"]["password"]
    github_token = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("âŒ Missing encryption password or GitHub token in secrets.")
    st.stop()

# === Load Encrypted Excel from GitHub ===
@st.cache_data
def load_encrypted_excel(filename):
    url = GITHUB_RAW_BASE + filename
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"âŒ Failed to fetch file from GitHub. Status: {response.status_code}")
        st.stop()

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()
    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        return df
    except Exception as e:
        st.error("âŒ Failed to decrypt student list.")
        st.stop()

# === Load Encrypted JSON from GitHub ===
def load_encrypted_progress():
    url = GITHUB_RAW_BASE + PROGRESS_FILE
    response = requests.get(url)
    if response.status_code != 200:
        return {}  # No progress file yet

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()
    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        return json.load(decrypted_stream)
    except Exception as e:
        st.warning("âš ï¸ Couldn't load progress file. Starting fresh.")
        return {}

# === Save Encrypted JSON to GitHub ===
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

# === App Layout ===
st.set_page_config(page_title="ðŸŽ“ Microlearning LMS", layout="centered")
st.title("ðŸŽ“ Microlearning Platform")

df_students = load_encrypted_excel(STUDENT_LIST_FILE)
df_students["RegNo"] = df_students["RegNo"].astype(str).str.strip().str.upper()

progress_data = load_encrypted_progress()

# === Login ===
st.subheader("ðŸ” Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]
    if student.empty:
        st.error("âŒ Registration number not found!")
    else:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        already_completed = progress_data.get(regno, {}).get("completed", False)

        if not already_completed:
            if "start_time" not in st.session_state:
                st.session_state.start_time = time.time()

            elapsed = time.time() - st.session_state.start_time
            remaining = max(0, int(VIDEO_DURATION - elapsed))
            progress_percent = min(elapsed / VIDEO_DURATION, 1.0)

            st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

            st.progress(progress_percent, text="â³ Watching video...")
            mins, secs = divmod(remaining, 60)
            st.markdown(f"â±ï¸ Time left to unlock certificate: **{mins:02d}:{secs:02d}**")

            if remaining == 0:
                progress_data[regno] = {
                    "name": student["Name"],
                    "completed": True,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                save_progress_to_github(progress_data)
                st.success("ðŸŽ‰ Video completed! Certificate is now available.")
        else:
            st.info("â„¹ï¸ You have already completed the video. You can download your certificate.")

        if progress_data.get(regno, {}).get("completed", False):
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )
            with open(cert_file, "rb") as f:
                st.download_button("â¬‡ï¸ Download Certificate", f, file_name=cert_file)
