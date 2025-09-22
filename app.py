import streamlit as st
import pandas as pd
import time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ---------------------------
# Load student list from Excel
# ---------------------------
@st.cache_data
def load_students_list():
    return pd.read_excel("students.xlsx")

# ---------------------------
# Generate PDF certificate
# ---------------------------
def generate_certificate(name, regno, dept, year, section, email):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Title
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 100, "Certificate of Participation")

    # Student details
    c.setFont("Helvetica", 14)
    text_y = height - 180
    line_height = 25

    details = [
        f"Name       : {name}",
        f"Reg No     : {regno}",
        f"Dept       : {dept}",
        f"Year       : {year}",
        f"Section    : {section}",
        f"Email      : {email}",
    ]

    for detail in details:
        c.drawCentredString(width / 2, text_y, detail)
        text_y -= line_height

    # Footer
    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(width / 2, 100, "Issued by Microlearning LMS")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ---------------------------
# Streamlit App
# ---------------------------
st.title("🎓 Certificate Generator")

students_df = load_students_list()
st.dataframe(students_df)

regno_input = st.text_input("Enter your Register Number:")

if regno_input:
    student = students_df[students_df["RegNo"] == regno_input]

    if not student.empty:
        student = student.iloc[0]

        name = student.get("Name", "N/A")
        regno = student.get("RegNo", "N/A")
        dept = student.get("Dept", "N/A")
        year = student.get("Year", "N/A")
        section = student.get("Section", "N/A")
        email = student.get("Email", "N/A")

        st.success(f"✅ Student found: {name} ({regno})")

        # Countdown before enabling download
        countdown_time = 5
        countdown_placeholder = st.empty()

        for i in range(countdown_time, 0, -1):
            countdown_placeholder.warning(f"Please wait {i} seconds before downloading...")
            time.sleep(1)

        countdown_placeholder.success("You can now download your certificate 🎉")

        pdf_buffer = generate_certificate(name, regno, dept, year, section, email)

        st.download_button(
            label="📥 Download Certificate (PDF)",
            data=pdf_buffer,
            file_name=f"certificate_{regno}.pdf",
            mime="application/pdf",
        )
    else:
        st.error("❌ No student found with that Register Number.")
