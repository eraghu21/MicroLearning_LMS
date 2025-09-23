import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# Constants
BUFFER_SIZE = 64 * 1024
AES_FILE = "Students_List.aes"
PROGRESS_FILE = "progress.csv"
VIDEO_URL = "https://youtu.be/Tva_sr4BUfk?si=oiKwWi_NGyNjriJu"  # 🔁 Replace this with your YouTube embed link
CERTIFICATE_DIR = "certificates"

# Ensure certificate directory exists
os.makedirs(CERTIFICATE_DIR, exist_ok=True)

# Load student data from AES-encrypted Excel file
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

# Load or initialize progress
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return pd.read_csv(PROGRESS_FILE)
    else:
        return pd.DataFrame(columns=["RegNo", "Name", "Video_Status", "Certificate_Status", "Timestamp"])

# Save progress to CSV
def save_progress(progress_df):
    progress_df.to_csv(PROGRESS_FILE, index=False)

# Generate certificate PDF
def generate_certificate(name, regno):
    file_path = os.path.join(CERTIFICATE_DIR, f"{name}_{regno}.pdf")
    c = canvas.Canvas(file_path, pagesize=A4)
    c.setFont("Helvetica", 20)
    c.drawCentredString(300, 750, "Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawCentredString(300, 700, f"This certifies that {name}")
    c.drawCentredString(300, 675, f"Reg. No: {regno}")
    c.drawCentredString(300, 640, "has successfully completed the session.")
    c.drawCentredString(300, 610, "Date: " + datetime.today().strftime('%Y-%m-%d'))
    c.save()
    return file_path

# Streamlit App
def main():
    st.title("🎓 LMS App – Video Learning & Certificate")

    # Admin Panel
    st.sidebar.header("Admin Panel")
    password = st.sidebar.text_input("🔐 Enter AES Password", type="password")
    uploaded_file = st.sidebar.file_uploader("📤 Upload Encrypted Excel (.aes)", type="aes")

    if uploaded_file and password:
        with open(AES_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())

        students_df = load_student_data(password)
        if students_df is not None:
            st.success("✅ Student data loaded successfully!")

            regno = st.text_input("Enter your Registration Number to login:")

            if regno:
                student = students_df[students_df["RegNo"] == regno]
                if student.empty:
                    st.error("❌ Invalid Registration Number.")
                else:
                    name = student.iloc[0]["Name"]
                    st.success(f"Welcome, {name}!")

                    progress_df = load_progress()
                    existing = progress_df[progress_df["RegNo"] == regno]

                    if not existing.empty and existing.iloc[0]["Video_Status"] == "Completed":
                        st.info("✅ You already watched the video.")
                        cert_path = os.path.join(CERTIFICATE_DIR, f"{name}_{regno}.pdf")
                        if os.path.exists(cert_path):
                            with open(cert_path, "rb") as f:
                                st.download_button("📄 Download Your Certificate", f, file_name=os.path.basename(cert_path))
                        else:
                            cert_path = generate_certificate(name, regno)
                            with open(cert_path, "rb") as f:
                                st.download_button("📄 Download Your Certificate", f, file_name=os.path.basename(cert_path))
                    else:
                        st.video(VIDEO_URL)
                        if st.button("✅ Mark as Watched"):
                            cert_path = generate_certificate(name, regno)
                            new_record = {
                                "RegNo": regno,
                                "Name": name,
                                "Video_Status": "Completed",
                                "Certificate_Status": "Downloaded",
                                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            progress_df = progress_df[progress_df["RegNo"] != regno]  # Remove duplicates
                            progress_df = pd.concat([progress_df, pd.DataFrame([new_record])], ignore_index=True)
                            save_progress(progress_df)
                            with open(cert_path, "rb") as f:
                                st.download_button("📄 Download Your Certificate", f, file_name=os.path.basename(cert_path))

if __name__ == "__main__":
    main()
