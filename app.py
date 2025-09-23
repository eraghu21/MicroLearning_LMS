import streamlit as st
import pandas as pd
import pyAesCrypt
import io
import requests
from datetime import datetime
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# Constants
BUFFER_SIZE = 64 * 1024
CERT_DIR = "certificates"
VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your actual video

# GitHub secrets
GITHUB_TOKEN = st.secrets["github"]["token"]
REPO = st.secrets["github"]["repo"]
AES_FILENAME = st.secrets["github"]["aes_filename"]
PROGRESS_FILENAME = st.secrets["github"]["progress_filename"]

# Create cert directory
os.makedirs(CERT_DIR, exist_ok=True)

# === GitHub File Fetcher ===
def download_file_from_github(filename):
    url = f"https://raw.githubusercontent.com/{REPO}/main/{filename}"
    response = requests.get(url)
    if response.status_code == 200:
        return io.BytesIO(response.content)
    else:
        st.error(f"❌ Failed to fetch `{filename}` from GitHub.")
        return None

# === Decrypt AES File ===
def decrypt_excel(aes_file, password):
    try:
        decrypted = io.BytesIO()
        aes_file.seek(0, os.SEEK_END)
        file_len = aes_file.tell()
        aes_file.seek(0)
        pyAesCrypt.decryptStream(aes_file, decrypted, password, BUFFER_SIZE, file_len)
        decrypted.seek(0)
        df = pd.read_excel(decrypted)
        return df
    except Exception as e:
        st.error("❌ AES decryption failed. Invalid password or file.")
        return None

# === Load Progress from GitHub ===
def load_progress_from_github():
    url = f"https://raw.githubusercontent.com/{REPO}/main/{PROGRESS_FILENAME}"
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_csv(io.BytesIO(response.content))
    else:
        st.warning("⚠️ Progress file not found. Initializing empty progress.")
        return pd.DataFrame(columns=["RegNo", "Name", "Video_Status", "Certificate_Status", "Timestamp"])

# === Upload Progress to GitHub ===
def upload_progress_to_github(df):
    csv_data = df.to_csv(index=False).encode()
    b64_data = base64.b64encode(csv_data).decode()
    url = f"https://api.github.com/repos/{REPO}/contents/{PROGRESS_FILENAME}"

    # Check if file exists (GET SHA)
    get_resp = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if get_resp.status_code == 200:
        sha = get_resp.json()["sha"]
    else:
        sha = None

    # Commit
    commit_message = f"Update progress - {datetime.now().isoformat()}"
    payload = {
        "message": commit_message,
        "content": b64_data,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(url, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if put_resp.status_code in [200, 201]:
        st.success("✅ Progress updated on GitHub.")
    else:
        st.error("❌ Failed to update progress to GitHub.")

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
    st.title("🎓 LMS App – GitHub Integration")

    # Sidebar
    st.sidebar.header("🔐 Admin Access")
    password = st.sidebar.text_input("Enter AES Password", type="password")

    if password:
        aes_file = download_file_from_github(AES_FILENAME)
        if aes_file:
            student_df = decrypt_excel(aes_file, password)
            if student_df is not None:
                st.success("✅ Student list loaded.")

                regno = st.text_input("Enter your Registration Number to login:")
                if regno:
                    student = student_df[student_df["RegNo"] == regno]
                    if student.empty:
                        st.error("❌ Invalid Reg. No")
                        return
                    name = student.iloc[0]["Name"]
                    st.success(f"Welcome {name}!")

                    # Load progress
                    progress_df = load_progress_from_github()
                    record = progress_df[progress_df["RegNo"] == regno]

                    if not record.empty and record.iloc[0]["Video_Status"] == "Completed":
                        st.info("✅ You already completed the video. Certificate available.")
                        cert_file = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")
                        if not os.path.exists(cert_file):
                            cert_file = generate_certificate(name, regno)
                        with open(cert_file, "rb") as f:
                            st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))
                    else:
                        st.video(VIDEO_URL)
                        if st.button("✅ Mark as Watched"):
                            cert_file = generate_certificate(name, regno)
                            progress_df = progress_df[progress_df["RegNo"] != regno]
                            new_row = {
                                "RegNo": regno,
                                "Name": name,
                                "Video_Status": "Completed",
                                "Certificate_Status": "Downloaded",
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            progress_df = pd.concat([progress_df, pd.DataFrame([new_row])], ignore_index=True)
                            upload_progress_to_github(progress_df)
                            with open(cert_file, "rb") as f:
                                st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))

if __name__ == "__main__":
    main()
