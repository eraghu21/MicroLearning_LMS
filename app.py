import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import os
from datetime import datetime
import base64
import requests
import streamlit.components.v1 as components
from fpdf import FPDF

# ====================== CONFIG ======================
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
os.makedirs(CERT_DIR, exist_ok=True)

VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your video ID
VIDEO_DURATION = 15  # seconds

AES_FILE = st.secrets["aes"]["file"]
AES_PASSWORD = st.secrets["aes"]["password"]

GITHUB_TOKEN = st.secrets["github"]["token"]
REPO = st.secrets["github"]["repo"]
PROGRESS_FILE = st.secrets["github"]["progress_file"]

ADMIN_PASSWORD = st.secrets["admin"]["password"]

# ====================== CERTIFICATE BACKGROUND ======================
certificate_base64 = """
iVBORw0KGgoAAAANSUhEUgAAAyAAAABkCAYAAABogL1UAAAACXBIWXMAAAsTAAALEwEAmpwY
AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAACBjSFJNAAB6JgAAgIQA
APoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAABf0lEQVR42u3RAQEAAAgDoJvc6FNgAAAI
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAPwX4QAB9g
kSxQAAAABJRU5ErkJggg==
"""

def save_certificate_background():
    clean_b64 = certificate_base64.replace("\n", "").replace(" ", "")
    img_bytes = base64.b64decode(clean_b64)
    file_path = os.path.join(CERT_DIR, "certificate_bg.jpeg")
    os.makedirs(CERT_DIR, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(img_bytes)
    return file_path

# Define global variable
BG_IMAGE_PATH = save_certificate_background()

# ====================== LOAD STUDENTS ======================
@st.cache_data
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
        st.error(f"❌ Failed to load student file: {e}")
        return None

# ====================== GITHUB PROGRESS ======================
def load_progress_from_github():
    url = f"https://raw.githubusercontent.com/{REPO}/main/{PROGRESS_FILE}"
    response = requests.get(url)
    if response.status_code == 200:
        df = pd.read_csv(io.BytesIO(response.content), dtype={"RegNo": str})
        df["RegNo"] = df["RegNo"].astype(str).str.strip()
        return df
    else:
        return pd.DataFrame(columns=["RegNo","Name","Video_Status","Certificate_Status","Timestamp"])

def upload_progress_to_github(df):
    csv_data = df.to_csv(index=False).encode()
    b64_data = base64.b64encode(csv_data).decode()
    url = f"https://api.github.com/repos/{REPO}/contents/{PROGRESS_FILE}"

    get_resp = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = get_resp.json()["sha"] if get_resp.status_code == 200 else None

    payload = {
        "message": f"Update progress - {datetime.now().isoformat()}",
        "content": b64_data,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return put_resp.status_code in [200, 201]

# ====================== GENERATE CERTIFICATE ======================
def generate_certificate(name, regno):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_path = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")
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
    return file_path

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

    # Admin sidebar
    st.sidebar.header("🔐 Admin Access")
    admin_pass = st.sidebar.text_input("Enter admin password", type="password")
    if admin_pass == ADMIN_PASSWORD:
        st.sidebar.success("✅ Admin access granted")
        df_progress = load_progress_from_github()
        st.sidebar.subheader("📊 Student Progress")
        st.sidebar.dataframe(df_progress)

    # Load students
    student_df = load_students()
    if student_df is None:
        return

    regno = st.text_input("Enter your Registration Number:").strip()
    if not regno:
        return

    student = student_df[student_df["RegNo"] == regno]
    if student.empty:
        st.error("❌ Invalid Registration Number")
        return

    name = student.iloc[0]["Name"]
    st.success(f"Welcome {name} (RegNo: {regno})")

    cert_file = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")

    # Load progress
    df_progress = load_progress_from_github()
    df_progress["RegNo"] = df_progress["RegNo"].astype(str).str.strip()
    record = df_progress[df_progress["RegNo"] == regno]

    if not record.empty:
        st.info("✅ You have already watched the video. You can download your certificate below.")
        if not os.path.exists(cert_file):
            cert_file = generate_certificate(name, regno)
        with open(cert_file, "rb") as f:
            st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file), key=f"download_{regno}")
    else:
        if st.session_state.get("current_student") != regno:
            st.session_state.video_finished = False
            st.session_state.current_student = regno
   
        show_video_with_timer(VIDEO_URL, VIDEO_DURATION)

        if not st.session_state.get("video_finished", False):
            if st.button("✅ I have watched the video"):
                st.session_state.video_finished = True

        if st.session_state.get("video_finished", False):
            if not os.path.exists(cert_file):
                cert_file = generate_certificate(name, regno)
            # Update GitHub
            df_progress = df_progress[df_progress["RegNo"] != regno]
            new_row = {
                "RegNo": regno,
                "Name": name,
                "Video_Status": "Completed",
                "Certificate_Status": "Downloaded",
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            df_progress = pd.concat([df_progress, pd.DataFrame([new_row])], ignore_index=True)
            upload_success = upload_progress_to_github(df_progress)
            if upload_success:
                st.success("✅ Progress saved!")
            else:
                st.error("❌ Failed to save progress!")

            with open(cert_file, "rb") as f:
                st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file), key=f"download_{regno}")

if __name__ == "__main__":
    main()
