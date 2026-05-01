import base64
import io
from datetime import datetime
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from PIL import Image as PILImage

app = FastAPI(title="TPS PDF Export Service")

# 1. Enable CORS for cross-origin requests from the Flask frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the Flask URL (e.g., http://localhost:5000)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Pydantic Models for Input Validation
class ReportMeta(BaseModel):
    title: str
    company: str
    department: str
    author: str
    period: str

class TableData(BaseModel):
    years: List[int]
    pensiun: List[int]
    regenerasi: List[int]
    jumlah_awal: List[int]
    jumlah_akhir: List[int]

class PDFExportRequest(BaseModel):
    chart_image: str  # Base64 string
    report_meta: ReportMeta
    table_data: TableData

@app.post("/api/export-pdf/from-image")
async def export_pdf(request: PDFExportRequest):
    try:
        # Create a buffer for the PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=1.5*cm, 
            leftMargin=1.5*cm, 
            topMargin=1.5*cm, 
            bottomMargin=1.5*cm
        )
        elements = []
        styles = getSampleStyleSheet()

        # --- A. Header Section ---
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#185FA5'),
            spaceAfter=2
        )
        sub_header_style = ParagraphStyle(
            'SubHeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            spaceAfter=12
        )
        
        elements.append(Paragraph(request.report_meta.company.upper(), header_style))
        elements.append(Paragraph(request.report_meta.department, sub_header_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#185FA5'), spaceAfter=2))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=20))

        # --- B. Title Section ---
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1, # Center
            spaceAfter=5
        )
        elements.append(Paragraph(request.report_meta.title, title_style))
        elements.append(Paragraph(f"Periode: {request.report_meta.period}", styles['Normal']))
        elements.append(Paragraph(f"Tanggal Cetak: {datetime.now().strftime('%d %B %Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 1*cm))

        # --- C. Chart Image Section ---
        # Decode base64 image
        header, encoded = request.chart_image.split(",", 1)
        image_data = base64.b64decode(encoded)
        img_buffer = io.BytesIO(image_data)
        
        # Use PIL to verify and get dimensions
        pil_img = PILImage.open(img_buffer)
        width, height = pil_img.size
        aspect = height / float(width)
        
        target_width = 16*cm
        target_height = target_width * aspect
        
        chart_img = Image(img_buffer, width=target_width, height=target_height)
        elements.append(chart_img)
        elements.append(Spacer(1, 1*cm))

        # --- D. Table Section ---
        elements.append(Paragraph("Ringkasan Data Proyeksi", styles['Heading3']))
        elements.append(Spacer(1, 0.5*cm))

        # Prepare Table Data
        header = ["Tahun", "Pensiun", "Regenerasi", "Jml Awal", "Jml Akhir"]
        data = [header]
        
        td = request.table_data
        for i in range(len(td.years)):
            data.append([
                td.years[i],
                td.pensiun[i],
                td.regenerasi[i],
                td.jumlah_awal[i],
                td.jumlah_akhir[i]
            ])
            
        # Add TOTAL Row
        data.append([
            "TOTAL / AVG",
            sum(td.pensiun),
            sum(td.regenerasi),
            "-",
            int(sum(td.jumlah_akhir) / len(td.jumlah_akhir))
        ])

        # Style the table
        table = Table(data, colWidths=[3*cm, 3*cm, 3*cm, 3.5*cm, 3.5*cm])
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#185FA5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#F2F2F2')), # Zebra stripes handled by alternating colors manually if needed, or simple background
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F4FD')), # Total row background
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ])
        
        # Apply zebra stripes
        for i, row in enumerate(data):
            if i > 0 and i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.white)
            elif i > 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F9F9F9'))

        table.setStyle(table_style)
        elements.append(table)

        # --- E. Footer (Manual Page Numbering) ---
        def footer(canvas, doc):
            canvas.saveState()
            footer_text = f"Dicetak oleh: {request.report_meta.author} | Halaman {doc.page}"
            canvas.setFont('Helvetica', 9)
            canvas.drawRightString(A4[0] - 1.5*cm, 1*cm, footer_text)
            canvas.restoreState()

        # Build PDF
        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
        
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
