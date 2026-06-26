import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.database import StudentProfile, AcademicMarks
from src.ml_models import predict_student_risk
from src.analytics import predict_exam_pass_probability

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(BASE_DIR, "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def generate_student_pdf_report(db: Session, student_id: int) -> str:
    """
    Generates a professional, print-ready PDF progress report for a student.
    Returns the absolute path of the generated PDF file.
    """
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student:
        raise ValueError(f"Student with ID {student_id} not found.")
        
    student_name = student.user.name
    roll_num = student.roll_number
    section = student.class_section
    attendance = student.attendance_pct
    
    # Calculate performance metrics
    marks = student.marks
    avg_internal = sum(m.internal_marks for m in marks) / len(marks) if marks else 0.0
    avg_assign = sum(m.assignment_scores for m in marks) / len(marks) if marks else 0.0
    avg_exam = sum(m.exam_marks for m in marks if m.exam_marks is not None) / len(marks) if marks else 0.0
    
    # Run predictions
    # Calculate averages/aggregates for the ML model
    assignments = student.assignments
    sub_rate = sum(1 for a in assignments if a.status in ["Submitted", "Graded"]) / len(assignments) if assignments else 1.0
    remarks = student.remarks
    avg_sentiment = sum(r.sentiment_score for r in remarks) / len(remarks) if remarks else 0.0
    
    ml_data = {
        "attendance_pct": attendance,
        "internal_marks_avg": avg_internal,
        "assignment_score_avg": avg_assign,
        "exam_marks_avg": avg_exam,
        "assignment_completion_rate": sub_rate,
        "sentiment_score_avg": avg_sentiment
    }
    
    prediction = predict_student_risk(ml_data)
    risk_label = prediction["risk_label"]
    risk_score = prediction["risk_score"]
    
    pass_prob = predict_exam_pass_probability(attendance, avg_internal, sub_rate)
    
    # Configure PDF Output Path
    pdf_filename = f"report_{roll_num}_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    
    # Document Setup
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    bold_body_style = ParagraphStyle(
        'BoldReportBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    alert_box_style = ParagraphStyle(
        'AlertBoxText',
        parent=body_style,
        fontSize=11,
        leading=15,
        textColor=colors.white
    )
    
    # Header Section
    story.append(Paragraph("STUDENT PERFORMANCE MONITORING CELL", ParagraphStyle('Sub', fontSize=9, leading=11, textColor=colors.HexColor('#64748B'), fontName='Helvetica-Bold')))
    story.append(Paragraph("Comprehensive Academic Evaluation Report", title_style))
    story.append(Spacer(1, 10))
    
    # Metadata Table
    meta_data = [
        [Paragraph("<b>Student Name:</b>", body_style), Paragraph(student_name, body_style), Paragraph("<b>Roll Number:</b>", body_style), Paragraph(roll_num, body_style)],
        [Paragraph("<b>Class / Section:</b>", body_style), Paragraph(section, body_style), Paragraph("<b>Report Date:</b>", body_style), Paragraph(datetime.now().strftime("%B %d, %Y"), body_style)],
        [Paragraph("<b>Overall Attendance:</b>", body_style), Paragraph(f"{attendance:.1f}%", body_style), Paragraph("<b>Final Pass Probability:</b>", body_style), Paragraph(f"{pass_prob*100:.1f}%", body_style)]
    ]
    
    meta_table = Table(meta_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    
    story.append(meta_table)
    story.append(Spacer(1, 20))
    
    # Risk Profile Alert Box
    risk_colors = {
        "High": colors.HexColor("#EF4444"), # Red
        "Medium": colors.HexColor("#F59E0B"), # Amber
        "Low": colors.HexColor("#10B981") # Green
    }
    
    risk_color = risk_colors.get(risk_label, colors.HexColor("#3B82F6"))
    
    alert_content = [
        [Paragraph(f"<b>AI PREDICTIVE RISK LEVEL: {risk_label.upper()} ({risk_score:.1f}/100)</b>", alert_box_style)],
        [Paragraph(f"This student has been classified as <b>{risk_label} Risk</b> based on historical models analyzing attendance patterns, assessment scores, and classroom sentiment.", alert_box_style)]
    ]
    alert_table = Table(alert_content, colWidths=[7.0*inch])
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), risk_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(alert_table)
    story.append(Spacer(1, 20))
    
    # Academic Grades Table
    story.append(Paragraph("Subject-wise Performance Summary", section_style))
    
    # Table headers
    headers = [
        Paragraph("<b>Subject</b>", bold_body_style),
        Paragraph("<b>Internals (30)</b>", bold_body_style),
        Paragraph("<b>Assignments (20)</b>", bold_body_style),
        Paragraph("<b>Exams (50)</b>", bold_body_style),
        Paragraph("<b>Total (100)</b>", bold_body_style),
        Paragraph("<b>Status</b>", bold_body_style)
    ]
    
    grades_table_data = [headers]
    
    for m in student.marks:
        total = m.internal_marks + m.assignment_scores + (m.exam_marks or 0)
        status_text = "Pass" if total >= 40 else "Fail"
        status_color = "#10B981" if status_text == "Pass" else "#EF4444"
        
        grades_table_data.append([
            Paragraph(m.subject, body_style),
            Paragraph(f"{m.internal_marks:.1f}", body_style),
            Paragraph(f"{m.assignment_scores:.1f}", body_style),
            Paragraph(f"{m.exam_marks:.1f}" if m.exam_marks is not None else "N/A", body_style),
            Paragraph(f"<b>{total:.1f}</b>", body_style),
            Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", body_style)
        ])
        
    grades_table = Table(grades_table_data, colWidths=[2.0*inch, 1.0*inch, 1.1*inch, 0.9*inch, 1.0*inch, 1.0*inch])
    grades_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(grades_table)
    story.append(Spacer(1, 20))
    
    # Behavioral Feedback & Remarks
    story.append(Paragraph("Faculty Comments & Remarks Sentiment", section_style))
    if student.remarks:
        remarks_data = []
        for rem in student.remarks:
            sentiment_text = "Positive" if rem.sentiment_score > 0.2 else ("Negative" if rem.sentiment_score < -0.2 else "Neutral")
            remarks_data.append([
                Paragraph(f"<b>{rem.faculty.name}:</b>", bold_body_style),
                Paragraph(f"\"{rem.remark_text}\" <br/><font color='#64748B'>[Sentiment: {sentiment_text}]</font>", body_style)
            ])
            
        remarks_table = Table(remarks_data, colWidths=[2.0*inch, 5.0*inch])
        remarks_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(remarks_table)
    else:
        story.append(Paragraph("No faculty comments recorded for this term.", body_style))
        
    story.append(Spacer(1, 20))
    
    # Recommendations & Action Plans
    story.append(Paragraph("Academic Action Plan & Recommendations", section_style))
    
    rec_text = ""
    if risk_label == "High":
        rec_text = """
        • <b>Mandatory Remedial Classes:</b> The student is required to attend daily extra-help sessions for weak subjects.<br/><br/>
        • <b>Parent-Teacher Conference:</b> We recommend the parents schedule an immediate review meeting with the coordinator.<br/><br/>
        • <b>Attendance Correction:</b> Immediate regular attendance is needed. Missing class drops exam clearance probability.<br/><br/>
        • <b>Assignment Backlog Clearance:</b> Complete all pending assignments within 7 days to recover partial credit.
        """
    elif risk_label == "Medium":
        rec_text = """
        • <b>Weekly Review Sessions:</b> Dedicate 2 hours of self-study specifically for subjects with grades below 70%.<br/><br/>
        • <b>Assignment Timeline:</b> Ensure assignments are submitted on time. Tracker indicates late submission tendencies.<br/><br/>
        • <b>Attendance Monitoring:</b> Keep class attendance above 75% to avoid eligibility restrictions.
        """
    else:
        rec_text = """
        • <b>Consistent Schedule:</b> Continue following the current study regime.<br/><br/>
        • <b>Enrichment Projects:</b> Recommend participating in peer mentoring or exploring undergraduate research clubs.<br/><br/>
        • <b>Advanced Electives:</b> Take online honors courses or advanced certification papers.
        """
        
    story.append(Paragraph(rec_text, body_style))
    
    # Build Document
    doc.build(story)
    
    print(f"Generated PDF progress report for student ID {student_id} at: {pdf_path}")
    return pdf_path

if __name__ == "__main__":
    from src.database import SessionLocal, seed_database
    seed_database()
    db = SessionLocal()
    generate_student_pdf_report(db, 1)
