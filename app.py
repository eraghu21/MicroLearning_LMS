import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from github import Github  # ⬅ NEW

# === Constants ===
BUFFER_SIZE = 64 * 1024
AES_FILE = "Students_List.aes"
PROGRESS_FILE = "progress.csv"
VIDEO_URL = "https://www.youtube.com/embed/Tva_sr4BUfk"  # 🔁 Replace with your embed link
CERTIFICATE_DIR = "certificates"

# Ensure certificate directory exists
os.makedirs(CERTIFICATE_DIR, exist_ok=True)

# === Load student data from AES-encrypted Excel file ===
@st.cache_data
def load_student_data(password):
    try:
        with open(AES_FILE, "rb") as fIn:
            decrypted = io.BytesIO()
            pyAesCrypt.decryptStream(fIn, decrypted, password, BUFFER_SIZE, len(fIn.read()))
            decrypted.seek(0)
            df = pd.read_excel(decrypted)
            return df
    except Exception:
        st.error("❌ Error decrypting the file. Check password or file format.")
        return None

# === Load / Save Progress ===
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return pd.read_csv(PROGRESS_FILE)
    else:
        return pd.DataFrame(columns=["RegNo", "Name", "Dept", "Year", "Section", "Video_Status", "Certificate_Status", "Timestamp"])

def save_progress(progress_df):
    progress_df.to_csv(PROGRESS_FILE, index=False)

# === Upload progress.csv to GitHub ===
def upload_to_github(file_path, repo_name, branch="main"):
    try:
        token = st.secrets["github"]["token"]   # store in Streamlit Secrets
        g = Github(token)
        repo = g.get_repo(repo_name)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(contents.path, "Update progress.csv", content, contents.sha, branch=branch)
        except Exception:
            repo.create_file(file_path, "Add progress.csv", content, branch=branch)

        st.sidebar.success("✅ Progress saved to GitHub successfully.")
    except Exception as e:
        st.sidebar.error(f"⚠️ GitHub upload failed: {e}")

# === Generate Certificate ===
def generate_certificate(name, regno, dept, year, section):
    file_path = os.path.join(CERTIFICATE_DIR, f"{name}_{regno}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 780, "Certificate of Completion")

    # Main Text
    c.setFont("Helvetica", 16)
    c.drawCentredString(300, 740, f"This is to certify that")
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(300, 710, f"{name} (Reg.No: {regno})")

    # Additional details
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 670, f"Department: {dept}")
    c.drawCentredString(300, 650, f"Year: {year}   |   Section: {section}")

    # Completion text
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 610, "has successfully completed the training session.")

    # Date & Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.drawCentredString(300, 580, f"Issued on: {timestamp}")

    c.save()
    return file_path

# === Main App ===
def main():
    st.title("🎓 LMS App – Video Learning & Certificate")

    # Admin Panel (Sidebar)
    st.sidebar.header("Admin Panel")
    password = st.sidebar.text_input("🔐 Enter AES Password", type="password")
    uploaded_file = st.sidebar.file_uploader("📤 Upload Encrypted Excel (.aes)", type="aes")
    repo_name = st.sidebar.text_input("📂 GitHub Repo (e.g., username/repo)")
    branch = st.sidebar.text_input("🌿 Branch", value="main")

    if uploaded_file and password:
        # Save uploaded AES file
        with open(AES_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Load student list
        students_df = load_student_data(password)
        if students_df is not None:
            st.success("✅ Student data loaded successfully!")

            # Student Login
            regno = st.text_input("Enter your Registration Number to login:")

            if regno:
                student = students_df[students_df["RegNo"] == regno]
                if student.empty:
                    st.error("❌ Invalid Registration Number.")
                else:
                    name = student.iloc[0]["Name"]
                    dept = student.iloc[0]["Dept"]
                    year = student.iloc[0]["Year"]
                    section = student.iloc[0]["Section"]

                    st.success(f"Welcome, {name} ({dept}, Year {year}, Section {section})")

                    # Load progress
                    progress_df = load_progress()
                    existing = progress_df[progress_df["RegNo"] == regno]

                    # Already watched → allow certificate
                    if not existing.empty and existing.iloc[0]["Video_Status"] == "Completed":
                        st.info("✅ You already watched the video. You can download your certificate.")
                        cert_path = os.path.join(CERTIFICATE_DIR, f"{name}_{regno}.pdf")
                        if not os.path.exists(cert_path):
                            cert_path = generate_certificate(name, regno, dept, year, section)
                        with open(cert_path, "rb") as f:
                            st.download_button("📄 Download Your Certificate", f, file_name=os.path.basename(cert_path))

                    # New / Not completed → show video
                    else:
                        st.video(VIDEO_URL)
                        if st.button("✅ Mark as Watched"):
                            cert_path = generate_certificate(name, regno, dept, year, section)
                            new_record = {
                                "RegNo": regno,
                                "Name": name,
                                "Dept": dept,
                                "Year": year,
                                "Section": section,
                                "Video_Status": "Completed",
                                "Certificate_Status": "Downloaded",
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            # Remove old record if exists
                            progress_df = progress_df[progress_df["RegNo"] != regno]
                            progress_df = pd.concat([progress_df, pd.DataFrame([new_record])], ignore_index=True)
                            save_progress(progress_df)

                            # Upload to GitHub
                            if repo_name:
                                upload_to_github(PROGRESS_FILE, repo_name, branch)

                            with open(cert_path, "rb") as f:
                                st.download_button("📄 Download Your Certificate", f, file_name=os.path.basename(cert_path))

if __name__ == "__main__":
    main()
