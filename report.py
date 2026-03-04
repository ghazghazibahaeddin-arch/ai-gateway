from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime

def generate_pdf_report(stats: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.hexColor("#1e3a8a")
    )
    elements.append(Paragraph("AI Gateway Security & Savings Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", styles['Heading2']))
    summary_text = f"""
    This report summarizes the performance and security impact of the AI Gateway. 
    By intercepting and redacting sensitive information (PII) before it reached external LLM providers, 
    the organization maintained compliance and reduced privacy risks.
    """
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 20))

    # Key Metrics Table
    elements.append(Paragraph("Key Performance Indicators", styles['Heading3']))
    data = [
        ["Metric", "Value"],
        ["Total Requests", str(stats.get("total_requests", 0))],
        ["Total Tokens Processed", f"{stats.get('total_tokens', 0):,}"],
        ["Total Estimated Cost", f"${stats.get('total_cost', 0):.4f}"],
        ["PII Detections Blocked", str(stats.get("total_pii_detections", 0))],
        ["Flagged Privacy Risks", str(stats.get("requests_with_pii", 0))],
        ["Avg. Request Latency", f"{stats.get('avg_latency_ms', 0)}ms"],
    ]
    
    t = Table(data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#1e3a8a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 30))

    # PII Breakdown
    if stats.get("pii_by_type"):
        elements.append(Paragraph("Privacy Risks Blocked by Type", styles['Heading3']))
        pii_data = [["Entity Type", "Occurrences"]]
        for item in stats["pii_by_type"]:
            pii_data.append([item["type"], str(item["count"])])
        
        pt = Table(pii_data, colWidths=[200, 200])
        pt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#ef4444")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(pt)
        elements.append(Spacer(1, 20))

    # Model Usage
    if stats.get("by_model"):
        elements.append(Paragraph("Model Usage Distribution", styles['Heading3']))
        model_data = [["Model", "Requests", "Tokens", "Cost"]]
        for m in stats["by_model"]:
            model_data.append([m["model"], str(m["count"]), f"{m['tokens']:,}", f"${m['cost']:.4f}"])
        
        mt = Table(model_data, colWidths=[150, 80, 80, 80])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.hexColor("#3b82f6")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(mt)

    # Footer
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("This report is confidential and generated automatically by the AI Gateway.", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
