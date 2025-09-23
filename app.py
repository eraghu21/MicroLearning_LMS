import streamlit as st
import pandas as pd
import pyAesCrypt
import os
import io
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# === Configuration ===
BUFFER_SIZE = 64 * 1024
AES_FILE = "Students_List.aes"
PROGRESS_FILE = "progress.csv"
CERT_DIR = "certificates"
VIDEO_URL = "https://www.youtube.com/embed/YOUR_VIDEO_ID"  # Replace with your actual video link

# === Ensure certificate directory exists ===
os.makedirs(CERT_DIR, exist_ok=True)

# === Decrypt and Load Student Data ===
@st.cache_data
def load_student_data(password):
    try:
        with open(AES_FILE, "rb") as f:
            decrypted = io.BytesIO()
            pyAesCrypt.decryptStream(f, decrypted, password, BUFFER_SIZE, len(f.read()))
            decrypted.seek(0)
            df = pd.read_excel(decrypted)
            return df
    except Exception as e:
        st.error("❌ Failed to decrypt file. Check password or file format.")
        return None

# === Load Progress File ===
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return pd.read_csv(PROGRESS_FILE)
    else:
        return pd.DataFrame(columns=["RegNo", "Name", "Video_Status", "Certificate_Status", "Timestamp"])

# === Save Progress ===
def save_progress(df):
    df.to_csv(PROGRESS_FILE, index=False)

# === Generate Certificate PDF ===
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
    st.title("🎓 LMS App – Video Learning with Certificate")
    st.sidebar.header("🔐 Admin Panel")
    
    password = st.sidebar.text_input("Enter AES Password", type="password")
    uploaded_file = st.sidebar.file_uploader("Upload Encrypted Excel (.aes)", type="aes")

    if uploaded_file and password:
        with open(AES_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())

        student_df = load_student_data(password)

        if student_df is not None:
            st.success("✅ Student data loaded successfully!")

            regno = st.text_input("Enter your Registration Number to login:")

            if regno:
                student = student_df[student_df["RegNo"] == regno]

                if student.empty:
                    st.error("❌ Invalid Registration Number.")
                    return

                name = student.iloc[0]["Name"]
                st.success(f"Welcome, {name}!")

                # Load and check progress
                progress_df = load_progress()
                record = progress_df[progress_df["RegNo"] == regno]

                if not record.empty and record.iloc[0]["Video_Status"] == "Completed":
                    st.info("✅ You already completed the video. Certificate is available.")

                    cert_file = os.path.join(CERT_DIR, f"{name}_{regno}.pdf")
                    if not os.path.exists(cert_file):
                        cert_file = generate_certificate(name, regno)

                    with open(cert_file, "rb") as f:
                        st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))
                else:
                    # Show video
                    st.video(VIDEO_URL)
                    if st.button("✅ Mark as Watched"):
                        cert_file = generate_certificate(name, regno)

                        # Update or add progress
                        progress_df = progress_df[progress_df["RegNo"] != regno]
                        new_record = {
                            "RegNo": regno,
                            "Name": name,
                            "Video_Status": "Completed",
                            "Certificate_Status": "Downloaded",
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        progress_df = pd.concat([progress_df, pd.DataFrame([new_record])], ignore_index=True)
                        save_progress(progress_df)

                        with open(cert_file, "rb") as f:
                            st.success("🎉 Congratulations! Certificate ready.")
                            st.download_button("📄 Download Certificate", f, file_name=os.path.basename(cert_file))

if __name__ == "__main__":
    main()
