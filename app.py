import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
import time
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# === AES Config ===
bufferSize = 64 * 1024
try:
    password = st.secrets["encryption"]["password"]
except Exception:
    password = "your-default-password"

# === Google Sheets Config ===
try:
    service_account_info = st.secrets["gcp_service_account"]

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        dict(service_account_info),
        scopes=scopes
    )
    gclient = gspread.authorize(credentials)

    # TODO: replace with your real Google Sheet URL
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1IYQaHWgRwKwQYvxpE-bQYsHozuxIIkceufynUZwBwdI/edit?gid=0#gid=0"
    sheet = gclient.open_by_url(SHEET_URL).sheet1

except Exception as e:
    sheet = None
    st.error("⚠️ Could not connect to Google Sheets. Check secrets.toml and permissions.")
    st.exception(e)

# === Video duration in seconds ===
VIDEO_DURATION = 180  # 3 minutes

# === Load & Decrypt Excel from GitHub with validation ===
@st.cache_data
def load_encrypted_excel(url):
    response = requests.get(url)
    if response.status_code != 200:
        st.error(f"❌ Failed to fetch file from GitHub. Status code: {response.status_code}")
        st.stop()

    if len(response.content) < 32:
        st.error("❌ Downloaded file seems too small to be a valid AES file.")
        st.stop()
    if response.content[:4] == b'<htm':
        st.error("❌ GitHub link points to an HTML page, not the raw AES file.")
        st.stop()

    encrypted_bytes = io.BytesIO(response.content)
    decrypted_stream = io.BytesIO()

    try:
        pyAesCrypt.decryptStream(encrypted_bytes, decrypted_stream, password, bufferSize)
        decrypted_stream.seek(0)
        df = pd.read_excel(decrypted_stream)
        return df
    except ValueError:
        st.error("❌ Decryption failed: wrong password or invalid AES file.")
        st.stop()
    except Exception as e:
        st.error("❌ Failed to process decrypted file.")
        st.exception(e)
        st.stop()

# === Load Student List ===
STUDENT_LIST_URL = "https://raw.githubusercontent.com/eraghu21/MicroLearning_LMS/main/Students_List.xlsx.aes"
df_students = load_encrypted_excel(STUDENT_LIST_URL)
df_students["RegNo"] = df_students["RegNo"].astype(str).str.strip().str.upper()

# === Initialize Progress Tracking (local session) ===
if "progress" not in st.session_state:
    st.session_state.progress = pd.DataFrame({
        "RegNo": df_students["RegNo"],
        "Name": df_students["Name"],
        "VideoCompleted": False,
        "CertDownloaded": False
    })

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

# === Save Progress to Google Sheets ===
def save_progress_to_gsheet(regno, name, status):
    if sheet is None:
        return
    try:
        sheet.append_row([regno, name, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    except Exception as e:
        st.error("⚠️ Failed to update Google Sheet.")
        st.exception(e)

# === Streamlit UI ===
st.set_page_config(page_title="Microlearning LMS", layout="centered")
st.title("🎓 Microlearning Platform")

# --- Login ---
st.subheader("🔐 Student Login")
regno = st.text_input("Enter your Registration Number:").strip().upper()

if regno:
    student = df_students[df_students["RegNo"] == regno]
    if student.empty:
        st.error("❌ Registration number not found!")
    else:
        student = student.iloc[0]
        st.success(f"Welcome **{student['Name']}**!")

        # Get student progress
        idx = st.session_state.progress.index[st.session_state.progress["RegNo"] == regno][0]
        progress = st.session_state.progress.loc[idx]

        # --- Video Section ---
        st.video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")  # Replace with your video
        session_key = f"timer_{regno}"

        if not progress["VideoCompleted"]:
            if session_key not in st.session_state:
                st.session_state[session_key] = {"start_time": time.time(), "cert_ready": False}

            elapsed = time.time() - st.session_state[session_key]["start_time"]
            progress_ratio = min(elapsed / VIDEO_DURATION, 1.0)
            st.progress(progress_ratio, text="⏳ Watching video...")

            remaining = max(int(VIDEO_DURATION - elapsed), 0)
            mins, secs = divmod(remaining, 60)
            st.markdown(f"⏱️ Time left to complete: **{mins:02d}:{secs:02d}**")

            if elapsed >= VIDEO_DURATION and not st.session_state[session_key]["cert_ready"]:
                st.session_state[session_key]["cert_ready"] = True
                st.success("✅ Video completed! Certificate is ready.")
                st.session_state.progress.loc[idx, ["VideoCompleted"]] = True

                # Save completion to Google Sheets
                save_progress_to_gsheet(regno, student["Name"], "Video Completed")

            if st.session_state[session_key]["cert_ready"]:
                cert_file = generate_certificate(
                    student["Name"], regno, student["Dept"], student["Year"], student["Section"]
                )
                with open(cert_file, "rb") as f:
                    st.download_button(
                        "⬇️ Download Certificate",
                        f,
                        file_name=cert_file,
                        help="You can download your certificate once this session."
                    )
                # Save download status to Google Sheets
                st.session_state.progress.loc[idx, ["CertDownloaded"]] = True
                save_progress_to_gsheet(regno, student["Name"], "Certificate Downloaded")

        else:
            st.info("✅ You have already completed this video. Certificate is available for download.")
            cert_file = generate_certificate(
                student["Name"], regno, student["Dept"], student["Year"], student["Section"]
            )
            with open(cert_file, "rb") as f:
                st.download_button(
                    "⬇️ Download Certificate",
                    f,
                    file_name=cert_file,
                    help="Certificate can be downloaded anytime."
                )
