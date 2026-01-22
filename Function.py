# ==================== ENHANCED AISC 360-16 STEEL DESIGN WEB APP ====================
# Version: 7.0 - Professional UI/UX with Advanced Export Capabilities
# New Features: PDF/Excel Export, Modern UI, Enhanced Visualizations

import streamlit as st

# ==================== PAGE CONFIGURATION - MUST BE FIRST ====================
st.set_page_config(
    page_title="AISC 360-16 Steel Design Professional",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== IMPORTS ====================
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import math
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import io
import base64
from io import BytesIO

# Add these imports at the top with other imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# ==================== PROFESSIONAL PDF GENERATION WITH FIXED FORMATTING ====================
from reportlab.platypus import PageTemplate, Frame, BaseDocTemplate, KeepTogether
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas

from reportlab.platypus import PageTemplate, Frame, BaseDocTemplate, KeepTogether, Flowable
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "Section Comparison",
    "Design Evaluation & Export",
    "Documentation"
])

class EquationBox(Flowable):
    """Custom flowable for equation boxes with proper padding and no overlap"""
    def __init__(self, text, width):
        Flowable.__init__(self)
        self.text = text
        self.width = width
        self.height = 0
        
    def wrap(self, availWidth, availHeight):
        # Calculate required height with padding
        self.width = availWidth
        # Estimate height based on text length (adjust as needed)
        lines = len(self.text) / 80 + 1
        self.height = max(30, lines * 15 + 20)  # Minimum 30pt, with padding
        return (self.width, self.height)
    
    def draw(self):
        # Draw blue background box
        self.canv.setFillColor(rl_colors.HexColor('#E7F3FF'))
        self.canv.setStrokeColor(rl_colors.HexColor('#2196F3'))
        self.canv.setLineWidth(1)
        self.canv.roundRect(0, 0, self.width, self.height, 5, fill=1, stroke=1)
        
        # Draw text with proper padding
        self.canv.setFillColor(rl_colors.HexColor('#1565C0'))
        self.canv.setFont('Courier', 9)
        
        # Word wrap text
        words = self.text.split()
        lines = []
        current_line = []
        current_width = 0
        max_width = self.width - 20  # 10pt padding on each side
        
        for word in words:
            word_width = self.canv.stringWidth(word + ' ', 'Courier', 9)
            if current_width + word_width <= max_width:
                current_line.append(word)
                current_width += word_width
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = word_width
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines
        y_position = self.height - 15
        for line in lines:
            self.canv.drawString(10, y_position, line)
            y_position -= 12


# Optional: AgGrid (only if installed)
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    AGGRID_AVAILABLE = True
except ImportError:
    AGGRID_AVAILABLE = False

# PDF Export Libraries (silent import, warnings shown later)
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Excel Export Libraries (silent import, warnings shown later)
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.chart import BarChart, Reference, LineChart
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.utils import get_column_letter  # ADD THIS LINE
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for page numbers and headers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 9)
        self.setFillColor(rl_colors.grey)
        
        # Header
        self.line(0.75*inch, letter[1] - 0.6*inch, letter[0] - 0.75*inch, letter[1] - 0.6*inch)
        self.setFont("Helvetica-Bold", 10)
        self.setFillColor(rl_colors.HexColor('#667eea'))
        self.drawString(0.75*inch, letter[1] - 0.5*inch, "AISC 360-16 Steel Design - Calculation Report")
        
        # Footer
        self.setFont("Helvetica", 9)
        self.setFillColor(rl_colors.grey)
        self.line(0.75*inch, 0.6*inch, letter[0] - 0.75*inch, 0.6*inch)
        self.drawRightString(letter[0] - 0.75*inch, 0.4*inch, 
                            f"Page {self._pageNumber} of {page_count}")
        self.drawString(0.75*inch, 0.4*inch, 
                       f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def generate_professional_calculation_report(df, df_mat, section, material, analysis_results, design_params, project_info):
    """
    Generate professional engineering calculation report with:
    - Project information header
    - Hand calculation style (detailed step-by-step)
    - Summary tables
    - Graphs/Charts
    - Professional formatting
    """
    if not PDF_AVAILABLE:
        return None
    
    buffer = BytesIO()
    
    # Create document
    doc = BaseDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.6*inch, 
        leftMargin=0.6*inch,
        topMargin=1.2*inch,
        bottomMargin=0.8*inch,
        title="AISC 360-16 Structural Calculation"
    )
    
    # Define frame
    frame = Frame(
        doc.leftMargin, 
        doc.bottomMargin, 
        doc.width, 
        doc.height - 0.2*inch,
        id='normal',
        topPadding=10,
        bottomPadding=10
    )
    template = PageTemplate(id='main', frames=frame, onPage=lambda c, d: None)
    doc.addPageTemplates([template])
    
    story = []
    styles = getSampleStyleSheet()
    
    # ==================== CUSTOM STYLES ====================
    title_style = ParagraphStyle(
        'CalcTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=rl_colors.HexColor('#1a237e'),
        spaceAfter=12,
        spaceBefore=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=22
    )
    
    heading1_style = ParagraphStyle(
        'CalcHeading1',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=rl_colors.white,
        spaceAfter=8,
        spaceBefore=14,
        fontName='Helvetica-Bold',
        backColor=rl_colors.HexColor('#1a237e'),
        borderPadding=8,
        leading=18
    )
    
    heading2_style = ParagraphStyle(
        'CalcHeading2',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=rl_colors.HexColor('#1565c0'),
        spaceAfter=6,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderColor=rl_colors.HexColor('#1565c0'),
        borderPadding=4,
        leading=16
    )
    
    body_style = ParagraphStyle(
        'CalcBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=4,
        spaceBefore=2,
        alignment=TA_LEFT
    )
    
    equation_style = ParagraphStyle(
        'CalcEquation',
        parent=styles['Code'],
        fontSize=10,
        textColor=rl_colors.HexColor('#0d47a1'),
        backColor=rl_colors.HexColor('#e3f2fd'),
        borderWidth=1,
        borderColor=rl_colors.HexColor('#1976d2'),
        borderPadding=10,
        leftIndent=20,
        rightIndent=20,
        spaceAfter=8,
        spaceBefore=6,
        fontName='Courier',
        leading=14,
        alignment=TA_LEFT
    )
    
    result_style = ParagraphStyle(
        'CalcResult',
        parent=styles['Normal'],
        fontSize=11,
        textColor=rl_colors.HexColor('#1b5e20'),
        backColor=rl_colors.HexColor('#e8f5e9'),
        borderWidth=2,
        borderColor=rl_colors.HexColor('#4caf50'),
        borderPadding=10,
        spaceAfter=10,
        spaceBefore=6,
        fontName='Helvetica-Bold',
        leading=16,
        alignment=TA_CENTER
    )
    
    reference_style = ParagraphStyle(
        'CalcReference',
        parent=styles['Normal'],
        fontSize=9,
        textColor=rl_colors.HexColor('#616161'),
        fontName='Helvetica-Oblique',
        leading=12,
        leftIndent=30
    )
    
    # ==================== PROJECT HEADER TABLE ====================
    story.append(Spacer(1, 0.1*inch))
    
    # Project info table (professional engineering header)
    header_data = [
        [Paragraph('<b>STRUCTURAL CALCULATION SHEET</b>', 
                  ParagraphStyle('header', fontSize=14, alignment=TA_CENTER, textColor=rl_colors.white)),
         '', '', ''],
        ['Project:', project_info.get('project_name', 'N/A'), 
         'Project No.:', project_info.get('project_no', 'N/A')],
        ['Subject:', f'Steel Design - {section}', 
         'Date:', project_info.get('date', datetime.now().strftime('%Y-%m-%d'))],
        ['Designer:', project_info.get('designer', 'N/A'), 
         'Checker:', project_info.get('checker', 'N/A')],
        ['Reference:', 'AISC 360-16', 
         'Revision:', project_info.get('revision', '0')],
    ]
    
    header_table = Table(header_data, colWidths=[1.2*inch, 2.8*inch, 1.0*inch, 1.5*inch])
    header_table.setStyle(TableStyle([
        # Title row
        ('SPAN', (0, 0), (-1, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (0, -1), rl_colors.HexColor('#e8eaf6')),
        ('BACKGROUND', (2, 1), (2, -1), rl_colors.HexColor('#e8eaf6')),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#1a237e')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))
    
    # ==================== TABLE OF CONTENTS ====================
    story.append(Paragraph("TABLE OF CONTENTS", heading1_style))
    story.append(Spacer(1, 6))
    
    toc_data = [
        ['1.', 'Design Data & Material Properties', ''],
        ['2.', 'Section Properties', ''],
        ['3.', 'Section Classification (AISC Table B4.1)', ''],
        ['4.', 'Flexural Design (AISC Chapter F2)', ''],
        ['5.', 'Compression Design (AISC Chapter E3)', ''],
        ['6.', 'Design Summary & Conclusion', ''],
    ]
    
    toc_table = Table(toc_data, colWidths=[0.4*inch, 5*inch, 1*inch])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ==================== 1. DESIGN DATA ====================
    story.append(Paragraph("1. DESIGN DATA & MATERIAL PROPERTIES", heading1_style))
    story.append(Spacer(1, 8))
    
    # Get material properties
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    Fu = safe_scalar(df_mat.loc[material, "Tensile Strength (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    story.append(Paragraph("<b>1.1 Material Properties</b>", heading2_style))
    story.append(Paragraph(f"Steel Grade: <b>{material}</b>", body_style))
    story.append(Spacer(1, 4))
    
    mat_table_data = [
        ['Property', 'Symbol', 'Value', 'Unit'],
        ['Yield Strength', 'Fy', f'{Fy:.1f}', 'kgf/cm²'],
        ['Tensile Strength', 'Fu', f'{Fu:.1f}', 'kgf/cm²'],
        ['Modulus of Elasticity', 'E', f'{E:,.0f}', 'kgf/cm²'],
        ['Poisson\'s Ratio', 'ν', '0.30', '-'],
        ['Shear Modulus', 'G', f'{E/(2*1.3):,.0f}', 'kgf/cm²'],
    ]
    
    mat_table = Table(mat_table_data, colWidths=[2.2*inch, 1*inch, 1.5*inch, 1.3*inch])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1565c0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#f5f5f5')])
    ]))
    story.append(mat_table)
    story.append(Spacer(1, 10))
    
    # Design Parameters
    story.append(Paragraph("<b>1.2 Design Parameters (Input)</b>", heading2_style))
    
    design_table_data = [['Parameter', 'Symbol', 'Value', 'Unit']]
    
    if 'Mu' in design_params:
        design_table_data.append(['Required Moment Strength', 'Mu', f"{design_params['Mu']:.2f}", 't·m'])
    if 'Pu' in design_params:
        design_table_data.append(['Required Axial Strength', 'Pu', f"{design_params['Pu']:.2f}", 'tons'])
    if 'Lb' in design_params:
        design_table_data.append(['Unbraced Length', 'Lb', f"{design_params['Lb']:.2f}", 'm'])
    if 'KL' in design_params:
        design_table_data.append(['Effective Length', 'KL', f"{design_params['KL']:.2f}", 'm'])
    if 'Cb' in design_params:
        design_table_data.append(['Moment Gradient Factor', 'Cb', f"{design_params['Cb']:.2f}", '-'])
    
    design_table = Table(design_table_data, colWidths=[2.2*inch, 1*inch, 1.5*inch, 1.3*inch])
    design_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#ff6f00')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
    ]))
    story.append(design_table)
    
    # ==================== 2. SECTION PROPERTIES ====================
    story.append(PageBreak())
    story.append(Paragraph("2. SECTION PROPERTIES", heading1_style))
    story.append(Spacer(1, 8))
    
    story.append(Paragraph(f"<b>Selected Section: {section}</b>", heading2_style))
    story.append(Spacer(1, 4))
    
    # Get all section properties
    d = safe_scalar(df.loc[section, 'd [mm]'])
    bf = safe_scalar(df.loc[section, 'bf [mm]'])
    tf = safe_scalar(df.loc[section, 'tf [mm]'])
    tw = safe_scalar(df.loc[section, 'tw [mm]'])
    r = safe_scalar(df.loc[section, 'r [mm]']) if 'r [mm]' in df.columns else 0
    A = safe_scalar(df.loc[section, 'A [cm2]'])
    Ix = safe_scalar(df.loc[section, 'Ix [cm4]'])
    Iy = safe_scalar(df.loc[section, 'Iy [cm4]'])
    rx = safe_scalar(df.loc[section, 'rx [cm]'])
    ry = safe_scalar(df.loc[section, 'ry [cm]'])
    Sx = safe_scalar(df.loc[section, 'Sx [cm3]'])
    Sy = safe_scalar(df.loc[section, 'Sy [cm3]'])
    Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
    Zy = safe_scalar(df.loc[section, 'Zy [cm3]'])
    J = safe_scalar(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 0
    ho = safe_scalar(df.loc[section, 'ho [mm]']) if 'ho [mm]' in df.columns else (d - tf)
    rts = safe_scalar(df.loc[section, 'rts [cm]']) if 'rts [cm]' in df.columns else ry * 1.2
    
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
    weight = safe_scalar(df.loc[section, weight_col])
    
    # Section properties in two columns
    props_data_1 = [
        ['Geometric Properties', '', ''],
        ['Overall Depth', 'd', f'{d:.0f} mm'],
        ['Flange Width', 'bf', f'{bf:.0f} mm'],
        ['Flange Thickness', 'tf', f'{tf:.1f} mm'],
        ['Web Thickness', 'tw', f'{tw:.1f} mm'],
        ['Fillet Radius', 'r', f'{r:.1f} mm'],
        ['Unit Weight', 'w', f'{weight:.1f} kg/m'],
    ]
    
    props_data_2 = [
        ['Section Properties', '', ''],
        ['Cross-sectional Area', 'A', f'{A:.2f} cm²'],
        ['Moment of Inertia (x)', 'Ix', f'{Ix:,.0f} cm⁴'],
        ['Moment of Inertia (y)', 'Iy', f'{Iy:,.0f} cm⁴'],
        ['Radius of Gyration (x)', 'rx', f'{rx:.2f} cm'],
        ['Radius of Gyration (y)', 'ry', f'{ry:.2f} cm'],
        ['Torsional Constant', 'J', f'{J:.2f} cm⁴'],
    ]
    
    props_data_3 = [
        ['Section Moduli', '', ''],
        ['Elastic Modulus (x)', 'Sx', f'{Sx:,.1f} cm³'],
        ['Elastic Modulus (y)', 'Sy', f'{Sy:,.1f} cm³'],
        ['Plastic Modulus (x)', 'Zx', f'{Zx:,.1f} cm³'],
        ['Plastic Modulus (y)', 'Zy', f'{Zy:,.1f} cm³'],
        ['Distance b/w flanges', 'ho', f'{ho:.1f} mm'],
        ['Effective radius (LTB)', 'rts', f'{rts:.2f} cm'],
    ]
    
    # Create combined table
    def create_props_table(data):
        table = Table(data, colWidths=[2.2*inch, 0.8*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#37474f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('SPAN', (0, 0), (-1, 0)),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#fafafa')])
        ]))
        return table
    
    # Create a combined layout
    combined_data = [[create_props_table(props_data_1), create_props_table(props_data_2)]]
    combined_table = Table(combined_data, colWidths=[3.3*inch, 3.3*inch])
    combined_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(combined_table)
    story.append(Spacer(1, 8))
    story.append(create_props_table(props_data_3))
    
    # Add section diagram
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("<b>Section Cross-Section:</b>", body_style))
    story.append(Spacer(1, 6))
    
    # Generate section diagram
    fig_section = create_detailed_section_diagram(d, bf, tf, tw, section)
    img_buffer_section = BytesIO()
    plt.savefig(img_buffer_section, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig_section)
    img_buffer_section.seek(0)
    
    section_img = Image(img_buffer_section, width=4*inch, height=3*inch)
    story.append(section_img)
    
    # ==================== 3. SECTION CLASSIFICATION ====================
    story.append(PageBreak())
    story.append(Paragraph("3. SECTION CLASSIFICATION (AISC Table B4.1)", heading1_style))
    story.append(Spacer(1, 8))
    
    # Get classifications
    flex_class = classify_section_flexure(df, df_mat, section, material)
    comp_class = classify_section_compression(df, df_mat, section, material)
    
    if flex_class:
        story.append(Paragraph("<b>3.1 Flexural Member Classification (Table B4.1b)</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        # Flange Classification - Hand Calculation Style
        story.append(Paragraph("<b>Flange Classification (Case 10: Flanges of I-shaped sections)</b>", body_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Table B4.1b</i>", reference_style))
        story.append(Spacer(1, 4))
        
        story.append(Paragraph(
            f"<font face='Courier'>λf = bf / (2·tf) = {bf:.1f} / (2 × {tf:.1f}) = <b>{flex_class['flange_lambda']:.2f}</b></font>",
            equation_style
        ))
        
        story.append(Paragraph(
            f"<font face='Courier'>λpf = 0.38·√(E/Fy) = 0.38 × √({E:,.0f}/{Fy:.1f}) = <b>{flex_class['flange_lambda_p']:.2f}</b></font>",
            equation_style
        ))
        
        story.append(Paragraph(
            f"<font face='Courier'>λrf = 1.0·√(E/Fy) = 1.0 × √({E:,.0f}/{Fy:.1f}) = <b>{flex_class['flange_lambda_r']:.2f}</b></font>",
            equation_style
        ))
        
        # Classification check
        if flex_class['flange_lambda'] <= flex_class['flange_lambda_p']:
            check_text = f"λf = {flex_class['flange_lambda']:.2f} ≤ λpf = {flex_class['flange_lambda_p']:.2f}"
            result_text = "FLANGE: COMPACT ✓"
            result_color = '#4caf50'
        elif flex_class['flange_lambda'] <= flex_class['flange_lambda_r']:
            check_text = f"λpf = {flex_class['flange_lambda_p']:.2f} < λf = {flex_class['flange_lambda']:.2f} ≤ λrf = {flex_class['flange_lambda_r']:.2f}"
            result_text = "FLANGE: NON-COMPACT"
            result_color = '#ff9800'
        else:
            check_text = f"λf = {flex_class['flange_lambda']:.2f} > λrf = {flex_class['flange_lambda_r']:.2f}"
            result_text = "FLANGE: SLENDER ✗"
            result_color = '#f44336'
        
        story.append(Paragraph(f"<font face='Courier'>Check: {check_text}</font>", equation_style))
        story.append(Paragraph(
            f"<b>{result_text}</b>",
            ParagraphStyle('FlgResult', parent=result_style, textColor=rl_colors.HexColor(result_color))
        ))
        story.append(Spacer(1, 10))
        
        # Web Classification - Hand Calculation Style
        story.append(Paragraph("<b>Web Classification (Case 15: Webs in flexural compression)</b>", body_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Table B4.1b</i>", reference_style))
        story.append(Spacer(1, 4))
        
        h_web = ho if 'ho [mm]' in df.columns else (d - 2*tf)
        story.append(Paragraph(
            f"<font face='Courier'>λw = h / tw = {h_web:.1f} / {tw:.1f} = <b>{flex_class['web_lambda']:.2f}</b></font>",
            equation_style
        ))
        
        story.append(Paragraph(
            f"<font face='Courier'>λpw = 3.76·√(E/Fy) = 3.76 × √({E:,.0f}/{Fy:.1f}) = <b>{flex_class['web_lambda_p']:.2f}</b></font>",
            equation_style
        ))
        
        story.append(Paragraph(
            f"<font face='Courier'>λrw = 5.70·√(E/Fy) = 5.70 × √({E:,.0f}/{Fy:.1f}) = <b>{flex_class['web_lambda_r']:.2f}</b></font>",
            equation_style
        ))
        
        # Web classification check
        if flex_class['web_lambda'] <= flex_class['web_lambda_p']:
            check_text = f"λw = {flex_class['web_lambda']:.2f} ≤ λpw = {flex_class['web_lambda_p']:.2f}"
            result_text = "WEB: COMPACT ✓"
            result_color = '#4caf50'
        elif flex_class['web_lambda'] <= flex_class['web_lambda_r']:
            check_text = f"λpw = {flex_class['web_lambda_p']:.2f} < λw = {flex_class['web_lambda']:.2f} ≤ λrw = {flex_class['web_lambda_r']:.2f}"
            result_text = "WEB: NON-COMPACT"
            result_color = '#ff9800'
        else:
            check_text = f"λw = {flex_class['web_lambda']:.2f} > λrw = {flex_class['web_lambda_r']:.2f}"
            result_text = "WEB: SLENDER ✗"
            result_color = '#f44336'
        
        story.append(Paragraph(f"<font face='Courier'>Check: {check_text}</font>", equation_style))
        story.append(Paragraph(
            f"<b>{result_text}</b>",
            ParagraphStyle('WebResult', parent=result_style, textColor=rl_colors.HexColor(result_color))
        ))
    
    # ==================== 4. FLEXURAL DESIGN ====================
    if analysis_results and 'flexural' in analysis_results:
        story.append(PageBreak())
        story.append(Paragraph("4. FLEXURAL DESIGN (AISC Chapter F2)", heading1_style))
        story.append(Spacer(1, 8))
        
        flex = analysis_results['flexural']
        Lb = design_params.get('Lb', 0)
        Cb = design_params.get('Cb', 1.0)
        
        # Step 1: Plastic Moment
        story.append(Paragraph("<b>Step 1: Calculate Plastic Moment Capacity (Mp)</b>", heading2_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Equation F2-1</i>", reference_style))
        story.append(Spacer(1, 4))
        
        Mp_kgcm = Fy * Zx
        Mp_tm = Mp_kgcm / 100000
        
        story.append(Paragraph(
            f"<font face='Courier'>Mp = Fy × Zx</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Mp = {Fy:.1f} × {Zx:,.1f}</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Mp = {Mp_kgcm:,.0f} kgf·cm = <b>{Mp_tm:.2f} t·m</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 2: Limiting Lengths
        story.append(Paragraph("<b>Step 2: Calculate Limiting Laterally Unbraced Lengths</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        # Lp calculation
        story.append(Paragraph("<b>Compact Limit Lp (Equation F2-5):</b>", body_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Equation F2-5</i>", reference_style))
        
        Lp_cm = 1.76 * ry * math.sqrt(E / Fy)
        story.append(Paragraph(
            f"<font face='Courier'>Lp = 1.76 × ry × √(E/Fy)</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Lp = 1.76 × {ry:.2f} × √({E:,.0f}/{Fy:.1f})</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Lp = {Lp_cm:.1f} cm = <b>{flex['Lp']:.3f} m</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 6))
        
        # Lr calculation
        story.append(Paragraph("<b>Inelastic Limit Lr (Equation F2-6):</b>", body_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Equation F2-6</i>", reference_style))
        
        story.append(Paragraph(
            f"<font face='Courier'>Lr = 1.95 × rts × (E/0.7Fy) × √(Jc/Sxho) × √(1 + √(1 + 6.76(0.7Fy/E)²(Sxho/Jc)²))</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>where: rts = {rts:.2f} cm, J = {J:.2f} cm⁴, ho = {ho:.1f} mm, c = 1.0</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Lr = <b>{flex['Lr']:.3f} m</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 3: Determine Nominal Moment
        story.append(Paragraph(f"<b>Step 3: Determine Nominal Moment (Lb = {Lb:.2f} m)</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        if Lb <= flex['Lp']:
            story.append(Paragraph(
                f"<font face='Courier'>Lb = {Lb:.2f} m ≤ Lp = {flex['Lp']:.3f} m</font>",
                equation_style
            ))
            story.append(Paragraph("<b>→ YIELDING CONTROLS (F2.1) - LTB does not apply</b>", body_style))
            story.append(Paragraph("<i>Reference: AISC 360-16, Equation F2-1</i>", reference_style))
            story.append(Paragraph(
                f"<font face='Courier'>Mn = Mp = <b>{flex['Mn']:.2f} t·m</b></font>",
                equation_style
            ))
            
        elif Lb <= flex['Lr']:
            story.append(Paragraph(
                f"<font face='Courier'>Lp = {flex['Lp']:.3f} m < Lb = {Lb:.2f} m ≤ Lr = {flex['Lr']:.3f} m</font>",
                equation_style
            ))
            story.append(Paragraph("<b>→ INELASTIC LATERAL-TORSIONAL BUCKLING (F2.2)</b>", body_style))
            story.append(Paragraph("<i>Reference: AISC 360-16, Equation F2-2</i>", reference_style))
            
            Mr = 0.7 * Fy * Sx / 100000
            story.append(Paragraph(
                f"<font face='Courier'>Mn = Cb × [Mp - (Mp - 0.7FySx) × ((Lb-Lp)/(Lr-Lp))] ≤ Mp</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Mn = {Cb:.2f} × [{Mp_tm:.2f} - ({Mp_tm:.2f} - {Mr:.2f}) × (({Lb:.2f}-{flex['Lp']:.3f})/({flex['Lr']:.3f}-{flex['Lp']:.3f}))]</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Mn = <b>{flex['Mn']:.2f} t·m</b></font>",
                equation_style
            ))
            
        else:
            story.append(Paragraph(
                f"<font face='Courier'>Lb = {Lb:.2f} m > Lr = {flex['Lr']:.3f} m</font>",
                equation_style
            ))
            story.append(Paragraph("<b>→ ELASTIC LATERAL-TORSIONAL BUCKLING (F2.3)</b>", body_style))
            story.append(Paragraph("<i>Reference: AISC 360-16, Equations F2-3 and F2-4</i>", reference_style))
            
            story.append(Paragraph(
                f"<font face='Courier'>Fcr = (Cb×π²×E)/((Lb/rts)²) × √(1 + 0.078(Jc/Sxho)(Lb/rts)²)</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Mn = Fcr × Sx ≤ Mp</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Mn = <b>{flex['Mn']:.2f} t·m</b></font>",
                equation_style
            ))
        
        story.append(Spacer(1, 8))
        
        # Step 4: Design Strength
        story.append(Paragraph("<b>Step 4: Calculate Design Flexural Strength</b>", heading2_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Section F1</i>", reference_style))
        story.append(Spacer(1, 4))
        
        story.append(Paragraph(
            f"<font face='Courier'>φb = 0.90 (LRFD)</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>φbMn = 0.90 × {flex['Mn']:.2f} = <b>{flex['phi_Mn']:.2f} t·m</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 5: Adequacy Check
        story.append(Paragraph("<b>Step 5: Adequacy Check</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        Mu = design_params.get('Mu', 0)
        ratio = flex['ratio']
        
        story.append(Paragraph(
            f"<font face='Courier'>Mu = {Mu:.2f} t·m</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>φbMn = {flex['phi_Mn']:.2f} t·m</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Ratio = Mu / φbMn = {Mu:.2f} / {flex['phi_Mn']:.2f} = <b>{ratio:.3f}</b></font>",
            equation_style
        ))
        
        if flex['adequate']:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {ratio:.3f} ≤ 1.0 → <b>OK ✓</b></font>",
                equation_style
            ))
            story.append(Paragraph("<b>FLEXURAL DESIGN: ADEQUATE ✓</b>", result_style))
        else:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {ratio:.3f} > 1.0 → <b>NG ✗</b></font>",
                equation_style
            ))
            story.append(Paragraph(
                "<b>FLEXURAL DESIGN: INADEQUATE ✗</b>",
                ParagraphStyle('FailResult', parent=result_style, 
                              textColor=rl_colors.HexColor('#c62828'),
                              backColor=rl_colors.HexColor('#ffebee'),
                              borderColor=rl_colors.HexColor('#f44336'))
            ))
        
        # Add flexural capacity chart
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("<b>Flexural Capacity Curve:</b>", body_style))
        story.append(Spacer(1, 6))
        
        fig_flex = create_flexural_capacity_chart(df, df_mat, section, material, Lb, Cb, flex)
        img_buffer_flex = BytesIO()
        plt.savefig(img_buffer_flex, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig_flex)
        img_buffer_flex.seek(0)
        
        flex_img = Image(img_buffer_flex, width=5.5*inch, height=3.5*inch)
        story.append(flex_img)
    
    # ==================== 5. COMPRESSION DESIGN ====================
    if analysis_results and 'compression' in analysis_results:
        story.append(PageBreak())
        story.append(Paragraph("5. COMPRESSION DESIGN (AISC Chapter E3)", heading1_style))
        story.append(Spacer(1, 8))
        
        comp = analysis_results['compression']
        KL = design_params.get('KL', 0)
        
        # Step 1: Slenderness Ratio
        story.append(Paragraph("<b>Step 1: Calculate Slenderness Ratio</b>", heading2_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Section E2</i>", reference_style))
        story.append(Spacer(1, 4))
        
        KL_cm = KL * 100
        lambda_x = KL_cm / rx
        lambda_y = KL_cm / ry
        lambda_c = max(lambda_x, lambda_y)
        
        story.append(Paragraph(
            f"<font face='Courier'>KL = {KL:.2f} m = {KL_cm:.0f} cm</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>(KL/r)x = {KL_cm:.0f} / {rx:.2f} = <b>{lambda_x:.1f}</b></font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>(KL/r)y = {KL_cm:.0f} / {ry:.2f} = <b>{lambda_y:.1f}</b></font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Governing: (KL/r)max = <b>{lambda_c:.1f}</b> {'(X-axis)' if lambda_x >= lambda_y else '(Y-axis)'}</font>",
            equation_style
        ))
        
        # Check slenderness limit
        if lambda_c <= 200:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {lambda_c:.1f} ≤ 200 → OK (AISC E2)</font>",
                equation_style
            ))
        else:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {lambda_c:.1f} > 200 → Exceeds preferred limit (AISC E2)</font>",
                equation_style
            ))
        story.append(Spacer(1, 8))
        
        # Step 2: Elastic Buckling Stress
        story.append(Paragraph("<b>Step 2: Calculate Elastic Buckling Stress (Fe)</b>", heading2_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Equation E3-4</i>", reference_style))
        story.append(Spacer(1, 4))
        
        Fe = (math.pi**2 * E) / (lambda_c**2)
        
        story.append(Paragraph(
            f"<font face='Courier'>Fe = π²E / (KL/r)²</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Fe = π² × {E:,.0f} / {lambda_c:.1f}²</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Fe = <b>{Fe:,.1f} kgf/cm²</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 3: Critical Stress
        story.append(Paragraph("<b>Step 3: Determine Critical Stress (Fcr)</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        lambda_limit = 4.71 * math.sqrt(E / Fy)
        
        story.append(Paragraph(
            f"<font face='Courier'>Limiting Slenderness = 4.71 × √(E/Fy) = 4.71 × √({E:,.0f}/{Fy:.1f}) = {lambda_limit:.1f}</font>",
            equation_style
        ))
        
        if lambda_c <= lambda_limit:
            story.append(Paragraph(
                f"<font face='Courier'>(KL/r) = {lambda_c:.1f} ≤ {lambda_limit:.1f}</font>",
                equation_style
            ))
            story.append(Paragraph("<b>→ INELASTIC BUCKLING CONTROLS (E3-2)</b>", body_style))
            story.append(Paragraph("<i>Reference: AISC 360-16, Equation E3-2</i>", reference_style))
            
            story.append(Paragraph(
                f"<font face='Courier'>Fcr = [0.658^(Fy/Fe)] × Fy</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Fcr = [0.658^({Fy:.1f}/{Fe:.1f})] × {Fy:.1f}</font>",
                equation_style
            ))
        else:
            story.append(Paragraph(
                f"<font face='Courier'>(KL/r) = {lambda_c:.1f} > {lambda_limit:.1f}</font>",
                equation_style
            ))
            story.append(Paragraph("<b>→ ELASTIC BUCKLING CONTROLS (E3-3)</b>", body_style))
            story.append(Paragraph("<i>Reference: AISC 360-16, Equation E3-3</i>", reference_style))
            
            story.append(Paragraph(
                f"<font face='Courier'>Fcr = 0.877 × Fe</font>",
                equation_style
            ))
            story.append(Paragraph(
                f"<font face='Courier'>Fcr = 0.877 × {Fe:.1f}</font>",
                equation_style
            ))
        
        story.append(Paragraph(
            f"<font face='Courier'>Fcr = <b>{comp['Fcr']:,.1f} kgf/cm²</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 4: Nominal and Design Strength
        story.append(Paragraph("<b>Step 4: Calculate Nominal and Design Strength</b>", heading2_style))
        story.append(Paragraph("<i>Reference: AISC 360-16, Equation E3-1</i>", reference_style))
        story.append(Spacer(1, 4))
        
        story.append(Paragraph(
            f"<font face='Courier'>Pn = Fcr × Ag</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Pn = {comp['Fcr']:,.1f} × {A:.2f} = {comp['Fcr']*A:,.0f} kgf = <b>{comp['Pn']:.2f} tons</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 4))
        
        story.append(Paragraph(
            f"<font face='Courier'>φc = 0.90 (LRFD)</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>φcPn = 0.90 × {comp['Pn']:.2f} = <b>{comp['phi_Pn']:.2f} tons</b></font>",
            equation_style
        ))
        story.append(Spacer(1, 8))
        
        # Step 5: Adequacy Check
        story.append(Paragraph("<b>Step 5: Adequacy Check</b>", heading2_style))
        story.append(Spacer(1, 4))
        
        Pu = design_params.get('Pu', 0)
        ratio = comp['ratio']
        
        story.append(Paragraph(
            f"<font face='Courier'>Pu = {Pu:.2f} tons</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>φcPn = {comp['phi_Pn']:.2f} tons</font>",
            equation_style
        ))
        story.append(Paragraph(
            f"<font face='Courier'>Ratio = Pu / φcPn = {Pu:.2f} / {comp['phi_Pn']:.2f} = <b>{ratio:.3f}</b></font>",
            equation_style
        ))
        
        if comp['adequate']:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {ratio:.3f} ≤ 1.0 → <b>OK ✓</b></font>",
                equation_style
            ))
            story.append(Paragraph("<b>COMPRESSION DESIGN: ADEQUATE ✓</b>", result_style))
        else:
            story.append(Paragraph(
                f"<font face='Courier'>Check: {ratio:.3f} > 1.0 → <b>NG ✗</b></font>",
                equation_style
            ))
            story.append(Paragraph(
                "<b>COMPRESSION DESIGN: INADEQUATE ✗</b>",
                ParagraphStyle('FailResult', parent=result_style, 
                              textColor=rl_colors.HexColor('#c62828'),
                              backColor=rl_colors.HexColor('#ffebee'),
                              borderColor=rl_colors.HexColor('#f44336'))
            ))
        
        # Add compression capacity chart
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph("<b>Column Capacity Curve:</b>", body_style))
        story.append(Spacer(1, 6))
        
        fig_comp = create_compression_capacity_chart(E, Fy, A, lambda_c, lambda_limit, comp, Pu)
        img_buffer_comp = BytesIO()
        plt.savefig(img_buffer_comp, format='png', dpi=150, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig_comp)
        img_buffer_comp.seek(0)
        
        comp_img = Image(img_buffer_comp, width=5.5*inch, height=3.5*inch)
        story.append(comp_img)
    
    # ==================== 6. DESIGN SUMMARY ====================
    story.append(PageBreak())
    story.append(Paragraph("6. DESIGN SUMMARY & CONCLUSION", heading1_style))
    story.append(Spacer(1, 10))
    
    # Summary Table
    summary_data = [
        ['CHECK', 'CAPACITY', 'DEMAND', 'RATIO', 'STATUS'],
    ]
    
    if 'flexural' in analysis_results:
        flex = analysis_results['flexural']
        Mu = design_params.get('Mu', 0)
        status = '✓ PASS' if flex['adequate'] else '✗ FAIL'
        summary_data.append(['Flexural (φbMn)', f"{flex['phi_Mn']:.2f} t·m", 
                           f"{Mu:.2f} t·m", f"{flex['ratio']:.3f}", status])
    
    if 'compression' in analysis_results:
        comp = analysis_results['compression']
        Pu = design_params.get('Pu', 0)
        status = '✓ PASS' if comp['adequate'] else '✗ FAIL'
        summary_data.append(['Compression (φcPn)', f"{comp['phi_Pn']:.2f} tons",
                           f"{Pu:.2f} tons", f"{comp['ratio']:.3f}", status])
    
    summary_table = Table(summary_data, colWidths=[1.6*inch, 1.3*inch, 1.2*inch, 0.9*inch, 1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.HexColor('#1a237e')),
    ]))
    
    # Color code status column
    for i, row in enumerate(summary_data[1:], start=1):
        if '✓' in row[-1]:
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (-1, i), (-1, i), rl_colors.HexColor('#c8e6c9')),
                ('TEXTCOLOR', (-1, i), (-1, i), rl_colors.HexColor('#2e7d32')),
                ('FONTNAME', (-1, i), (-1, i), 'Helvetica-Bold'),
            ]))
        else:
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (-1, i), (-1, i), rl_colors.HexColor('#ffcdd2')),
                ('TEXTCOLOR', (-1, i), (-1, i), rl_colors.HexColor('#c62828')),
                ('FONTNAME', (-1, i), (-1, i), 'Helvetica-Bold'),
            ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Overall Conclusion
    overall_adequate = True
    if 'flexural' in analysis_results:
        overall_adequate = overall_adequate and analysis_results['flexural']['adequate']
    if 'compression' in analysis_results:
        overall_adequate = overall_adequate and analysis_results['compression']['adequate']
    
    if overall_adequate:
        conclusion_style = ParagraphStyle(
            'Conclusion',
            parent=result_style,
            fontSize=14,
            textColor=rl_colors.HexColor('#1b5e20'),
            backColor=rl_colors.HexColor('#c8e6c9'),
            borderColor=rl_colors.HexColor('#4caf50'),
            borderWidth=3
        )
        story.append(Paragraph(
            f"<b>CONCLUSION: SECTION {section} IS ADEQUATE FOR THE DESIGN LOADS ✓</b>",
            conclusion_style
        ))
    else:
        conclusion_style = ParagraphStyle(
            'Conclusion',
            parent=result_style,
            fontSize=14,
            textColor=rl_colors.HexColor('#b71c1c'),
            backColor=rl_colors.HexColor('#ffcdd2'),
            borderColor=rl_colors.HexColor('#f44336'),
            borderWidth=3
        )
        story.append(Paragraph(
            f"<b>CONCLUSION: SECTION {section} IS INADEQUATE - REVISE DESIGN ✗</b>",
            conclusion_style
        ))
    
    # Signature Block
    story.append(Spacer(1, 0.5*inch))
    
    sig_data = [
        ['PREPARED BY:', '', 'CHECKED BY:', ''],
        ['', '', '', ''],
        ['', '', '', ''],
        [f"Name: {project_info.get('designer', '_______________')}", '',
         f"Name: {project_info.get('checker', '_______________')}", ''],
        ['Date: _____________', '', 'Date: _____________', ''],
        ['Signature: _____________', '', 'Signature: _____________', ''],
    ]
    
    sig_table = Table(sig_data, colWidths=[2*inch, 0.7*inch, 2*inch, 0.7*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)
    
    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer

def create_detailed_section_diagram(d, bf, tf, tw, section_name):
    """Create a detailed I-beam cross-section diagram with dimensions"""
    fig, ax = plt.subplots(figsize=(6, 5))
    
    # Scale for visualization
    scale = 1.0
    d_s, bf_s, tf_s, tw_s = d*scale, bf*scale, tf*scale, tw*scale
    
    # Center
    cx, cy = 0, 0
    
    # Draw I-beam
    # Top flange
    ax.add_patch(patches.Rectangle(
        (cx - bf_s/2, cy + d_s/2 - tf_s), bf_s, tf_s,
        linewidth=2, edgecolor='#1a237e', facecolor='#e8eaf6'
    ))
    
    # Bottom flange
    ax.add_patch(patches.Rectangle(
        (cx - bf_s/2, cy - d_s/2), bf_s, tf_s,
        linewidth=2, edgecolor='#1a237e', facecolor='#e8eaf6'
    ))
    
    # Web
    ax.add_patch(patches.Rectangle(
        (cx - tw_s/2, cy - d_s/2 + tf_s), tw_s, d_s - 2*tf_s,
        linewidth=2, edgecolor='#1a237e', facecolor='#e8eaf6'
    ))
    
    # Dimension lines
    arrow_props = dict(arrowstyle='<->', color='#d32f2f', lw=1.5)
    
    # Overall height (d)
    offset_d = bf_s * 0.25
    ax.annotate('', xy=(bf_s/2 + offset_d, d_s/2),
                xytext=(bf_s/2 + offset_d, -d_s/2),
                arrowprops=arrow_props)
    ax.text(bf_s/2 + offset_d*1.8, 0, f'd = {d:.0f} mm',
            fontsize=10, color='#d32f2f', va='center', fontweight='bold')
    
    # Flange width (bf)
    offset_bf = d_s * 0.15
    ax.annotate('', xy=(-bf_s/2, d_s/2 + offset_bf),
                xytext=(bf_s/2, d_s/2 + offset_bf),
                arrowprops=arrow_props)
    ax.text(0, d_s/2 + offset_bf*2, f'bf = {bf:.0f} mm',
            fontsize=10, color='#d32f2f', ha='center', fontweight='bold')
    
    # Flange thickness (tf)
    ax.annotate('', xy=(-bf_s/2 - offset_d*0.5, d_s/2),
                xytext=(-bf_s/2 - offset_d*0.5, d_s/2 - tf_s),
                arrowprops=dict(arrowstyle='<->', color='#1976d2', lw=1.2))
    ax.text(-bf_s/2 - offset_d*1.5, d_s/2 - tf_s/2, f'tf = {tf:.1f}',
            fontsize=9, color='#1976d2', va='center', ha='right')
    
    # Web thickness (tw)
    ax.annotate('', xy=(-tw_s/2, -d_s/2 + tf_s + offset_bf*0.5),
                xytext=(tw_s/2, -d_s/2 + tf_s + offset_bf*0.5),
                arrowprops=dict(arrowstyle='<->', color='#388e3c', lw=1.2))
    ax.text(0, -d_s/2 + tf_s - offset_bf*0.8, f'tw = {tw:.1f}',
            fontsize=9, color='#388e3c', ha='center')
    
    # Styling
    ax.set_xlim(-bf_s * 1.0, bf_s * 1.3)
    ax.set_ylim(-d_s * 0.75, d_s * 0.85)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f'{section_name}\nCross-Section', fontsize=12, fontweight='bold', color='#1a237e')
    
    # Add axis labels
    ax.plot([cx, cx], [-d_s*0.6, d_s*0.6], 'k--', lw=0.5, alpha=0.5)
    ax.plot([-bf_s*0.6, bf_s*0.6], [cy, cy], 'k--', lw=0.5, alpha=0.5)
    ax.text(bf_s*0.65, 0, 'X', fontsize=8, va='center')
    ax.text(0, d_s*0.65, 'Y', fontsize=8, ha='center')
    
    plt.tight_layout()
    return fig


def create_flexural_capacity_chart(df, df_mat, section, material, Lb, Cb, flex_result):
    """Create flexural capacity curve for PDF report"""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Generate capacity curve
    Lb_points = np.linspace(0.1, 15, 200)
    Mn_points = []
    
    for lb in Lb_points:
        r = aisc_360_16_f2_flexural_design(df, df_mat, section, material, lb, Cb)
        Mn_points.append(0.9 * r['Mn'] if r else 0)
    
    # Plot capacity curve
    ax.plot(Lb_points, Mn_points, 'b-', linewidth=2.5, label='φbMn Capacity')
    
    # Zone shading
    ax.axvspan(0, flex_result['Lp'], alpha=0.15, color='green', label='Yielding Zone (F2.1)')
    ax.axvspan(flex_result['Lp'], flex_result['Lr'], alpha=0.15, color='orange', label='Inelastic LTB (F2.2)')
    ax.axvspan(flex_result['Lr'], 15, alpha=0.15, color='red', label='Elastic LTB (F2.3)')
    
    # Vertical lines
    ax.axvline(x=flex_result['Lp'], color='green', linestyle='--', linewidth=1.5)
    ax.axvline(x=flex_result['Lr'], color='orange', linestyle='--', linewidth=1.5)
    
    # Add labels
    ax.text(flex_result['Lp'], ax.get_ylim()[1]*0.95, f'Lp={flex_result["Lp"]:.2f}m',
            fontsize=9, color='green', ha='center', fontweight='bold')
    ax.text(flex_result['Lr'], ax.get_ylim()[1]*0.95, f'Lr={flex_result["Lr"]:.2f}m',
            fontsize=9, color='orange', ha='center', fontweight='bold')
    
    # Design point
    ax.plot([Lb], [flex_result['phi_Mn']], 'r*', markersize=15, 
            label=f'Design Point (Lb={Lb:.2f}m)', zorder=5)
    
    # Styling
    ax.set_xlabel('Unbraced Length, Lb (m)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Design Moment, φbMn (t·m)', fontsize=11, fontweight='bold')
    ax.set_title(f'AISC F2: Flexural Capacity Curve - {section}', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, None)
    
    plt.tight_layout()
    return fig


def create_compression_capacity_chart(E, Fy, Ag, lambda_c, lambda_limit, comp_result, Pu):
    """Create compression capacity curve for PDF report"""
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Generate capacity curve
    lambda_points = np.linspace(1, 250, 250)
    Pn_points = []
    
    for lc in lambda_points:
        Fe = (math.pi**2 * E) / (lc**2)
        if lc <= lambda_limit:
            Fcr = (0.658**(Fy/Fe)) * Fy
        else:
            Fcr = 0.877 * Fe
        Pn_points.append(0.9 * Fcr * Ag / 1000.0)
    
    # Plot capacity curve
    ax.plot(lambda_points, Pn_points, 'b-', linewidth=2.5, label='φcPn Capacity')
    
    # Zone shading
    ax.axvspan(0, lambda_limit, alpha=0.15, color='green', label='Inelastic Buckling (E3-2)')
    ax.axvspan(lambda_limit, 250, alpha=0.15, color='orange', label='Elastic Buckling (E3-3)')
    
    # Vertical line at limit
    ax.axvline(x=lambda_limit, color='orange', linestyle='--', linewidth=1.5)
    ax.text(lambda_limit, ax.get_ylim()[1]*0.95 if ax.get_ylim()[1] > 0 else Pn_points[0]*0.95, 
            f'λ limit={lambda_limit:.1f}',
            fontsize=9, color='orange', ha='center', fontweight='bold')
    
    # Design point
    ax.plot([comp_result['lambda_c']], [comp_result['phi_Pn']], 'r*', markersize=15,
            label=f'Design Point (λ={comp_result["lambda_c"]:.1f})', zorder=5)
    
    # Demand line
    if Pu > 0:
        ax.axhline(y=Pu, color='red', linestyle='--', linewidth=1.5, label=f'Pu = {Pu:.1f} tons')
    
    # Styling
    ax.set_xlabel('Slenderness Ratio (KL/r)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Design Strength, φcPn (tons)', fontsize=11, fontweight='bold')
    ax.set_title('AISC E3: Column Capacity Curve', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle=':')
    ax.legend(loc='upper right', fontsize=9, framealpha=0.95)
    ax.set_xlim(0, 250)
    ax.set_ylim(0, None)
    
    plt.tight_layout()
    return fig

# ==================== AISC CLASSIFICATION FUNCTIONS ====================
def classify_section_flexure(df, df_mat, section, material):
    """
    Classify section elements for flexural design per AISC 360-16 Table B4.1b
    Returns: dict with flange and web classifications
    """
    try:
        # Get section properties
        bf = safe_scalar(df.loc[section, 'bf [mm]'])
        tf = safe_scalar(df.loc[section, 'tf [mm]'])
        
        # For web
        if 'ho [mm]' in df.columns:
            h = safe_scalar(df.loc[section, 'ho [mm]'])
        else:
            d = safe_scalar(df.loc[section, 'd [mm]'])
            h = d - 2 * tf
        
        tw = safe_scalar(df.loc[section, 'tw [mm]'])
        
        # Material properties
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        # Flange slenderness (AISC Table B4.1b Case 10 - Flanges of I-sections)
        lambda_f = (bf / 2.0) / tf
        lambda_pf = 0.38 * safe_sqrt(E / Fy)
        lambda_rf = 1.0 * safe_sqrt(E / Fy)
        
        if lambda_f <= lambda_pf:
            flange_class = "Compact"
        elif lambda_f <= lambda_rf:
            flange_class = "Non-compact"
        else:
            flange_class = "Slender"
        
        # Web slenderness (AISC Table B4.1b Case 15 - Webs in flexural compression)
        lambda_w = h / tw
        lambda_pw = 3.76 * safe_sqrt(E / Fy)
        lambda_rw = 5.70 * safe_sqrt(E / Fy)
        
        if lambda_w <= lambda_pw:
            web_class = "Compact"
        elif lambda_w <= lambda_rw:
            web_class = "Non-compact"
        else:
            web_class = "Slender"
        
        return {
            'flange_class': flange_class,
            'flange_lambda': lambda_f,
            'flange_lambda_p': lambda_pf,
            'flange_lambda_r': lambda_rf,
            'web_class': web_class,
            'web_lambda': lambda_w,
            'web_lambda_p': lambda_pw,
            'web_lambda_r': lambda_rw
        }
        
    except Exception as e:
        st.error(f"Error in flexural classification: {e}")
        return None

def classify_section_compression(df, df_mat, section, material):
    """
    Classify section elements for compression design per AISC 360-16 Table B4.1a
    Returns: dict with overall classification
    """
    try:
        # Get section properties
        bf = safe_scalar(df.loc[section, 'bf [mm]'])
        tf = safe_scalar(df.loc[section, 'tf [mm]'])
        
        d = safe_scalar(df.loc[section, 'd [mm]'])
        tw = safe_scalar(df.loc[section, 'tw [mm]'])
        h = d - 2 * tf
        
        # Material properties
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        # Flange slenderness (AISC Table B4.1a Case 1 - Flanges of I-sections)
        lambda_f = (bf / 2.0) / tf
        lambda_r_flange = 0.56 * safe_sqrt(E / Fy)
        
        # Web slenderness (AISC Table B4.1a Case 5 - Webs of doubly symmetric I-sections)
        lambda_w = h / tw
        lambda_r_web = 1.49 * safe_sqrt(E / Fy)
        
        flange_slender = lambda_f > lambda_r_flange
        web_slender = lambda_w > lambda_r_web
        
        if flange_slender or web_slender:
            overall_class = "Slender"
            limiting_element = []
            if flange_slender:
                limiting_element.append("Flange")
            if web_slender:
                limiting_element.append("Web")
            limiting = " & ".join(limiting_element)
        else:
            overall_class = "Non-slender"
            limiting = "N/A"
        
        return {
            'overall_class': overall_class,
            'limiting_element': limiting,
            'flange_lambda': lambda_f,
            'flange_lambda_r': lambda_r_flange,
            'flange_slender': flange_slender,
            'web_lambda': lambda_w,
            'web_lambda_r': lambda_r_web,
            'web_slender': web_slender
        }
        
    except Exception as e:
        st.error(f"Error in compression classification: {e}")
        return None

def generate_excel_report(df, df_mat, section, material, analysis_results, design_params):
    """Generate comprehensive Excel calculation report with formatting"""
    if not EXCEL_AVAILABLE:
        return None
    
    buffer = BytesIO()
    wb = Workbook()
    
    # Define styles
    header_fill = PatternFill(start_color="667EEA", end_color="667EEA", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    title_font = Font(bold=True, size=16, color="667EEA")
    subtitle_font = Font(bold=True, size=14, color="2c3e50")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Compact/Non-compact fill colors
    compact_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    noncompact_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    slender_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    
    # Get classifications
    flex_class = classify_section_flexure(df, df_mat, section, material)
    comp_class = classify_section_compression(df, df_mat, section, material)
    
    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = "Design Summary"
    
    # Title
    ws_summary['A1'] = "AISC 360-16 STEEL DESIGN CALCULATION REPORT"
    ws_summary['A1'].font = title_font
    ws_summary['A1'].alignment = center_align
    ws_summary.merge_cells('A1:D1')
    
    # Header Info
    row = 3
    ws_summary[f'A{row}'] = "Report Generated:"
    ws_summary[f'B{row}'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row += 1
    ws_summary[f'A{row}'] = "Section:"
    ws_summary[f'B{row}'] = section
    row += 1
    ws_summary[f'A{row}'] = "Material Grade:"
    ws_summary[f'B{row}'] = material
    
    # Format header
    for r in range(3, 6):
        ws_summary[f'A{r}'].font = Font(bold=True)
        ws_summary[f'A{r}'].fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
    
    # Material Properties
    row = 8
    ws_summary[f'A{row}'] = "MATERIAL PROPERTIES"
    ws_summary[f'A{row}'].font = subtitle_font
    ws_summary.merge_cells(f'A{row}:C{row}')
    
    row += 1
    headers = ['Property', 'Value', 'Unit']
    for col, header in enumerate(headers, start=1):
        cell = ws_summary.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border
    
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    Fu = safe_scalar(df_mat.loc[material, "Tensile Strength (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    mat_props = [
        ['Yield Strength (Fy)', f'{Fy:.1f}', 'kgf/cm²'],
        ['Tensile Strength (Fu)', f'{Fu:.1f}', 'kgf/cm²'],
        ['Modulus of Elasticity (E)', f'{E:.0f}', 'kgf/cm²']
    ]
    
    for prop_row in mat_props:
        row += 1
        for col, value in enumerate(prop_row, start=1):
            cell = ws_summary.cell(row=row, column=col)
            cell.value = value
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
    
    # ========== COMPREHENSIVE SECTION PROPERTIES ==========
    row += 3
    ws_summary[f'A{row}'] = "COMPLETE SECTION PROPERTIES"
    ws_summary[f'A{row}'].font = subtitle_font
    ws_summary.merge_cells(f'A{row}:C{row}')
    
    row += 1
    for col, header in enumerate(headers, start=1):
        cell = ws_summary.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border
    
    # Comprehensive property list
    property_list = [
        ('d [mm]', 'Overall Depth'),
        ('bf [mm]', 'Flange Width'),
        ('tw [mm]', 'Web Thickness'),
        ('tf [mm]', 'Flange Thickness'),
        ('r [mm]', 'Fillet Radius'),
        ('A [cm2]', 'Cross-sectional Area'),
        ('Ix [cm4]', 'Moment of Inertia X-axis'),
        ('Iy [cm4]', 'Moment of Inertia Y-axis'),
        ('rx [cm]', 'Radius of Gyration X-axis'),
        ('ry [cm]', 'Radius of Gyration Y-axis'),
        ('Sx [cm3]', 'Elastic Section Modulus X'),
        ('Sy [cm3]', 'Elastic Section Modulus Y'),
        ('Zx [cm3]', 'Plastic Section Modulus X'),
        ('Zy [cm3]', 'Plastic Section Modulus Y'),
        ('h/tw', 'Web Slenderness Ratio'),
        ('0.5bf/tf', 'Flange Slenderness Ratio'),
        ('ho [mm]', 'Distance Between Flange Centroids'),
        ('j [cm4]', 'Torsional Constant'),
        ('cw [10^6 cm6]', 'Warping Constant'),
        ('rts [cm6]', 'Effective Radius'),
        ('Lp [cm]', 'Limiting Length for Plastic'),
        ('Lr [cm]', 'Limiting Length for Inelastic LTB')
    ]
    
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
    if weight_col in df.columns:
        weight = safe_scalar(df.loc[section, weight_col])
        row += 1
        ws_summary[f'A{row}'] = "Unit Weight"
        ws_summary[f'B{row}'] = f'{weight:.2f}'
        ws_summary[f'C{row}'] = 'kg/m'
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
    
    for prop_key, prop_description in property_list:
        if prop_key in df.columns:
            row += 1
            value = safe_scalar(df.loc[section, prop_key])
            unit = prop_key.split('[')[1].replace(']', '') if '[' in prop_key else ''
            
            ws_summary[f'A{row}'] = prop_description
            ws_summary[f'B{row}'] = f'{value:.3f}' if value < 100 else f'{value:.2f}'
            ws_summary[f'C{row}'] = unit
            
            for col in range(1, 4):
                cell = ws_summary.cell(row=row, column=col)
                cell.border = border
                cell.alignment = center_align if col > 1 else left_align
    
    # ========== FLEXURAL CLASSIFICATION ==========
    if flex_class:
        row += 3
        ws_summary[f'A{row}'] = "FLEXURAL MEMBER CLASSIFICATION (AISC Table B4.1b)"
        ws_summary[f'A{row}'].font = subtitle_font
        ws_summary.merge_cells(f'A{row}:C{row}')
        
        row += 1
        ws_summary[f'A{row}'] = "Element"
        ws_summary[f'B{row}'] = "Classification"
        ws_summary[f'C{row}'] = "Details"
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        # Flange classification
        row += 1
        ws_summary[f'A{row}'] = "Flange"
        ws_summary[f'B{row}'] = flex_class['flange_class']
        ws_summary[f'C{row}'] = f"λ={flex_class['flange_lambda']:.2f}, λp={flex_class['flange_lambda_p']:.2f}, λr={flex_class['flange_lambda_r']:.2f}"
        
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
            
            if col == 2:  # Classification column
                if flex_class['flange_class'] == "Compact":
                    cell.fill = compact_fill
                    cell.font = Font(bold=True, color="2E7D32")
                elif flex_class['flange_class'] == "Non-compact":
                    cell.fill = noncompact_fill
                    cell.font = Font(bold=True, color="F57C00")
                else:
                    cell.fill = slender_fill
                    cell.font = Font(bold=True, color="C62828")
        
        # Web classification
        row += 1
        ws_summary[f'A{row}'] = "Web"
        ws_summary[f'B{row}'] = flex_class['web_class']
        ws_summary[f'C{row}'] = f"λ={flex_class['web_lambda']:.2f}, λp={flex_class['web_lambda_p']:.2f}, λr={flex_class['web_lambda_r']:.2f}"
        
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
            
            if col == 2:  # Classification column
                if flex_class['web_class'] == "Compact":
                    cell.fill = compact_fill
                    cell.font = Font(bold=True, color="2E7D32")
                elif flex_class['web_class'] == "Non-compact":
                    cell.fill = noncompact_fill
                    cell.font = Font(bold=True, color="F57C00")
                else:
                    cell.fill = slender_fill
                    cell.font = Font(bold=True, color="C62828")
    
    # ========== COMPRESSION CLASSIFICATION ==========
    if comp_class:
        row += 3
        ws_summary[f'A{row}'] = "COMPRESSION MEMBER CLASSIFICATION (AISC Table B4.1a)"
        ws_summary[f'A{row}'].font = subtitle_font
        ws_summary.merge_cells(f'A{row}:C{row}')
        
        row += 1
        ws_summary[f'A{row}'] = "Element"
        ws_summary[f'B{row}'] = "Classification"
        ws_summary[f'C{row}'] = "Details"
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        # Overall classification
        row += 1
        ws_summary[f'A{row}'] = "Overall Section"
        ws_summary[f'B{row}'] = comp_class['overall_class']
        
        if comp_class['overall_class'] == "Slender":
            ws_summary[f'C{row}'] = f"Limiting: {comp_class['limiting_element']}"
        else:
            ws_summary[f'C{row}'] = "All elements within limits"
        
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
            
            if col == 2:  # Classification column
                if comp_class['overall_class'] == "Non-slender":
                    cell.fill = compact_fill
                    cell.font = Font(bold=True, color="2E7D32")
                else:
                    cell.fill = slender_fill
                    cell.font = Font(bold=True, color="C62828")
        
        # Flange details
        row += 1
        ws_summary[f'A{row}'] = "Flange"
        ws_summary[f'B{row}'] = "Slender" if comp_class['flange_slender'] else "Non-slender"
        ws_summary[f'C{row}'] = f"λ={comp_class['flange_lambda']:.2f}, λr={comp_class['flange_lambda_r']:.2f}"
        
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
        
        # Web details
        row += 1
        ws_summary[f'A{row}'] = "Web"
        ws_summary[f'B{row}'] = "Slender" if comp_class['web_slender'] else "Non-slender"
        ws_summary[f'C{row}'] = f"λ={comp_class['web_lambda']:.2f}, λr={comp_class['web_lambda_r']:.2f}"
        
        for col in range(1, 4):
            cell = ws_summary.cell(row=row, column=col)
            cell.border = border
            cell.alignment = center_align if col > 1 else left_align
    
    # Auto-size columns for Summary sheet
    try:
        for col_idx in range(1, ws_summary.max_column + 1):
            column_letter = get_column_letter(col_idx)
            max_length = 0
            for row_idx in range(1, ws_summary.max_row + 1):
                cell = ws_summary.cell(row=row_idx, column=col_idx)
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max_length + 2, 60)
            ws_summary.column_dimensions[column_letter].width = adjusted_width
    except:
        ws_summary.column_dimensions['A'].width = 40
        ws_summary.column_dimensions['B'].width = 25
        ws_summary.column_dimensions['C'].width = 30
        ws_summary.column_dimensions['D'].width = 15
    
    # Sheet 2: Analysis Results
    if analysis_results:
        ws_results = wb.create_sheet("Analysis Results")
        
        row = 1
        ws_results['A1'] = "DESIGN ANALYSIS RESULTS"
        ws_results['A1'].font = title_font
        ws_results.merge_cells('A1:D1')
        
        # Flexural Analysis
        if 'flexural' in analysis_results:
            row = 3
            ws_results[f'A{row}'] = "FLEXURAL ANALYSIS (AISC F2)"
            ws_results[f'A{row}'].font = subtitle_font
            ws_results.merge_cells(f'A{row}:B{row}')
            
            row += 1
            ws_results[f'A{row}'] = "Parameter"
            ws_results[f'B{row}'] = "Value"
            for col in range(1, 3):
                cell = ws_results.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = border
            
            flex_data = [
                ['Design Moment (φMn)', f"{analysis_results['flexural']['phi_Mn']:.2f} t·m"],
                ['Nominal Moment (Mn)', f"{analysis_results['flexural']['Mn']:.2f} t·m"],
                ['Plastic Moment (Mp)', f"{analysis_results['flexural']['Mp']:.2f} t·m"],
                ['Critical Length (Lp)', f"{analysis_results['flexural']['Lp']:.3f} m"],
                ['Critical Length (Lr)', f"{analysis_results['flexural']['Lr']:.3f} m"],
                ['Design Case', analysis_results['flexural']['case']],
                ['Design Zone', analysis_results['flexural']['zone']],
                ['Utilization Ratio', f"{analysis_results['flexural']['ratio']:.3f}"],
                ['Status', '✓ ADEQUATE' if analysis_results['flexural']['adequate'] else '✗ INADEQUATE']
            ]
            
            for data_row in flex_data:
                row += 1
                ws_results[f'A{row}'] = data_row[0]
                ws_results[f'B{row}'] = data_row[1]
                for col in range(1, 3):
                    cell = ws_results.cell(row=row, column=col)
                    cell.border = border
                    cell.alignment = left_align if col == 1 else center_align
                    
                    # Color code status
                    if col == 2 and data_row[0] == 'Status':
                        if '✓' in str(data_row[1]):
                            cell.fill = compact_fill
                            cell.font = Font(bold=True, color="2E7D32")
                        else:
                            cell.fill = slender_fill
                            cell.font = Font(bold=True, color="C62828")
        
        # Compression Analysis
        if 'compression' in analysis_results:
            row += 3
            ws_results[f'A{row}'] = "COMPRESSION ANALYSIS (AISC E3)"
            ws_results[f'A{row}'].font = subtitle_font
            ws_results.merge_cells(f'A{row}:B{row}')
            
            row += 1
            ws_results[f'A{row}'] = "Parameter"
            ws_results[f'B{row}'] = "Value"
            for col in range(1, 3):
                cell = ws_results.cell(row=row, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = border
            
            comp_data = [
                ['Design Strength (φPn)', f"{analysis_results['compression']['phi_Pn']:.2f} tons"],
                ['Nominal Strength (Pn)', f"{analysis_results['compression']['Pn']:.2f} tons"],
                ['Critical Stress (Fcr)', f"{analysis_results['compression']['Fcr']:.1f} kgf/cm²"],
                ['Slenderness Ratio (λc)', f"{analysis_results['compression']['lambda_c']:.1f}"],
                ['Buckling Mode', analysis_results['compression']['mode']],
                ['Utilization Ratio', f"{analysis_results['compression']['ratio']:.3f}"],
                ['Status', '✓ ADEQUATE' if analysis_results['compression']['adequate'] else '✗ INADEQUATE']
            ]
            
            for data_row in comp_data:
                row += 1
                ws_results[f'A{row}'] = data_row[0]
                ws_results[f'B{row}'] = data_row[1]
                for col in range(1, 3):
                    cell = ws_results.cell(row=row, column=col)
                    cell.border = border
                    cell.alignment = left_align if col == 1 else center_align
                    
                    # Color code status
                    if col == 2 and data_row[0] == 'Status':
                        if '✓' in str(data_row[1]):
                            cell.fill = compact_fill
                            cell.font = Font(bold=True, color="2E7D32")
                        else:
                            cell.fill = slender_fill
                            cell.font = Font(bold=True, color="C62828")
        
        # Design Parameters Sheet
        ws_params = wb.create_sheet("Design Parameters")
        
        row = 1
        ws_params['A1'] = "DESIGN INPUT PARAMETERS"
        ws_params['A1'].font = title_font
        ws_params.merge_cells('A1:B1')
        
        row = 3
        ws_params[f'A{row}'] = "Parameter"
        ws_params[f'B{row}'] = "Value"
        for col in range(1, 3):
            cell = ws_params.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        if design_params:
            param_data = []
            if 'Mu' in design_params:
                param_data.append(['Applied Moment (Mu)', f"{design_params['Mu']:.2f} t·m"])
            if 'Pu' in design_params:
                param_data.append(['Applied Axial Load (Pu)', f"{design_params['Pu']:.2f} tons"])
            if 'Lb' in design_params:
                param_data.append(['Unbraced Length (Lb)', f"{design_params['Lb']:.2f} m"])
            if 'KL' in design_params:
                param_data.append(['Effective Length (KL)', f"{design_params['KL']:.2f} m"])
            if 'KLx' in design_params:
                param_data.append(['Effective Length X (KLx)', f"{design_params['KLx']:.2f} m"])
            if 'KLy' in design_params:
                param_data.append(['Effective Length Y (KLy)', f"{design_params['KLy']:.2f} m"])
            if 'Cb' in design_params:
                param_data.append(['Moment Gradient Factor (Cb)', f"{design_params['Cb']:.2f}"])
            
            for data_row in param_data:
                row += 1
                ws_params[f'A{row}'] = data_row[0]
                ws_params[f'B{row}'] = data_row[1]
                for col in range(1, 3):
                    cell = ws_params.cell(row=row, column=col)
                    cell.border = border
                    cell.alignment = left_align if col == 1 else center_align
        
        # Auto-size columns for all sheets
        for ws in [ws_results, ws_params]:
            try:
                for col_idx in range(1, ws.max_column + 1):
                    column_letter = get_column_letter(col_idx)
                    max_length = 0
                    for row_idx in range(1, ws.max_row + 1):
                        cell = ws.cell(row=row_idx, column=col_idx)
                        try:
                            if cell.value:
                                max_length = max(max_length, len(str(cell.value)))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 60)
                    ws.column_dimensions[column_letter].width = adjusted_width
            except:
                ws.column_dimensions['A'].width = 40
                ws.column_dimensions['B'].width = 30
    
    # Save to buffer
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ==================== PROFESSIONAL ENHANCED CSS ====================
st.markdown("""
<style>
    /* Import Professional Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styling */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Enhanced Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: white;
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        padding: 0 30px;
        background: #f8f9fa;
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #e9ecef;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-color: #667eea;
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Professional Headers */
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 2rem 0;
        letter-spacing: -1px;
    }
    
    .section-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2c3e50;
        margin: 2rem 0 1.5rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 3px solid #667eea;
        position: relative;
    }
    
    .section-header::after {
        content: '';
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 100px;
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2);
    }
    
    /* Enhanced Card Designs */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px rgba(0,0,0,0.12);
    }
    
    .evaluation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
    }
    
    .evaluation-card h3 {
        color: white;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    .critical-lengths-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 6px 12px rgba(245, 87, 108, 0.3);
    }
    
    .design-summary {
        background: white;
        border: 3px solid #4caf50;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 8px rgba(76, 175, 80, 0.2);
    }
    
    /* Enhanced Status Boxes */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 5px solid #2196f3;
        padding: 1.25rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .success-box {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border-left: 5px solid #4caf50;
        padding: 1.25rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-left: 5px solid #ff9800;
        padding: 1.25rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .error-box {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-left: 5px solid #f44336;
        padding: 1.25rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* AISC Equation Styling */
    .aisc-equation {
        background: linear-gradient(135deg, #e7f3ff 0%, #d0e8ff 100%);
        border-left: 5px solid #2196f3;
        padding: 1.25rem;
        margin: 1rem 0;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        box-shadow: 0 2px 4px rgba(33, 150, 243, 0.1);
    }
    
    /* Enhanced Calculation Note */
    .calculation-note {
        background: #2c3e50;
        color: #ecf0f1;
        border: 2px solid #34495e;
        padding: 1.5rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        margin: 1rem 0;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        max-height: 600px;
        overflow-y: auto;
    }
    
    /* Professional Data Tables */
    .dataframe {
        font-size: 14px !important;
        border-radius: 10px;
        overflow: hidden;
    }
    
    .dataframe thead tr th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        font-weight: 600;
        padding: 15px 12px !important;
        text-align: center;
        font-size: 15px;
    }
    
    .dataframe tbody tr {
        transition: background-color 0.2s ease;
    }
    
    .dataframe tbody tr:hover {
        background-color: #f5f7fa !important;
    }
    
    .dataframe tbody tr td {
        padding: 12px !important;
        border-bottom: 1px solid #e9ecef;
        text-align: center;
    }
    
    /* Enhanced Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 1rem;
        font-weight: 600;
        color: #2c3e50;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 10px;
        font-weight: 600;
        font-size: 15px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Download Buttons */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stDownloadButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(76, 175, 80, 0.4);
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
        border-right: 2px solid #e9ecef;
    }
    
    /* Input Fields */
    .stNumberInput>div>div>input,
    .stTextInput>div>div>input,
    .stSelectbox>div>div {
        border-radius: 8px;
        border: 2px solid #e9ecef;
        padding: 10px;
        font-size: 15px;
        transition: border-color 0.3s ease;
    }
    
    .stNumberInput>div>div>input:focus,
    .stTextInput>div>div>input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Slider Styling */
    .stSlider>div>div>div>div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #f8f9fa;
        border-radius: 10px;
        font-weight: 600;
        font-size: 16px;
        padding: 12px;
    }
    
    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATA PATHS ====================
file_path = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-Material.csv"

# ==================== SESSION STATE INITIALIZATION ====================
# ==================== SESSION STATE INITIALIZATION ====================
if 'selected_section' not in st.session_state:
    st.session_state.selected_section = None
if 'selected_material' not in st.session_state:
    st.session_state.selected_material = None
if 'selected_sections' not in st.session_state:
    st.session_state.selected_sections = []
if 'calculation_report' not in st.session_state:
    st.session_state.calculation_report = ""
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = None
if 'project_info' not in st.session_state:
    st.session_state.project_info = {
        'project_name': '',
        'project_no': '',
        'designer': '',
        'checker': '',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'revision': '0'
    }

# ==================== HELPER FUNCTIONS ====================
@st.cache_data
def load_data():
    """Load steel section and material databases"""
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        return df, df_mat, True
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

def safe_scalar(value):
    """Safely convert numpy array or other type to scalar float"""
    try:
        if hasattr(value, 'item'):
            return float(value.item())
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            return float(value[0]) if len(value) > 0 else 0.0
        else:
            return float(value)
    except:
        return 0.0

def safe_sqrt(value):
    """Safe square root that ensures non-negative input"""
    val = safe_scalar(value)
    return math.sqrt(abs(val)) if val >= 0 else 0.0

# ==================== AISC 360-16 DESIGN FUNCTIONS ====================
def aisc_360_16_f2_flexural_design(df, df_mat, section, material, Lb_input, Cb=1.0):
    """AISC 360-16 F2 - Lateral-Torsional Buckling Analysis"""
    try:
        Sx = safe_scalar(df.loc[section, "Sx [cm3]"])
        Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        if 'rts [cm]' in df.columns:
            rts = safe_scalar(df.loc[section, 'rts [cm]'])
        else:
            rts = ry * 1.2
        
        J = safe_scalar(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 1.0
        
        if 'ho [mm]' in df.columns:
            ho = safe_scalar(df.loc[section, 'ho [mm]']) / 10.0
        else:
            ho = safe_scalar(df.loc[section, 'd [mm]']) / 10.0
        
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        Lb = safe_scalar(Lb_input)
        Cb = safe_scalar(Cb)
        
        # AISC 360-16 Equation F2.5
        Lp = 1.76 * ry * safe_sqrt(E / Fy) / 100.0
        
        # AISC 360-16 Equation F2.6
        c = 1.0
        term1 = 1.95 * rts * E / (0.7 * Fy)
        inner_sqrt = J * c / (Sx * ho)
        term2 = safe_sqrt(inner_sqrt)
        
        ratio_term = (0.7 * Fy / E) ** 2
        geometry_term = (Sx * ho / (J * c)) ** 2
        complex_inner = 1.0 + 6.76 * ratio_term * geometry_term
        term3 = safe_sqrt(1.0 + safe_sqrt(complex_inner))
        
        Lr = term1 * term2 * term3 / 100.0
        
        Mp = Fy * Zx
        
        if Lb <= Lp:
            Case = "F2.1 - Yielding"
            Mn = Mp
        elif Lb <= Lr:
            Case = "F2.2 - Inelastic LTB"
            Lb_cm = Lb * 100.0
            Lp_cm = Lp * 100.0  
            Lr_cm = Lr * 100.0
            
            Mp_minus_Mr = Mp - 0.7 * Fy * Sx
            length_ratio = (Lb_cm - Lp_cm) / (Lr_cm - Lp_cm)
            Mn = Cb * (Mp - Mp_minus_Mr * length_ratio)
            Mn = min(Mp, Mn)
        else:
            Case = "F2.3 - Elastic LTB"
            Lb_cm = Lb * 100.0
            Lb_rts_ratio = Lb_cm / rts
            
            term_1 = (Cb * math.pi**2 * E) / (Lb_rts_ratio**2)
            term_2 = 0.078 * (J * c / (Sx * ho)) * (Lb_rts_ratio**2)
            Fcr = term_1 * safe_sqrt(1.0 + term_2)
            
            Mn = Fcr * Sx
            Mn = min(Mp, Mn)
        
        Mn_tm = Mn / 100000.0
        Mp_tm = Mp / 100000.0
        
        return {
            'Mn': Mn_tm,
            'Mp': Mp_tm,
            'Lp': Lp,
            'Lr': Lr, 
            'Case': Case,
            'Cb': Cb
        }
        
    except Exception as e:
        st.error(f"Error in AISC 360-16 F2 calculation: {str(e)}")
        return None

def aisc_360_16_e3_compression_design(df, df_mat, section, material, KLx, KLy):
    """AISC 360-16 E3 - Flexural Buckling Analysis"""
    try:
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        Ag = safe_scalar(df.loc[section, 'A [cm2]'])
        rx = safe_scalar(df.loc[section, 'rx [cm]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        KLx_scalar = safe_scalar(KLx) * 100.0
        KLy_scalar = safe_scalar(KLy) * 100.0
        
        lambda_x = KLx_scalar / rx
        lambda_y = KLy_scalar / ry
        lambda_c = max(lambda_x, lambda_y)
        
        Fe = (math.pi**2 * E) / (lambda_c**2)
        
        lambda_limit = 4.71 * safe_sqrt(E / Fy)
        
        if lambda_c <= lambda_limit:
            buckling_mode = "Inelastic"
            exponent = Fy / Fe
            Fcr = (0.658 ** exponent) * Fy
        else:
            buckling_mode = "Elastic"
            Fcr = 0.877 * Fe
        
        Pn = Fcr * Ag / 1000.0
        phi_c = 0.90
        phi_Pn = phi_c * Pn
        
        slenderness_ok = lambda_c <= 200.0
        
        return {
            'Pn': Pn,
            'phi_Pn': phi_Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_c': lambda_c,
            'lambda_limit': lambda_limit,
            'buckling_mode': buckling_mode,
            'slenderness_ok': slenderness_ok,
            'phi_c': phi_c
        }
        
    except Exception as e:
        st.error(f"Error in AISC 360-16 E3 compression analysis: {e}")
        return None

def aisc_360_16_h1_interaction(Pu, phi_Pn, Mux, phi_Mnx, Muy, phi_Mny):
    """AISC 360-16 H1 - Combined Forces Analysis"""
    try:
        Pu = safe_scalar(Pu)
        phi_Pn = safe_scalar(phi_Pn) 
        Mux = safe_scalar(Mux)
        phi_Mnx = safe_scalar(phi_Mnx)
        Muy = safe_scalar(Muy)
        phi_Mny = safe_scalar(phi_Mny)
        
        if phi_Pn <= 0.0 or phi_Mnx <= 0.0 or phi_Mny <= 0.0:
            return None
        
        Pr_Pc = Pu / phi_Pn
        Mrx_Mcx = Mux / phi_Mnx
        Mry_Mcy = Muy / phi_Mny
        
        if Pr_Pc >= 0.2:
            interaction_ratio = Pr_Pc + (8.0/9.0) * (Mrx_Mcx + Mry_Mcy)
            equation = "H1-1a"
        else:
            interaction_ratio = Pr_Pc/2.0 + (Mrx_Mcx + Mry_Mcy)
            equation = "H1-1b"
        
        design_ok = interaction_ratio <= 1.0
        safety_margin = (1.0 - interaction_ratio) if design_ok else None
        
        return {
            'interaction_ratio': interaction_ratio,
            'equation': equation,
            'design_ok': design_ok,
            'Pr_Pc': Pr_Pc,
            'Mrx_Mcx': Mrx_Mcx,
            'Mry_Mcy': Mry_Mcy,
            'safety_margin': safety_margin
        }
        
    except Exception as e:
        st.error(f"Error in AISC 360-16 H1 interaction calculation: {e}")
        return None

def create_section_preview(d, bf, tf, tw, section_name):
    """Create a mini I-beam cross-section preview for sidebar"""
    fig, ax = plt.subplots(figsize=(3, 3.5))
    
    # Convert to plotting units (scale for visualization)
    scale = 1.0
    d_s = d * scale
    bf_s = bf * scale
    tf_s = tf * scale
    tw_s = tw * scale
    
    # Center coordinates
    cx, cy = 0, 0
    
    # Draw I-beam shape
    # Top flange
    top_flange = patches.Rectangle(
        (cx - bf_s/2, cy + d_s/2 - tf_s),
        bf_s, tf_s,
        linewidth=2, edgecolor='#667eea', facecolor='#e3f2fd'
    )
    ax.add_patch(top_flange)
    
    # Bottom flange
    bottom_flange = patches.Rectangle(
        (cx - bf_s/2, cy - d_s/2),
        bf_s, tf_s,
        linewidth=2, edgecolor='#667eea', facecolor='#e3f2fd'
    )
    ax.add_patch(bottom_flange)
    
    # Web
    web = patches.Rectangle(
        (cx - tw_s/2, cy - d_s/2 + tf_s),
        tw_s, d_s - 2*tf_s,
        linewidth=2, edgecolor='#667eea', facecolor='#e3f2fd'
    )
    ax.add_patch(web)
    
    # Add dimension lines
    dim_offset = bf_s * 0.15
    arrow_props = dict(arrowstyle='<->', color='#f44336', lw=1.5)
    
    # Height dimension (d)
    ax.annotate('', xy=(bf_s/2 + dim_offset, d_s/2),
                xytext=(bf_s/2 + dim_offset, -d_s/2),
                arrowprops=arrow_props)
    ax.text(bf_s/2 + dim_offset*2, 0, f'd={d:.0f}',
            fontsize=8, color='#f44336', va='center', fontweight='bold')
    
    # Width dimension (bf)
    ax.annotate('', xy=(-bf_s/2, d_s/2 + dim_offset),
                xytext=(bf_s/2, d_s/2 + dim_offset),
                arrowprops=arrow_props)
    ax.text(0, d_s/2 + dim_offset*2.5, f'bf={bf:.0f}',
            fontsize=8, color='#f44336', ha='center', fontweight='bold')
    
    # Styling
    ax.set_xlim(-bf_s * 0.8, bf_s * 1.2)
    ax.set_ylim(-d_s * 0.7, d_s * 0.8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(section_name, fontsize=10, fontweight='bold', color='#2c3e50')
    
    plt.tight_layout()
    return fig

# ==================== ENHANCED PLOTLY CHART CONFIGURATIONS ====================
def create_enhanced_plotly_config():
    """Standard configuration for all Plotly charts with improved readability"""
    return {
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'aisc_chart',
            'height': 800,
            'width': 1200,
            'scale': 2
        }
    }

def get_enhanced_plotly_layout():
    """Standard layout settings for enhanced readability"""
    return {
        'template': 'plotly_white',
        'font': {
            'family': 'Inter, sans-serif',
            'size': 14,
            'color': '#2c3e50'
        },
        'title': {
            'font': {'size': 20, 'color': '#2c3e50', 'family': 'Inter'},
            'x': 0.5,
            'xanchor': 'center'
        },
        'xaxis': {
            'title': {'font': {'size': 16, 'color': '#34495e'}},
            'tickfont': {'size': 13},
            'gridcolor': '#ecf0f1',
            'showgrid': True,
            'zeroline': True,
            'zerolinecolor': '#bdc3c7',
            'showline': True,
            'linecolor': '#bdc3c7'
        },
        'yaxis': {
            'title': {'font': {'size': 16, 'color': '#34495e'}},
            'tickfont': {'size': 13},
            'gridcolor': '#ecf0f1',
            'showgrid': True,
            'zeroline': True,
            'zerolinecolor': '#bdc3c7',
            'showline': True,
            'linecolor': '#bdc3c7'
        },
        'margin': {'l': 80, 'r': 80, 't': 100, 'b': 80},
        'hovermode': 'closest',
        'plot_bgcolor': 'white',
        'paper_bgcolor': 'white'
    }

def generate_professional_pdf_report(df, df_mat, section, material, analysis_results, design_params):
    """Generate professional PDF report with perfect formatting - NO OVERLAP"""
    if not PDF_AVAILABLE:
        return None
    
    buffer = BytesIO()
    
    # Create document with proper margins
    doc = BaseDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=0.75*inch, 
        leftMargin=0.75*inch,
        topMargin=1.1*inch,  # Increased for header
        bottomMargin=0.9*inch,  # Increased for footer
        title="AISC 360-16 Steel Design Report"
    )
    
    # Define frame for content with proper margins
    frame = Frame(
        doc.leftMargin, 
        doc.bottomMargin, 
        doc.width, 
        doc.height - 0.3*inch,  # Account for header/footer space
        id='normal',
        topPadding=12,
        bottomPadding=12
    )
    template = PageTemplate(id='main', frames=frame, onPage=lambda c, d: None)
    doc.addPageTemplates([template])
    
    story = []
    styles = getSampleStyleSheet()
    
    # ==================== ENHANCED CUSTOM STYLES - NO OVERLAP ====================
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=rl_colors.HexColor('#667eea'),
        spaceAfter=18,
        spaceBefore=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=24
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=rl_colors.HexColor('#2c3e50'),
        spaceAfter=10,
        spaceBefore=16,
        fontName='Helvetica-Bold',
        borderWidth=0,  # Remove border to prevent overlap
        backColor=rl_colors.HexColor('#f0f3ff'),
        borderPadding=6,
        leftIndent=0,
        rightIndent=0,
        keepWithNext=True,
        leading=18
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=rl_colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold',
        keepWithNext=True,
        leading=16
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        spaceAfter=4,
        spaceBefore=2,
        alignment=TA_LEFT,
        wordWrap='CJK'  # Better word wrapping
    )
    
    # Improved equation style - no overlap
    equation_style = ParagraphStyle(
        'EquationStyle',
        parent=styles['Code'],
        fontSize=9,
        textColor=rl_colors.HexColor('#1565C0'),
        backColor=rl_colors.HexColor('#E7F3FF'),
        borderWidth=1,
        borderColor=rl_colors.HexColor('#2196F3'),
        borderPadding=8,
        leftIndent=12,
        rightIndent=12,
        spaceAfter=8,
        spaceBefore=8,
        fontName='Courier',
        leading=12,
        borderRadius=5
    )
    
    # ==================== TITLE PAGE ====================
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("AISC 360-16 STEEL DESIGN", title_style))
    story.append(Paragraph("COMPREHENSIVE CALCULATION REPORT", title_style))
    story.append(Spacer(1, 0.4*inch))
    
    # Report Info with proper table
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_data = [
        ['Report Generated:', timestamp],
        ['Section:', section],
        ['Material Grade:', material],
        ['Analysis Type:', 'Comprehensive Design Evaluation']
    ]
    
    header_table = Table(header_data, colWidths=[2.3*inch, 4.2*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (0, -1), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, rl_colors.grey),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [rl_colors.HexColor('#f5f5f5'), rl_colors.white])
    ]))
    story.append(KeepTogether(header_table))
    story.append(Spacer(1, 0.25*inch))
    
    # Get material properties
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    Fu = safe_scalar(df_mat.loc[material, "Tensile Strength (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    # ==================== MATERIAL PROPERTIES ====================
    story.append(Paragraph("1. MATERIAL PROPERTIES", heading1_style))
    story.append(Spacer(1, 6))
    
    mat_data = [
        ['Property', 'Value', 'Unit', 'Description'],
        ['Fy', f'{Fy:.1f}', 'kgf/cm²', 'Yield Strength'],
        ['Fu', f'{Fu:.1f}', 'kgf/cm²', 'Tensile Strength'],
        ['E', f'{E:.0f}', 'kgf/cm²', 'Modulus of Elasticity']
    ]
    
    mat_table = Table(mat_data, colWidths=[1.3*inch, 1.2*inch, 1.3*inch, 2.7*inch])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#f9f9f9')])
    ]))
    story.append(KeepTogether(mat_table))
    story.append(Spacer(1, 0.2*inch))
    
    # ==================== SECTION PROPERTIES ====================
    story.append(PageBreak())
    story.append(Paragraph("2. SECTION PROPERTIES", heading1_style))
    story.append(Spacer(1, 6))
    
    # Build properties table with proper column widths
    props_data = [['Property', 'Symbol', 'Value', 'Unit']]
    
    property_list = [
        ('d [mm]', 'd', 'mm'),
        ('bf [mm]', 'bf', 'mm'),
        ('tw [mm]', 'tw', 'mm'),
        ('tf [mm]', 'tf', 'mm'),
        ('A [cm2]', 'A', 'cm²'),
        ('Ix [cm4]', 'Ix', 'cm⁴'),
        ('Iy [cm4]', 'Iy', 'cm⁴'),
        ('rx [cm]', 'rx', 'cm'),
        ('ry [cm]', 'ry', 'cm'),
        ('Sx [cm3]', 'Sx', 'cm³'),
        ('Sy [cm3]', 'Sy', 'cm³'),
        ('Zx [cm3]', 'Zx', 'cm³'),
        ('Zy [cm3]', 'Zy', 'cm³'),
    ]
    
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
    
    for prop_key, symbol, unit in property_list:
        if prop_key in df.columns:
            value = safe_scalar(df.loc[section, prop_key])
            description = prop_key.split('[')[0].strip()
            formatted_value = f'{value:.2f}' if value < 1000 else f'{value:.1f}'
            props_data.append([description, symbol, formatted_value, unit])
    
    # Create table with word wrap
    props_table = Table(props_data, colWidths=[2.2*inch, 0.9*inch, 1.4*inch, 1*inch])
    props_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#f9f9f9')]),
        ('WORDWRAP', (0, 0), (-1, -1), True)
    ]))
    story.append(KeepTogether(props_table))
    story.append(Spacer(1, 0.15*inch))
    
    # Add slenderness ratios
    bf = safe_scalar(df.loc[section, 'bf [mm]'])
    tf = safe_scalar(df.loc[section, 'tf [mm]'])
    d = safe_scalar(df.loc[section, 'd [mm]'])
    tw = safe_scalar(df.loc[section, 'tw [mm]'])
    h = safe_scalar(df.loc[section, 'ho [mm]']) if 'ho [mm]' in df.columns else (d - 2*tf)
    
    slender_data = [
        ['Parameter', 'Value'],
        ['Flange Slenderness (bf/2tf)', f'{(bf/2.0)/tf:.2f}'],
        ['Web Slenderness (h/tw)', f'{h/tw:.2f}']
    ]
    
    slender_table = Table(slender_data, colWidths=[3.5*inch, 2*inch])
    slender_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#2196f3')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
    ]))
    story.append(KeepTogether(slender_table))
    
    # ==================== SECTION CLASSIFICATION ====================
    story.append(PageBreak())
    story.append(Paragraph("3. SECTION CLASSIFICATION", heading1_style))
    story.append(Spacer(1, 8))
    
    flex_class = classify_section_flexure(df, df_mat, section, material)
    comp_class = classify_section_compression(df, df_mat, section, material)
    
    if flex_class:
        story.append(Paragraph("3.1 Flexural Classification (AISC Table B4.1b)", heading2_style))
        story.append(Spacer(1, 6))
        
        # Flange - Use equation box for formulas
        story.append(Paragraph("<b>Flange (Case 10: I-shaped sections)</b>", body_style))
        story.append(Spacer(1, 4))
        
        # Use custom equation box instead of paragraph
        eq_text = f"λp = 0.38√(E/Fy) = 0.38√({E:.0f}/{Fy:.1f}) = {flex_class['flange_lambda_p']:.2f}"
        story.append(EquationBox(eq_text, doc.width))
        story.append(Spacer(1, 4))
        
        eq_text = f"λr = 1.0√(E/Fy) = 1.0√({E:.0f}/{Fy:.1f}) = {flex_class['flange_lambda_r']:.2f}"
        story.append(EquationBox(eq_text, doc.width))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph(
            f"<b>Actual λ = (bf/2)/tf = {flex_class['flange_lambda']:.2f}</b>",
            body_style
        ))
        story.append(Paragraph(
            f"<b>Classification: {flex_class['flange_class']}</b>",
            body_style
        ))
        story.append(Spacer(1, 12))
        
        # Web
        story.append(Paragraph("<b>Web (Case 15: Webs in flexure)</b>", body_style))
        story.append(Spacer(1, 4))
        
        eq_text = f"λpw = 3.76√(E/Fy) = {flex_class['web_lambda_p']:.2f}"
        story.append(EquationBox(eq_text, doc.width))
        story.append(Spacer(1, 4))
        
        eq_text = f"λrw = 5.70√(E/Fy) = {flex_class['web_lambda_r']:.2f}"
        story.append(EquationBox(eq_text, doc.width))
        story.append(Spacer(1, 6))
        
        story.append(Paragraph(
            f"<b>Actual λ = h/tw = {flex_class['web_lambda']:.2f}</b>",
            body_style
        ))
        story.append(Paragraph(
            f"<b>Classification: {flex_class['web_class']}</b>",
            body_style
        ))
        story.append(Spacer(1, 0.15*inch))
    
    if comp_class:
        story.append(Paragraph("3.2 Compression Classification (AISC Table B4.1a)", heading2_style))
        story.append(Spacer(1, 6))
        
        comp_summary = [
            ['Element', 'λ', 'λr', 'Status'],
            ['Flange', f'{comp_class["flange_lambda"]:.2f}', 
             f'{comp_class["flange_lambda_r"]:.2f}', 
             'Slender' if comp_class['flange_slender'] else 'Non-slender'],
            ['Web', f'{comp_class["web_lambda"]:.2f}',
             f'{comp_class["web_lambda_r"]:.2f}',
             'Slender' if comp_class['web_slender'] else 'Non-slender'],
        ]
        
        comp_table = Table(comp_summary, colWidths=[1.5*inch, 1.3*inch, 1.3*inch, 1.4*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ]))
        story.append(KeepTogether(comp_table))
        
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"<b>Overall: {comp_class['overall_class']}</b>",
            body_style
        ))
    
    # ==================== DESIGN ANALYSIS ====================
    if analysis_results:
        story.append(PageBreak())
        story.append(Paragraph("4. DESIGN ANALYSIS", heading1_style))
        story.append(Spacer(1, 10))
        
        # FLEXURAL ANALYSIS
        if 'flexural' in analysis_results:
            story.append(Paragraph("4.1 Flexural Design (AISC Chapter F2)", heading2_style))
            story.append(Spacer(1, 6))
            
            flex = analysis_results['flexural']
            Lb = design_params.get('Lb', 0)
            Cb = design_params.get('Cb', 1.0)
            
            Sx = safe_scalar(df.loc[section, "Sx [cm3]"])
            Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
            ry = safe_scalar(df.loc[section, 'ry [cm]'])
            
            # Step 1
            story.append(Paragraph("<b>Step 1: Plastic Moment</b>", body_style))
            story.append(Spacer(1, 4))
            
            eq_text = f"Mp = Fy × Zx = {Fy:.1f} × {Zx:.2f} = {flex['Mp']:.2f} t·m"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 2
            story.append(Paragraph("<b>Step 2: Limiting Lengths</b>", body_style))
            story.append(Spacer(1, 4))
            
            eq_text = f"Lp = 1.76 × ry × √(E/Fy) = 1.76 × {ry:.2f} × √({E:.0f}/{Fy:.1f}) = {flex['Lp']:.3f} m"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 4))
            
            eq_text = f"Lr = {flex['Lr']:.3f} m (AISC Eq. F2-6)"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 3
            story.append(Paragraph(f"<b>Step 3: Nominal Moment (Lb = {Lb:.2f} m)</b>", body_style))
            story.append(Spacer(1, 4))
            
            if Lb <= flex['Lp']:
                story.append(Paragraph(
                    f"Lb ({Lb:.2f}m) ≤ Lp ({flex['Lp']:.3f}m) → <b>Yielding (F2.1)</b>",
                    body_style
                ))
                eq_text = f"Mn = Mp = {flex['Mn']:.2f} t·m"
            elif Lb <= flex['Lr']:
                story.append(Paragraph(
                    f"Lp < Lb ({Lb:.2f}m) ≤ Lr → <b>Inelastic LTB (F2.2)</b>",
                    body_style
                ))
                eq_text = f"Mn = Cb[Mp - ...] = {flex['Mn']:.2f} t·m"
            else:
                story.append(Paragraph(
                    f"Lb ({Lb:.2f}m) > Lr → <b>Elastic LTB (F2.3)</b>",
                    body_style
                ))
                eq_text = f"Mn = Fcr × Sx = {flex['Mn']:.2f} t·m"
            
            story.append(Spacer(1, 4))
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 4
            story.append(Paragraph("<b>Step 4: Design Strength</b>", body_style))
            story.append(Spacer(1, 4))
            
            eq_text = f"φMn = 0.90 × {flex['Mn']:.2f} = {flex['phi_Mn']:.2f} t·m"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 12))
            
            # Summary table
            flex_summary = [
                ['Parameter', 'Value'],
                ['Design Capacity (φMn)', f"{flex['phi_Mn']:.2f} t·m"],
                ['Nominal Moment (Mn)', f"{flex['Mn']:.2f} t·m"],
                ['Plastic Moment (Mp)', f"{flex['Mp']:.2f} t·m"],
                ['Design Case', flex['case']],
                ['Design Zone', flex['zone']],
                ['Utilization', f"{flex['ratio']:.3f}"],
                ['Status', '✓ ADEQUATE' if flex['adequate'] else '✗ INADEQUATE']
            ]
            
            flex_table = Table(flex_summary, colWidths=[3*inch, 2.5*inch])
            flex_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#4caf50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ]))
            story.append(KeepTogether(flex_table))
            
            # Add chart
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph("<b>Flexural Capacity Curve:</b>", body_style))
            story.append(Spacer(1, 6))
            
            # Generate chart with better formatting
            fig, ax = plt.subplots(figsize=(6.5, 4))
            Lb_points = np.linspace(0.1, 15, 200)
            Mn_points = []
            
            for lb in Lb_points:
                r = aisc_360_16_f2_flexural_design(df, df_mat, section, material, lb, Cb)
                Mn_points.append(0.9 * r['Mn'] if r else 0)
            
            ax.plot(Lb_points, Mn_points, 'b-', linewidth=2.5, label='φM$_n$')
            ax.axvline(x=flex['Lp'], color='g', linestyle='--', linewidth=1.5, 
                      label=f'L$_p$ = {flex["Lp"]:.2f}m')
            ax.axvline(x=flex['Lr'], color='orange', linestyle='--', linewidth=1.5,
                      label=f'L$_r$ = {flex["Lr"]:.2f}m')
            ax.plot([Lb], [flex['phi_Mn']], 'r*', markersize=15, 
                   label='Design Point', zorder=5)
            
            ax.set_xlabel('Unbraced Length, L$_b$ (m)', fontsize=10, fontweight='bold')
            ax.set_ylabel('Design Moment, φM$_n$ (t·m)', fontsize=10, fontweight='bold')
            ax.set_title(f'Flexural Capacity - {section}', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.7)
            ax.legend(loc='best', framealpha=0.9, fontsize=8)
            ax.tick_params(labelsize=8)
            
            # Save with proper margins
            img_buffer = BytesIO()
            plt.tight_layout(pad=0.5)
            plt.savefig(img_buffer, format='png', dpi=120, bbox_inches='tight')
            plt.close()
            img_buffer.seek(0)
            
            img = Image(img_buffer, width=5.5*inch, height=3.4*inch)
            story.append(img)
        
        # COMPRESSION ANALYSIS
        if 'compression' in analysis_results:
            story.append(PageBreak())
            story.append(Paragraph("4.2 Compression Design (AISC Chapter E3)", heading2_style))
            story.append(Spacer(1, 6))
            
            comp = analysis_results['compression']
            KL = design_params.get('KL', 0)
            
            Ag = safe_scalar(df.loc[section, 'A [cm2]'])
            rx = safe_scalar(df.loc[section, 'rx [cm]'])
            ry = safe_scalar(df.loc[section, 'ry [cm]'])
            
            # Step 1
            story.append(Paragraph("<b>Step 1: Slenderness Ratio</b>", body_style))
            story.append(Spacer(1, 4))
            
            KL_cm = KL * 100
            lambda_x = KL_cm / rx
            lambda_y = KL_cm / ry
            lambda_c = max(lambda_x, lambda_y)
            
            eq_text = f"λc = max(KL/rx, KL/ry) = max({lambda_x:.1f}, {lambda_y:.1f}) = {lambda_c:.1f}"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 2
            story.append(Paragraph("<b>Step 2: Elastic Buckling Stress</b>", body_style))
            story.append(Spacer(1, 4))
            
            Fe = (math.pi**2 * E) / (lambda_c**2)
            eq_text = f"Fe = π²E/(λc)² = π² × {E:.0f} / {lambda_c:.1f}² = {Fe:.1f} kgf/cm²"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 3
            story.append(Paragraph("<b>Step 3: Critical Stress</b>", body_style))
            story.append(Spacer(1, 4))
            
            lambda_limit = 4.71 * safe_sqrt(E / Fy)
            
            if lambda_c <= lambda_limit:
                story.append(Paragraph(
                    f"λc ({lambda_c:.1f}) ≤ {lambda_limit:.1f} → <b>Inelastic (E3-2)</b>",
                    body_style
                ))
                exponent = Fy / Fe
                Fcr = (0.658 ** exponent) * Fy
                eq_text = f"Fcr = [0.658^(Fy/Fe)] × Fy = {Fcr:.1f} kgf/cm²"
            else:
                story.append(Paragraph(
                    f"λc ({lambda_c:.1f}) > {lambda_limit:.1f} → <b>Elastic (E3-3)</b>",
                    body_style
                ))
                Fcr = 0.877 * Fe
                eq_text = f"Fcr = 0.877 × Fe = {Fcr:.1f} kgf/cm²"
            
            story.append(Spacer(1, 4))
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 10))
            
            # Step 4
            story.append(Paragraph("<b>Step 4: Design Strength</b>", body_style))
            story.append(Spacer(1, 4))
            
            Pn = Fcr * Ag / 1000
            eq_text = f"Pn = Fcr × Ag = {Fcr:.1f} × {Ag:.2f} / 1000 = {Pn:.2f} tons"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 4))
            
            eq_text = f"φPn = 0.90 × {Pn:.2f} = {comp['phi_Pn']:.2f} tons"
            story.append(EquationBox(eq_text, doc.width))
            story.append(Spacer(1, 12))
            
            # Summary table
            comp_summary = [
                ['Parameter', 'Value'],
                ['Design Strength (φPn)', f"{comp['phi_Pn']:.2f} tons"],
                ['Nominal Strength (Pn)', f"{comp['Pn']:.2f} tons"],
                ['Critical Stress (Fcr)', f"{comp['Fcr']:.1f} kgf/cm²"],
                ['Slenderness (λc)', f"{comp['lambda_c']:.1f}"],
                ['Buckling Mode', comp['mode']],
                ['Utilization', f"{comp['ratio']:.3f}"],
                ['Status', '✓ ADEQUATE' if comp['adequate'] else '✗ INADEQUATE']
            ]
            
            comp_table = Table(comp_summary, colWidths=[3*inch, 2.5*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#2196f3')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.whitesmoke),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ]))
            story.append(KeepTogether(comp_table))
            
            # Add chart
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph("<b>Column Capacity Curve:</b>", body_style))
            story.append(Spacer(1, 6))
            
            fig, ax = plt.subplots(figsize=(6.5, 4))
            lambda_points = np.linspace(1, 250, 250)
            Pn_points = []
            
            for lc in lambda_points:
                Fe_temp = (math.pi**2 * E) / (lc**2)
                if lc <= lambda_limit:
                    Fcr_temp = (0.658**(Fy/Fe_temp)) * Fy
                else:
                    Fcr_temp = 0.877 * Fe_temp
                Pn_points.append(0.9 * Fcr_temp * Ag / 1000.0)
            
            ax.plot(lambda_points, Pn_points, 'b-', linewidth=2.5, label='φP$_n$')
            ax.axvline(x=lambda_limit, color='orange', linestyle='--', linewidth=1.5,
                      label=f'λ limit = {lambda_limit:.1f}')
            ax.plot([comp['lambda_c']], [comp['phi_Pn']], 'r*', markersize=15,
                   label='Design Point', zorder=5)
            
            if 'Pu' in design_params and design_params['Pu'] > 0:
                ax.axhline(y=design_params['Pu'], color='g', linestyle='--',
                          linewidth=1.5, label=f'P$_u$ = {design_params["Pu"]:.1f} tons')
            
            ax.set_xlabel('Slenderness Ratio (KL/r)', fontsize=10, fontweight='bold')
            ax.set_ylabel('Design Strength, φP$_n$ (tons)', fontsize=10, fontweight='bold')
            ax.set_title(f'Column Capacity - {section}', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle=':', linewidth=0.7)
            ax.legend(loc='best', framealpha=0.9, fontsize=8)
            ax.tick_params(labelsize=8)
            
            img_buffer = BytesIO()
            plt.tight_layout(pad=0.5)
            plt.savefig(img_buffer, format='png', dpi=120, bbox_inches='tight')
            plt.close()
            img_buffer.seek(0)
            
            img = Image(img_buffer, width=5.5*inch, height=3.4*inch)
            story.append(img)
    
    # Footer
    story.append(PageBreak())
    story.append(Spacer(1, 2*inch))
    footer_text = """
    <para align=center>
    <b>AISC 360-16 Steel Design Professional v7.0</b><br/>
    All calculations comply with AISC 360-16 specifications.<br/>
    <br/>
    © 2024 - Professional Structural Engineering Tool
    </para>
    """
    story.append(Paragraph(footer_text, body_style))
    
    # Build PDF with custom canvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer


# ==================== ENHANCED EXCEL EXPORT WITH DETAILED CALCULATIONS ====================
def generate_enhanced_excel_report(df, df_mat, section, material, analysis_results, design_params):
    """Generate comprehensive Excel calculation report with detailed AISC equations and charts"""
    if not EXCEL_AVAILABLE:
        return None
    
    buffer = BytesIO()
    wb = Workbook()
    
    # ==================== DEFINE ENHANCED STYLES ====================
    # Title styles
    title_font = Font(bold=True, size=20, color="667EEA")
    title_fill = PatternFill(start_color="F0F3FF", end_color="F0F3FF", fill_type="solid")
    
    # Header styles
    header_fill = PatternFill(start_color="667EEA", end_color="667EEA", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    
    # Subheader styles
    subheader_fill = PatternFill(start_color="2196F3", end_color="2196F3", fill_type="solid")
    subheader_font = Font(bold=True, color="FFFFFF", size=11)
    
    # Section header styles
    section_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
    section_font = Font(bold=True, size=14, color="2c3e50")
    
    # Equation styles
    equation_fill = PatternFill(start_color="E7F3FF", end_color="E7F3FF", fill_type="solid")
    equation_font = Font(italic=True, size=10, color="1565C0")
    
    # Calculation styles
    calc_fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
    
    # Result styles
    result_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    result_font = Font(bold=True, color="2E7D32", size=11)
    
    # Status styles
    adequate_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    adequate_font = Font(bold=True, color="2E7D32")
    inadequate_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    inadequate_font = Font(bold=True, color="C62828")
    
    # Classification styles
    compact_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    compact_font = Font(bold=True, color="2E7D32")
    noncompact_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    noncompact_font = Font(bold=True, color="F57C00")
    slender_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
    slender_font = Font(bold=True, color="C62828")
    
    # Alignment
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    right_align = Alignment(horizontal="right", vertical="center")
    
    # Borders
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    thick_border = Border(
        left=Side(style='medium'),
        right=Side(style='medium'),
        top=Side(style='medium'),
        bottom=Side(style='medium')
    )
    
    # ==================== SHEET 1: COVER & SUMMARY ====================
    ws_cover = wb.active
    ws_cover.title = "Cover & Summary"
    
    # Title
    ws_cover['A1'] = "AISC 360-16 STEEL DESIGN"
    ws_cover['A1'].font = title_font
    ws_cover['A1'].fill = title_fill
    ws_cover['A1'].alignment = center_align
    ws_cover.merge_cells('A1:F1')
    ws_cover.row_dimensions[1].height = 30
    
    ws_cover['A2'] = "COMPREHENSIVE CALCULATION REPORT"
    ws_cover['A2'].font = Font(bold=True, size=16, color="764ba2")
    ws_cover['A2'].fill = title_fill
    ws_cover['A2'].alignment = center_align
    ws_cover.merge_cells('A2:F2')
    ws_cover.row_dimensions[2].height = 25
    
    # Report information
    row = 4
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info_data = [
        ['Report Generated:', timestamp],
        ['Section:', section],
        ['Material Grade:', material],
        ['Analysis Type:', 'Comprehensive Design Evaluation'],
    ]
    
    for label, value in info_data:
        ws_cover[f'A{row}'] = label
        ws_cover[f'A{row}'].font = Font(bold=True, size=11)
        ws_cover[f'A{row}'].fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
        ws_cover[f'A{row}'].border = thin_border
        ws_cover[f'B{row}'] = value
        ws_cover[f'B{row}'].border = thin_border
        ws_cover.merge_cells(f'B{row}:D{row}')
        row += 1
    
    # Material Properties Summary
    row += 2
    ws_cover[f'A{row}'] = "MATERIAL PROPERTIES"
    ws_cover[f'A{row}'].font = section_font
    ws_cover[f'A{row}'].fill = section_fill
    ws_cover[f'A{row}'].alignment = center_align
    ws_cover.merge_cells(f'A{row}:D{row}')
    
    row += 1
    mat_headers = ['Property', 'Value', 'Unit', 'Description']
    for col, header in enumerate(mat_headers, start=1):
        cell = ws_cover.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    Fu = safe_scalar(df_mat.loc[material, "Tensile Strength (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    mat_data = [
        ['Fy', f'{Fy:.1f}', 'kgf/cm²', 'Yield Strength'],
        ['Fu', f'{Fu:.1f}', 'kgf/cm²', 'Tensile Strength'],
        ['E', f'{E:.0f}', 'kgf/cm²', 'Modulus of Elasticity']
    ]
    
    for mat_row in mat_data:
        row += 1
        for col, value in enumerate(mat_row, start=1):
            cell = ws_cover.cell(row=row, column=col)
            cell.value = value
            cell.border = thin_border
            cell.alignment = center_align if col > 1 else left_align
    
    # Design Parameters
    if design_params:
        row += 2
        ws_cover[f'A{row}'] = "DESIGN PARAMETERS"
        ws_cover[f'A{row}'].font = section_font
        ws_cover[f'A{row}'].fill = section_fill
        ws_cover[f'A{row}'].alignment = center_align
        ws_cover.merge_cells(f'A{row}:C{row}')
        
        row += 1
        param_headers = ['Parameter', 'Value', 'Unit']
        for col, header in enumerate(param_headers, start=1):
            cell = ws_cover.cell(row=row, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border
        
        param_data = []
        if 'Mu' in design_params:
            param_data.append(['Applied Moment (Mu)', f"{design_params['Mu']:.2f}", 't·m'])
        if 'Pu' in design_params:
            param_data.append(['Applied Axial Load (Pu)', f"{design_params['Pu']:.2f}", 'tons'])
        if 'Lb' in design_params:
            param_data.append(['Unbraced Length (Lb)', f"{design_params['Lb']:.2f}", 'm'])
        if 'KL' in design_params:
            param_data.append(['Effective Length (KL)', f"{design_params['KL']:.2f}", 'm'])
        if 'Cb' in design_params:
            param_data.append(['Moment Gradient Factor (Cb)', f"{design_params['Cb']:.2f}", ''])
        
        for data_row in param_data:
            row += 1
            for col, value in enumerate(data_row, start=1):
                cell = ws_cover.cell(row=row, column=col)
                cell.value = value
                cell.border = thin_border
                cell.alignment = center_align if col > 1 else left_align
    
    # Overall Status
    if analysis_results:
        row += 2
        ws_cover[f'A{row}'] = "DESIGN STATUS"
        ws_cover[f'A{row}'].font = section_font
        ws_cover[f'A{row}'].fill = section_fill
        ws_cover[f'A{row}'].alignment = center_align
        ws_cover.merge_cells(f'A{row}:D{row}')
        
        row += 1
        overall_adequate = True
        status_data = []
        
        if 'flexural' in analysis_results:
            flex = analysis_results['flexural']
            status_data.append(['Flexural Check', f"{flex['ratio']:.3f}", 
                              '✓ PASS' if flex['adequate'] else '✗ FAIL'])
            overall_adequate = overall_adequate and flex['adequate']
        
        if 'compression' in analysis_results:
            comp = analysis_results['compression']
            status_data.append(['Compression Check', f"{comp['ratio']:.3f}",
                              '✓ PASS' if comp['adequate'] else '✗ FAIL'])
            overall_adequate = overall_adequate and comp['adequate']
        
        if 'interaction' in analysis_results:
            inter = analysis_results['interaction']
            status_data.append(['Interaction Check', f"{inter['interaction_ratio']:.3f}",
                              '✓ PASS' if inter['design_ok'] else '✗ FAIL'])
            overall_adequate = overall_adequate and inter['design_ok']
        
        for check_name, ratio, status in status_data:
            row += 1
            ws_cover[f'A{row}'] = check_name
            ws_cover[f'A{row}'].border = thin_border
            ws_cover[f'A{row}'].alignment = left_align
            
            ws_cover[f'B{row}'] = ratio
            ws_cover[f'B{row}'].border = thin_border
            ws_cover[f'B{row}'].alignment = center_align
            
            ws_cover[f'C{row}'] = status
            ws_cover[f'C{row}'].border = thin_border
            ws_cover[f'C{row}'].alignment = center_align
            if '✓' in status:
                ws_cover[f'C{row}'].fill = adequate_fill
                ws_cover[f'C{row}'].font = adequate_font
            else:
                ws_cover[f'C{row}'].fill = inadequate_fill
                ws_cover[f'C{row}'].font = inadequate_font
        
        row += 1
        ws_cover[f'A{row}'] = "OVERALL STATUS"
        ws_cover[f'A{row}'].font = Font(bold=True, size=12)
        ws_cover[f'A{row}'].border = thick_border
        ws_cover[f'A{row}'].alignment = center_align
        ws_cover.merge_cells(f'A{row}:B{row}')
        
        ws_cover[f'C{row}'] = '✓ ADEQUATE' if overall_adequate else '✗ INADEQUATE'
        ws_cover[f'C{row}'].border = thick_border
        ws_cover[f'C{row}'].alignment = center_align
        ws_cover[f'C{row}'].font = Font(bold=True, size=12, color="FFFFFF")
        if overall_adequate:
            ws_cover[f'C{row}'].fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
        else:
            ws_cover[f'C{row}'].fill = PatternFill(start_color="F44336", end_color="F44336", fill_type="solid")
    
    # Auto-size columns
    for col in ['A', 'B', 'C', 'D']:
        ws_cover.column_dimensions[col].width = 25
    
    # ==================== SHEET 2: COMPLETE SECTION PROPERTIES ====================
    ws_props = wb.create_sheet("Section Properties")
    
    row = 1
    ws_props['A1'] = "COMPLETE SECTION PROPERTIES"
    ws_props['A1'].font = title_font
    ws_props['A1'].fill = title_fill
    ws_props['A1'].alignment = center_align
    ws_props.merge_cells('A1:E1')
    ws_props.row_dimensions[1].height = 25
    
    row = 3
    ws_props[f'A{row}'] = "Geometric Properties"
    ws_props[f'A{row}'].font = section_font
    ws_props[f'A{row}'].fill = section_fill
    ws_props.merge_cells(f'A{row}:E{row}')
    
    row += 1
    prop_headers = ['Property Description', 'Symbol', 'Value', 'Unit', 'AISC Reference']
    for col, header in enumerate(prop_headers, start=1):
        cell = ws_props.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    
    # Comprehensive property list with AISC references
    property_definitions = [
        ('Unit Weight [kg/m]', 'w', 'Weight per unit length', 'Table 1-1'),
        ('d [mm]', 'd', 'Overall depth', 'Table 1-1'),
        ('bf [mm]', 'bf', 'Flange width', 'Table 1-1'),
        ('tw [mm]', 'tw', 'Web thickness', 'Table 1-1'),
        ('tf [mm]', 'tf', 'Flange thickness', 'Table 1-1'),
        ('r [mm]', 'r', 'Fillet radius', 'Table 1-1'),
        ('A [cm2]', 'A', 'Cross-sectional area', 'Table 1-1'),
        ('Ix [cm4]', 'Ix', 'Moment of inertia, X-axis', 'Table 1-1'),
        ('Iy [cm4]', 'Iy', 'Moment of inertia, Y-axis', 'Table 1-1'),
        ('rx [cm]', 'rx', 'Radius of gyration, X-axis', 'Table 1-1'),
        ('ry [cm]', 'ry', 'Radius of gyration, Y-axis', 'Table 1-1'),
        ('Sx [cm3]', 'Sx', 'Elastic section modulus, X-axis', 'Table 1-1'),
        ('Sy [cm3]', 'Sy', 'Elastic section modulus, Y-axis', 'Table 1-1'),
        ('Zx [cm3]', 'Zx', 'Plastic section modulus, X-axis', 'Table 1-1'),
        ('Zy [cm3]', 'Zy', 'Plastic section modulus, Y-axis', 'Table 1-1'),
        ('ho [mm]', 'ho', 'Distance between flange centroids', 'Table 1-1'),
        ('j [cm4]', 'J', 'Torsional constant', 'Table 1-1'),
        ('cw [10^6 cm6]', 'Cw', 'Warping constant', 'Table 1-1'),
        ('rts [cm6]', 'rts', 'Effective radius for LTB', 'Eq. F2-7'),
    ]
    
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
    
    for prop_key, symbol, description, reference in property_definitions:
        # Handle weight column name variation
        check_key = weight_col if prop_key == 'Unit Weight [kg/m]' else prop_key
        
        if check_key in df.columns:
            row += 1
            value = safe_scalar(df.loc[section, check_key])
            unit = check_key.split('[')[1].replace(']', '') if '[' in check_key else ''
            
            ws_props[f'A{row}'] = description
            ws_props[f'B{row}'] = symbol
            ws_props[f'C{row}'] = f'{value:.3f}' if value < 100 else f'{value:.2f}'
            ws_props[f'D{row}'] = unit
            ws_props[f'E{row}'] = reference
            
            for col in range(1, 6):
                cell = ws_props.cell(row=row, column=col)
                cell.border = thin_border
                cell.alignment = center_align if col > 1 else left_align
    
    # Add calculated slenderness ratios
    row += 2
    ws_props[f'A{row}'] = "Calculated Slenderness Ratios"
    ws_props[f'A{row}'].font = section_font
    ws_props[f'A{row}'].fill = section_fill
    ws_props.merge_cells(f'A{row}:E{row}')
    
    row += 1
    for col, header in enumerate(prop_headers, start=1):
        cell = ws_props.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    
    bf = safe_scalar(df.loc[section, 'bf [mm]'])
    tf = safe_scalar(df.loc[section, 'tf [mm]'])
    d = safe_scalar(df.loc[section, 'd [mm]'])
    tw = safe_scalar(df.loc[section, 'tw [mm]'])
    
    if 'ho [mm]' in df.columns:
        h = safe_scalar(df.loc[section, 'ho [mm]'])
    else:
        h = d - 2 * tf
    
    flange_slenderness = (bf / 2.0) / tf
    web_slenderness = h / tw
    
    slenderness_data = [
        ['Flange slenderness', 'bf/2tf', f'{flange_slenderness:.2f}', '', 'Table B4.1'],
        ['Web slenderness', 'h/tw', f'{web_slenderness:.2f}', '', 'Table B4.1']
    ]
    
    for data_row in slenderness_data:
        row += 1
        for col, value in enumerate(data_row, start=1):
            cell = ws_props.cell(row=row, column=col)
            cell.value = value
            cell.border = thin_border
            cell.alignment = center_align if col > 1 else left_align
    
    # Auto-size columns
    for col in ['A', 'B', 'C', 'D', 'E']:
        ws_props.column_dimensions[col].width = 25
    
    # ==================== SHEET 3: SECTION CLASSIFICATION ====================
    ws_class = wb.create_sheet("Section Classification")
    
    row = 1
    ws_class['A1'] = "SECTION CLASSIFICATION PER AISC 360-16"
    ws_class['A1'].font = title_font
    ws_class['A1'].fill = title_fill
    ws_class['A1'].alignment = center_align
    ws_class.merge_cells('A1:F1')
    ws_class.row_dimensions[1].height = 25
    
    # Get classifications
    flex_class = classify_section_flexure(df, df_mat, section, material)
    comp_class = classify_section_compression(df, df_mat, section, material)
    
    if flex_class:
        row = 3
        ws_class[f'A{row}'] = "FLEXURAL MEMBER CLASSIFICATION (Table B4.1b)"
        ws_class[f'A{row}'].font = section_font
        ws_class[f'A{row}'].fill = section_fill
        ws_class.merge_cells(f'A{row}:F{row}')
        
        # Flange Classification
        row += 2
        ws_class[f'A{row}'] = "FLANGE CLASSIFICATION"
        ws_class[f'A{row}'].font = Font(bold=True, size=11, color="2c3e50")
        ws_class.merge_cells(f'A{row}:F{row}')
        
        row += 1
        ws_class[f'A{row}'] = "Case 10: Flanges of I-shaped sections in flexure"
        ws_class[f'A{row}'].font = Font(italic=True, size=10)
        ws_class.merge_cells(f'A{row}:F{row}')
        
        row += 2
        flange_data = [
            ['Parameter', 'Equation', 'Value', ''],
            ['λ (Actual)', f'(bf/2)/tf = ({bf:.1f}/2)/{tf:.1f}', f'{flex_class["flange_lambda"]:.2f}', ''],
            ['λp (Compact limit)', f'0.38√(E/Fy) = 0.38√({E:.0f}/{Fy:.1f})', f'{flex_class["flange_lambda_p"]:.2f}', 'Eq. B4-1a'],
            ['λr (Non-compact limit)', f'1.0√(E/Fy) = 1.0√({E:.0f}/{Fy:.1f})', f'{flex_class["flange_lambda_r"]:.2f}', 'Eq. B4-1b'],
        ]
        
        for data_row in flange_data:
            row += 1
            ws_class[f'A{row}'] = data_row[0]
            ws_class[f'A{row}'].font = Font(bold=True) if 'Parameter' in data_row[0] else Font()
            ws_class[f'A{row}'].border = thin_border
            ws_class[f'A{row}'].alignment = left_align
            
            ws_class.merge_cells(f'B{row}:C{row}')
            ws_class[f'B{row}'] = data_row[1]
            ws_class[f'B{row}'].border = thin_border
            ws_class[f'B{row}'].alignment = left_align
            if 'Eq.' in data_row[0] or 'λp' in data_row[0] or 'λr' in data_row[0]:
                ws_class[f'B{row}'].fill = equation_fill
            
            ws_class[f'D{row}'] = data_row[2]
            ws_class[f'D{row}'].border = thin_border
            ws_class[f'D{row}'].alignment = center_align
            
            ws_class[f'E{row}'] = data_row[3]
            ws_class[f'E{row}'].border = thin_border
            ws_class[f'E{row}'].alignment = center_align
            ws_class[f'E{row}'].font = Font(italic=True, size=9)
        
        row += 1
        ws_class[f'A{row}'] = "CLASSIFICATION:"
        ws_class[f'A{row}'].font = Font(bold=True, size=11)
        ws_class[f'A{row}'].border = thin_border
        
        ws_class.merge_cells(f'B{row}:D{row}')
        ws_class[f'B{row}'] = flex_class['flange_class'].upper()
        ws_class[f'B{row}'].border = thin_border
        ws_class[f'B{row}'].alignment = center_align
        
        if flex_class['flange_class'] == 'Compact':
            ws_class[f'B{row}'].fill = compact_fill
            ws_class[f'B{row}'].font = compact_font
        elif flex_class['flange_class'] == 'Non-compact':
            ws_class[f'B{row}'].fill = noncompact_fill
            ws_class[f'B{row}'].font = noncompact_font
        else:
            ws_class[f'B{row}'].fill = slender_fill
            ws_class[f'B{row}'].font = slender_font
        
        # Web Classification
        row += 3
        ws_class[f'A{row}'] = "WEB CLASSIFICATION"
        ws_class[f'A{row}'].font = Font(bold=True, size=11, color="2c3e50")
        ws_class.merge_cells(f'A{row}:F{row}')
        
        row += 1
        ws_class[f'A{row}'] = "Case 15: Webs of doubly symmetric I-shaped members in flexure"
        ws_class[f'A{row}'].font = Font(italic=True, size=10)
        ws_class.merge_cells(f'A{row}:F{row}')
        
        row += 2
        web_data = [
            ['Parameter', 'Equation', 'Value', ''],
            ['λ (Actual)', f'h/tw = {h:.1f}/{tw:.1f}', f'{flex_class["web_lambda"]:.2f}', ''],
            ['λpw (Compact limit)', f'3.76√(E/Fy) = 3.76√({E:.0f}/{Fy:.1f})', f'{flex_class["web_lambda_p"]:.2f}', 'Eq. B4-1a'],
            ['λrw (Non-compact limit)', f'5.70√(E/Fy) = 5.70√({E:.0f}/{Fy:.1f})', f'{flex_class["web_lambda_r"]:.2f}', 'Eq. B4-1b'],
        ]
        
        for data_row in web_data:
            row += 1
            ws_class[f'A{row}'] = data_row[0]
            ws_class[f'A{row}'].font = Font(bold=True) if 'Parameter' in data_row[0] else Font()
            ws_class[f'A{row}'].border = thin_border
            ws_class[f'A{row}'].alignment = left_align
            
            ws_class.merge_cells(f'B{row}:C{row}')
            ws_class[f'B{row}'] = data_row[1]
            ws_class[f'B{row}'].border = thin_border
            ws_class[f'B{row}'].alignment = left_align
            if 'Eq.' in data_row[0] or 'λp' in data_row[0] or 'λr' in data_row[0]:
                ws_class[f'B{row}'].fill = equation_fill
            
            ws_class[f'D{row}'] = data_row[2]
            ws_class[f'D{row}'].border = thin_border
            ws_class[f'D{row}'].alignment = center_align
            
            ws_class[f'E{row}'] = data_row[3]
            ws_class[f'E{row}'].border = thin_border
            ws_class[f'E{row}'].alignment = center_align
            ws_class[f'E{row}'].font = Font(italic=True, size=9)
        
        row += 1
        ws_class[f'A{row}'] = "CLASSIFICATION:"
        ws_class[f'A{row}'].font = Font(bold=True, size=11)
        ws_class[f'A{row}'].border = thin_border
        
        ws_class.merge_cells(f'B{row}:D{row}')
        ws_class[f'B{row}'] = flex_class['web_class'].upper()
        ws_class[f'B{row}'].border = thin_border
        ws_class[f'B{row}'].alignment = center_align
        
        if flex_class['web_class'] == 'Compact':
            ws_class[f'B{row}'].fill = compact_fill
            ws_class[f'B{row}'].font = compact_font
        elif flex_class['web_class'] == 'Non-compact':
            ws_class[f'B{row}'].fill = noncompact_fill
            ws_class[f'B{row}'].font = noncompact_font
        else:
            ws_class[f'B{row}'].fill = slender_fill
            ws_class[f'B{row}'].font = slender_font
    
    if comp_class:
        row += 4
        ws_class[f'A{row}'] = "COMPRESSION MEMBER CLASSIFICATION (Table B4.1a)"
        ws_class[f'A{row}'].font = section_font
        ws_class[f'A{row}'].fill = section_fill
        ws_class.merge_cells(f'A{row}:F{row}')
        
        row += 2
        comp_data = [
            ['Element', 'Case', 'λ (Actual)', 'λr (Limit)', 'Status'],
            ['Flange', 'Case 1: Flanges of I-shaped sections', f'{comp_class["flange_lambda"]:.2f}', 
             f'{comp_class["flange_lambda_r"]:.2f}', 'Slender' if comp_class['flange_slender'] else 'Non-slender'],
            ['Web', 'Case 5: Webs of doubly symmetric I-sections', f'{comp_class["web_lambda"]:.2f}',
             f'{comp_class["web_lambda_r"]:.2f}', 'Slender' if comp_class['web_slender'] else 'Non-slender'],
        ]
        
        for data_row in comp_data:
            row += 1
            for col, value in enumerate(data_row, start=1):
                cell = ws_class.cell(row=row, column=col)
                cell.value = value
                cell.border = thin_border
                cell.alignment = center_align if col > 2 else left_align
                
                if row > (len(comp_data) + row - len(comp_data)) and col == 1:
                    cell.font = Font(bold=True)
                elif 'Parameter' in str(value) or 'Element' in str(value):
                    cell.font = header_font
                    cell.fill = header_fill
                elif col == 5 and 'Slender' in str(value):
                    cell.fill = slender_fill
                    cell.font = slender_font
                elif col == 5 and 'Non-slender' in str(value):
                    cell.fill = compact_fill
                    cell.font = compact_font
        
        row += 1
        ws_class[f'A{row}'] = "OVERALL CLASSIFICATION:"
        ws_class[f'A{row}'].font = Font(bold=True, size=11)
        ws_class[f'A{row}'].border = thick_border
        ws_class.merge_cells(f'A{row}:C{row}')
        
        ws_class.merge_cells(f'D{row}:E{row}')
        ws_class[f'D{row}'] = comp_class['overall_class'].upper()
        ws_class[f'D{row}'].border = thick_border
        ws_class[f'D{row}'].alignment = center_align
        
        if comp_class['overall_class'] == 'Non-slender':
            ws_class[f'D{row}'].fill = compact_fill
            ws_class[f'D{row}'].font = compact_font
        else:
            ws_class[f'D{row}'].fill = slender_fill
            ws_class[f'D{row}'].font = slender_font
        
        if comp_class['overall_class'] == 'Slender':
            row += 1
            ws_class[f'A{row}'] = f"Limiting Element: {comp_class['limiting_element']}"
            ws_class[f'A{row}'].font = Font(italic=True, color="C62828")
            ws_class.merge_cells(f'A{row}:E{row}')
    
    # Auto-size columns
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws_class.column_dimensions[col].width = 20
    ws_class.column_dimensions['B'].width = 35
    
    # ==================== SHEET 4: FLEXURAL ANALYSIS ====================
    if analysis_results and 'flexural' in analysis_results:
        ws_flex = wb.create_sheet("Flexural Analysis")
        
        row = 1
        ws_flex['A1'] = "AISC 360-16 CHAPTER F2: FLEXURAL DESIGN"
        ws_flex['A1'].font = title_font
        ws_flex['A1'].fill = title_fill
        ws_flex['A1'].alignment = center_align
        ws_flex.merge_cells('A1:E1')
        ws_flex.row_dimensions[1].height = 25
        
        flex = analysis_results['flexural']
        Lb = design_params.get('Lb', 0)
        Cb = design_params.get('Cb', 1.0)
        
        Sx = safe_scalar(df.loc[section, "Sx [cm3]"])
        Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        rts = safe_scalar(df.loc[section, 'rts [cm]']) if 'rts [cm]' in df.columns else ry * 1.2
        J = safe_scalar(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 1.0
        ho = safe_scalar(df.loc[section, 'ho [mm]']) / 10.0 if 'ho [mm]' in df.columns else d / 10.0
        
        # Step 1: Calculate Plastic Moment
        row = 3
        ws_flex[f'A{row}'] = "STEP 1: CALCULATE PLASTIC MOMENT Mp"
        ws_flex[f'A{row}'].font = section_font
        ws_flex[f'A{row}'].fill = section_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 2
        ws_flex[f'A{row}'] = "AISC Equation F2-1:"
        ws_flex[f'A{row}'].font = Font(bold=True, italic=True)
        ws_flex[f'A{row}'].fill = equation_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_flex[f'A{row}'] = "Mp = Fy × Zx"
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_flex[f'A{row}'] = f"Mp = {Fy:.1f} × {Zx:.2f}"
        ws_flex.merge_cells(f'A{row}:B{row}')
        ws_flex[f'C{row}'] = f"{flex['Mp']*100000:.0f} kgf·cm"
        ws_flex[f'D{row}'] = "="
        ws_flex[f'D{row}'].alignment = center_align
        ws_flex[f'E{row}'] = f"{flex['Mp']:.2f} t·m"
        ws_flex[f'E{row}'].fill = result_fill
        ws_flex[f'E{row}'].font = result_font
        
        # Step 2: Limiting Lengths
        row += 3
        ws_flex[f'A{row}'] = "STEP 2: CALCULATE LIMITING LATERALLY UNBRACED LENGTHS"
        ws_flex[f'A{row}'].font = section_font
        ws_flex[f'A{row}'].fill = section_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 2
        ws_flex[f'A{row}'] = "Compact Limit Lp (AISC Equation F2-5):"
        ws_flex[f'A{row}'].font = Font(bold=True, italic=True)
        ws_flex[f'A{row}'].fill = equation_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_flex[f'A{row}'] = "Lp = 1.76 × ry × √(E/Fy)"
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_flex[f'A{row}'] = f"Lp = 1.76 × {ry:.2f} × √({E:.0f}/{Fy:.1f})"
        ws_flex.merge_cells(f'A{row}:B{row}')
        ws_flex[f'C{row}'] = f"{flex['Lp']*100:.2f} cm"
        ws_flex[f'D{row}'] = "="
        ws_flex[f'D{row}'].alignment = center_align
        ws_flex[f'E{row}'] = f"{flex['Lp']:.3f} m"
        ws_flex[f'E{row}'].fill = result_fill
        ws_flex[f'E{row}'].font = result_font
        
        row += 2
        ws_flex[f'A{row}'] = "Inelastic Limit Lr (AISC Equation F2-6):"
        ws_flex[f'A{row}'].font = Font(bold=True, italic=True)
        ws_flex[f'A{row}'].fill = equation_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_flex[f'A{row}'] = "Lr = 1.95 × rts × (E/(0.7Fy)) × √(Jc/(Sx×ho)) × √(1 + √(1 + 6.76×((0.7Fy)/E)²×((Sx×ho)/(Jc))²))"
        ws_flex[f'A{row}'].alignment = Alignment(wrap_text=True)
        ws_flex.merge_cells(f'A{row}:E{row}')
        ws_flex.row_dimensions[row].height = 30
        
        row += 1
        ws_flex[f'A{row}'] = "Where:"
        row += 1
        ws_flex[f'A{row}'] = f"  rts = {rts:.2f} cm"
        row += 1
        ws_flex[f'A{row}'] = f"  J = {J:.2f} cm⁴"
        row += 1
        ws_flex[f'A{row}'] = f"  ho = {ho:.2f} cm"
        row += 1
        ws_flex[f'A{row}'] = f"  c = 1.0 (for doubly symmetric I-shapes)"
        
        row += 1
        ws_flex[f'A{row}'] = "Result:"
        ws_flex.merge_cells(f'A{row}:D{row}')
        ws_flex[f'E{row}'] = f"{flex['Lr']:.3f} m"
        ws_flex[f'E{row}'].fill = result_fill
        ws_flex[f'E{row}'].font = result_font
        
        # Step 3: Determine Nominal Moment
        row += 3
        ws_flex[f'A{row}'] = f"STEP 3: DETERMINE NOMINAL MOMENT Mn (Lb = {Lb:.2f} m)"
        ws_flex[f'A{row}'].font = section_font
        ws_flex[f'A{row}'].fill = section_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 2
        if Lb <= flex['Lp']:
            ws_flex[f'A{row}'] = f"Lb ({Lb:.2f}m) ≤ Lp ({flex['Lp']:.3f}m)"
            ws_flex[f'A{row}'].font = Font(bold=True, size=11)
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "AISC Equation F2-1 applies (Yielding - Limit State of Lateral-Torsional Buckling does not apply)"
            ws_flex[f'A{row}'].fill = equation_fill
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "Mn = Mp"
            ws_flex.merge_cells(f'A{row}:D{row}')
            ws_flex[f'E{row}'] = f"{flex['Mn']:.2f} t·m"
            ws_flex[f'E{row}'].fill = result_fill
            ws_flex[f'E{row}'].font = result_font
            
        elif Lb <= flex['Lr']:
            ws_flex[f'A{row}'] = f"Lp ({flex['Lp']:.3f}m) < Lb ({Lb:.2f}m) ≤ Lr ({flex['Lr']:.3f}m)"
            ws_flex[f'A{row}'].font = Font(bold=True, size=11)
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "AISC Equation F2-2 applies (Inelastic Lateral-Torsional Buckling)"
            ws_flex[f'A{row}'].fill = equation_fill
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "Mn = Cb[Mp - (Mp - 0.7FySx)((Lb-Lp)/(Lr-Lp))] ≤ Mp"
            ws_flex[f'A{row}'].alignment = Alignment(wrap_text=True)
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            Mr = 0.7 * Fy * Sx / 100000
            ws_flex[f'A{row}'] = f"Mn = {Cb:.2f}[{flex['Mp']:.2f} - ({flex['Mp']:.2f} - {Mr:.2f}) × (({Lb:.2f}-{flex['Lp']:.3f})/({flex['Lr']:.3f}-{flex['Lp']:.3f}))]"
            ws_flex.merge_cells(f'A{row}:D{row}')
            ws_flex[f'E{row}'] = f"{flex['Mn']:.2f} t·m"
            ws_flex[f'E{row}'].fill = result_fill
            ws_flex[f'E{row}'].font = result_font
            
        else:
            ws_flex[f'A{row}'] = f"Lb ({Lb:.2f}m) > Lr ({flex['Lr']:.3f}m)"
            ws_flex[f'A{row}'].font = Font(bold=True, size=11)
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "AISC Equation F2-3 applies (Elastic Lateral-Torsional Buckling)"
            ws_flex[f'A{row}'].fill = equation_fill
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "Fcr = (Cbπ²E)/((Lb/rts)²) × √(1 + 0.078(Jc/(Sxho))×(Lb/rts)²)"
            ws_flex[f'A{row}'].alignment = Alignment(wrap_text=True)
            ws_flex.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_flex[f'A{row}'] = "Mn = Fcr × Sx ≤ Mp"
            ws_flex.merge_cells(f'A{row}:D{row}')
            ws_flex[f'E{row}'] = f"{flex['Mn']:.2f} t·m"
            ws_flex[f'E{row}'].fill = result_fill
            ws_flex[f'E{row}'].font = result_font
        
        # Step 4: Design Strength
        row += 3
        ws_flex[f'A{row}'] = "STEP 4: CALCULATE DESIGN STRENGTH"
        ws_flex[f'A{row}'].font = section_font
        ws_flex[f'A{row}'].fill = section_fill
        ws_flex.merge_cells(f'A{row}:E{row}')
        
        row += 2
        ws_flex[f'A{row}'] = "Resistance Factor (AISC Section F1):"
        ws_flex[f'A{row}'].font = Font(bold=True)
        
        row += 1
        ws_flex[f'A{row}'] = "φb = 0.90"
        ws_flex[f'A{row}'].fill = equation_fill
        
        row += 2
        ws_flex[f'A{row}'] = "φMn = φb × Mn"
        ws_flex.merge_cells(f'A{row}:B{row}')
        ws_flex[f'C{row}'] = f"= 0.90 × {flex['Mn']:.2f}"
        ws_flex[f'D{row}'] = "="
        ws_flex[f'D{row}'].alignment = center_align
        ws_flex[f'E{row}'] = f"{flex['phi_Mn']:.2f} t·m"
        ws_flex[f'E{row}'].fill = result_fill
        ws_flex[f'E{row}'].font = result_font
        ws_flex[f'E{row}'].border = thick_border
        
        # Summary Table
        row += 3
        ws_flex[f'A{row}'] = "FLEXURAL DESIGN SUMMARY"
        ws_flex[f'A{row}'].font = section_font
        ws_flex[f'A{row}'].fill = section_fill
        ws_flex.merge_cells(f'A{row}:C{row}')
        
        row += 1
        summary_data = [
            ['Parameter', 'Value', 'Status'],
            ['Design Moment Capacity (φMn)', f"{flex['phi_Mn']:.2f} t·m", ''],
            ['Nominal Moment (Mn)', f"{flex['Mn']:.2f} t·m", ''],
            ['Plastic Moment (Mp)', f"{flex['Mp']:.2f} t·m", ''],
            ['Limiting Length Lp', f"{flex['Lp']:.3f} m", ''],
            ['Limiting Length Lr', f"{flex['Lr']:.3f} m", ''],
            ['Design Case', flex['case'], ''],
            ['Design Zone', flex['zone'], ''],
            ['Utilization Ratio', f"{flex['ratio']:.3f}", '✓ PASS' if flex['adequate'] else '✗ FAIL'],
        ]
        
        for data_row in summary_data:
            row += 1
            for col, value in enumerate(data_row, start=1):
                cell = ws_flex.cell(row=row, column=col)
                cell.value = value
                cell.border = thin_border
                cell.alignment = center_align if col > 1 else left_align
                
                if 'Parameter' in str(value):
                    cell.font = header_font
                    cell.fill = header_fill
                elif col == 3 and '✓' in str(value):
                    cell.fill = adequate_fill
                    cell.font = adequate_font
                elif col == 3 and '✗' in str(value):
                    cell.fill = inadequate_fill
                    cell.font = inadequate_font
        
        # Auto-size columns
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_flex.column_dimensions[col].width = 25
    
    # ==================== SHEET 5: COMPRESSION ANALYSIS ====================
    if analysis_results and 'compression' in analysis_results:
        ws_comp = wb.create_sheet("Compression Analysis")
        
        row = 1
        ws_comp['A1'] = "AISC 360-16 CHAPTER E3: COMPRESSION DESIGN"
        ws_comp['A1'].font = title_font
        ws_comp['A1'].fill = title_fill
        ws_comp['A1'].alignment = center_align
        ws_comp.merge_cells('A1:E1')
        ws_comp.row_dimensions[1].height = 25
        
        comp = analysis_results['compression']
        KL = design_params.get('KL', 0)
        
        Ag = safe_scalar(df.loc[section, 'A [cm2]'])
        rx = safe_scalar(df.loc[section, 'rx [cm]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        # Step 1: Slenderness Ratio
        row = 3
        ws_comp[f'A{row}'] = "STEP 1: CALCULATE SLENDERNESS RATIO"
        ws_comp[f'A{row}'].font = section_font
        ws_comp[f'A{row}'].fill = section_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 2
        KL_cm = KL * 100
        lambda_x = KL_cm / rx
        lambda_y = KL_cm / ry
        lambda_c = max(lambda_x, lambda_y)
        
        ws_comp[f'A{row}'] = f"KL/rx = {KL_cm:.1f} / {rx:.2f}"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{lambda_x:.1f}"
        ws_comp[f'E{row}'].fill = calc_fill
        
        row += 1
        ws_comp[f'A{row}'] = f"KL/ry = {KL_cm:.1f} / {ry:.2f}"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{lambda_y:.1f}"
        ws_comp[f'E{row}'].fill = calc_fill
        
        row += 1
        ws_comp[f'A{row}'] = "λc = max(KL/rx, KL/ry)"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{lambda_c:.1f}"
        ws_comp[f'E{row}'].fill = result_fill
        ws_comp[f'E{row}'].font = result_font
        
        # Step 2: Elastic Buckling Stress
        row += 3
        ws_comp[f'A{row}'] = "STEP 2: CALCULATE ELASTIC BUCKLING STRESS Fe"
        ws_comp[f'A{row}'].font = section_font
        ws_comp[f'A{row}'].fill = section_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 2
        ws_comp[f'A{row}'] = "AISC Equation E3-4:"
        ws_comp[f'A{row}'].font = Font(bold=True, italic=True)
        ws_comp[f'A{row}'].fill = equation_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_comp[f'A{row}'] = "Fe = π²E / (KL/r)²"
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 1
        Fe = (math.pi**2 * E) / (lambda_c**2)
        ws_comp[f'A{row}'] = f"Fe = π² × {E:.0f} / {lambda_c:.1f}²"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{Fe:.1f} kgf/cm²"
        ws_comp[f'E{row}'].fill = result_fill
        ws_comp[f'E{row}'].font = result_font
        
        # Step 3: Determine Critical Stress
        row += 3
        ws_comp[f'A{row}'] = "STEP 3: DETERMINE CRITICAL STRESS Fcr"
        ws_comp[f'A{row}'].font = section_font
        ws_comp[f'A{row}'].fill = section_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 2
        lambda_limit = 4.71 * safe_sqrt(E / Fy)
        ws_comp[f'A{row}'] = "Limiting Slenderness:"
        ws_comp[f'A{row}'].font = Font(bold=True)
        
        row += 1
        ws_comp[f'A{row}'] = f"4.71√(E/Fy) = 4.71√({E:.0f}/{Fy:.1f})"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{lambda_limit:.1f}"
        ws_comp[f'E{row}'].fill = calc_fill
        
        row += 2
        if lambda_c <= lambda_limit:
            ws_comp[f'A{row}'] = f"λc ({lambda_c:.1f}) ≤ {lambda_limit:.1f}"
            ws_comp[f'A{row}'].font = Font(bold=True, size=11)
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_comp[f'A{row}'] = "INELASTIC BUCKLING - AISC Equation E3-2:"
            ws_comp[f'A{row}'].fill = equation_fill
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_comp[f'A{row}'] = "Fcr = [0.658^(Fy/Fe)] × Fy"
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            exponent = Fy / Fe
            Fcr = (0.658 ** exponent) * Fy
            ws_comp[f'A{row}'] = f"Fcr = [0.658^({Fy:.1f}/{Fe:.1f})] × {Fy:.1f}"
            ws_comp.merge_cells(f'A{row}:D{row}')
            ws_comp[f'E{row}'] = f"{Fcr:.1f} kgf/cm²"
            ws_comp[f'E{row}'].fill = result_fill
            ws_comp[f'E{row}'].font = result_font
        else:
            ws_comp[f'A{row}'] = f"λc ({lambda_c:.1f}) > {lambda_limit:.1f}"
            ws_comp[f'A{row}'].font = Font(bold=True, size=11)
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_comp[f'A{row}'] = "ELASTIC BUCKLING - AISC Equation E3-3:"
            ws_comp[f'A{row}'].fill = equation_fill
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            ws_comp[f'A{row}'] = "Fcr = 0.877 × Fe"
            ws_comp.merge_cells(f'A{row}:E{row}')
            
            row += 1
            Fcr = 0.877 * Fe
            ws_comp[f'A{row}'] = f"Fcr = 0.877 × {Fe:.1f}"
            ws_comp.merge_cells(f'A{row}:D{row}')
            ws_comp[f'E{row}'] = f"{Fcr:.1f} kgf/cm²"
            ws_comp[f'E{row}'].fill = result_fill
            ws_comp[f'E{row}'].font = result_font
        
        # Step 4: Calculate Strength
        row += 3
        ws_comp[f'A{row}'] = "STEP 4: CALCULATE NOMINAL AND DESIGN STRENGTH"
        ws_comp[f'A{row}'].font = section_font
        ws_comp[f'A{row}'].fill = section_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 2
        ws_comp[f'A{row}'] = "AISC Equation E3-1:"
        ws_comp[f'A{row}'].font = Font(bold=True, italic=True)
        ws_comp[f'A{row}'].fill = equation_fill
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 1
        ws_comp[f'A{row}'] = "Pn = Fcr × Ag"
        ws_comp.merge_cells(f'A{row}:E{row}')
        
        row += 1
        Pn = Fcr * Ag / 1000
        ws_comp[f'A{row}'] = f"Pn = {Fcr:.1f} × {Ag:.2f} / 1000"
        ws_comp.merge_cells(f'A{row}:D{row}')
        ws_comp[f'E{row}'] = f"{Pn:.2f} tons"
        ws_comp[f'E{row}'].fill = result_fill
        ws_comp[f'E{row}'].font = result_font
        
        row += 2
        ws_comp[f'A{row}'] = "Resistance Factor (AISC Section E1):"
        ws_comp[f'A{row}'].font = Font(bold=True)
        
        row += 1
        ws_comp[f'A{row}'] = "φc = 0.90"
        ws_comp[f'A{row}'].fill = equation_fill
        
        row += 2
        ws_comp[f'A{row}'] = "φPn = φc × Pn"
        ws_comp.merge_cells(f'A{row}:B{row}')
        ws_comp[f'C{row}'] = f"= 0.90 × {Pn:.2f}"
        ws_comp[f'D{row}'] = "="
        ws_comp[f'D{row}'].alignment = center_align
        ws_comp[f'E{row}'] = f"{comp['phi_Pn']:.2f} tons"
        ws_comp[f'E{row}'].fill = result_fill
        ws_comp[f'E{row}'].font = result_font
        ws_comp[f'E{row}'].border = thick_border
        
        # Summary Table
        row += 3
        ws_comp[f'A{row}'] = "COMPRESSION DESIGN SUMMARY"
        ws_comp[f'A{row}'].font = section_font
        ws_comp[f'A{row}'].fill = section_fill
        ws_comp.merge_cells(f'A{row}:C{row}')
        
        row += 1
        summary_data = [
            ['Parameter', 'Value', 'Status'],
            ['Design Strength (φPn)', f"{comp['phi_Pn']:.2f} tons", ''],
            ['Nominal Strength (Pn)', f"{comp['Pn']:.2f} tons", ''],
            ['Critical Stress (Fcr)', f"{comp['Fcr']:.1f} kgf/cm²", ''],
            ['Elastic Buckling Stress (Fe)', f"{Fe:.1f} kgf/cm²", ''],
            ['Slenderness Ratio (λc)', f"{comp['lambda_c']:.1f}", ''],
            ['Buckling Mode', comp['mode'], ''],
            ['Utilization Ratio', f"{comp['ratio']:.3f}", '✓ PASS' if comp['adequate'] else '✗ FAIL'],
        ]
        
        for data_row in summary_data:
            row += 1
            for col, value in enumerate(data_row, start=1):
                cell = ws_comp.cell(row=row, column=col)
                cell.value = value
                cell.border = thin_border
                cell.alignment = center_align if col > 1 else left_align
                
                if 'Parameter' in str(value):
                    cell.font = header_font
                    cell.fill = header_fill
                elif col == 3 and '✓' in str(value):
                    cell.fill = adequate_fill
                    cell.font = adequate_font
                elif col == 3 and '✗' in str(value):
                    cell.fill = inadequate_fill
                    cell.font = inadequate_font
        
        # Auto-size columns
        for col in ['A', 'B', 'C', 'D', 'E']:
            ws_comp.column_dimensions[col].width = 25
    
    # Save to buffer
    wb.save(buffer)
    buffer.seek(0)
    return buffer

# ==================== EVALUATION FUNCTION ====================
def evaluate_section_design(df, df_mat, section, material, design_loads, design_lengths):
    """Comprehensive section evaluation"""
    try:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
        weight = safe_scalar(df.loc[section, weight_col])
        
        flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section, material, design_lengths['Lb'])
        comp_result = aisc_360_16_e3_compression_design(df, df_mat, section, material, 
                                                       design_lengths['KLx'], design_lengths['KLy'])
        
        if flex_result and comp_result:
            phi_Mn = 0.9 * flex_result['Mn']
            phi_Pn = comp_result['phi_Pn']
            
            moment_ratio = design_loads['Mu'] / phi_Mn if phi_Mn > 0 else 999
            axial_ratio = design_loads['Pu'] / phi_Pn if phi_Pn > 0 else 999
            
            flexural_adequate = moment_ratio <= 1.0
            compression_adequate = axial_ratio <= 1.0
            overall_adequate = flexural_adequate and compression_adequate
            
            Lp = flex_result['Lp']
            Lr = flex_result['Lr'] 
            current_Lb = design_lengths['Lb']
            
            if current_Lb <= Lp:
                flexural_zone = "Yielding (F2.1)"
            elif current_Lb <= Lr:
                flexural_zone = "Inelastic LTB (F2.2)"
            else:
                flexural_zone = "Elastic LTB (F2.3)"
            
            return {
                'section': section,
                'material': material,
                'weight': weight,
                'flexural': {
                    'Mn': flex_result['Mn'],
                    'phi_Mn': phi_Mn,
                    'Mp': flex_result['Mp'],
                    'Lp': Lp,
                    'Lr': Lr,
                    'case': flex_result['Case'],
                    'zone': flexural_zone,
                    'ratio': moment_ratio,
                    'adequate': flexural_adequate,
                },
                'compression': {
                    'Pn': comp_result['Pn'],
                    'phi_Pn': phi_Pn,
                    'Fcr': comp_result['Fcr'],
                    'lambda_c': comp_result['lambda_c'],
                    'mode': comp_result['buckling_mode'],
                    'ratio': axial_ratio,
                    'adequate': compression_adequate,
                },
                'design_check': {
                    'overall_adequate': overall_adequate,
                    'moment_utilization': moment_ratio,
                    'axial_utilization': axial_ratio,
                }
            }
    except Exception as e:
        st.error(f"Error in section evaluation: {e}")
        return None

# ==================== LOAD DATA ====================
df, df_mat, success = load_data()

if not success:
    st.error("❌ Failed to load data. Please check your internet connection.")
    st.stop()

# ==================== LIBRARY STATUS WARNINGS ====================
if not PDF_AVAILABLE:
    st.sidebar.warning("⚠️ PDF export unavailable. Install: `pip install reportlab`")
if not EXCEL_AVAILABLE:
    st.sidebar.warning("⚠️ Excel export unavailable. Install: `pip install openpyxl`")

# ==================== MAIN HEADER ====================
st.markdown('<h1 class="main-header">AISC 360-16 Steel Design Professional v7.0</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #7f8c8d; font-size: 1.1rem; font-weight: 500;">Professional UI/UX | Advanced Export Capabilities | Enhanced Visualizations</p>', unsafe_allow_html=True)

# ==================== IMPROVED PROFESSIONAL SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🔧 Design Configuration")
    st.markdown("---")
    
    # ========== MATERIAL SELECTION ==========
    material_list = list(df_mat.index)
    selected_material = st.selectbox(
        "⚙️ Steel Grade:",
        material_list,
        index=0,
        key="material_selector",
        help="Select steel material grade per AISC 360-16"
    )
    st.session_state.selected_material = selected_material
    
    if selected_material:
        Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
        Fu = safe_scalar(df_mat.loc[selected_material, "Tensile Strength (ksc)"])
        E = safe_scalar(df_mat.loc[selected_material, "E"])
        
        st.markdown(f"""
        <div class="info-box">
        <b>📋 Material: {selected_material}</b><br>
        • Fy = {Fy:.1f} kgf/cm²<br>
        • Fu = {Fu:.1f} kgf/cm²<br>
        • E = {E:,.0f} kgf/cm²
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📐 Section Selection")
    
    # ========== SECTION SELECTION - FIXED ==========
    section_list = list(df.index)
    
    # Get default index from session state
    default_index = 0
    if st.session_state.selected_section and st.session_state.selected_section in section_list:
        default_index = section_list.index(st.session_state.selected_section)
    
    # Use selectbox with proper index tracking
    selected_section = st.selectbox(
        "🔩 Select Section:",
        section_list,
        index=default_index,
        key="section_selector",
        help="Select steel section from database"
    )
    
    # Update session state
    st.session_state.selected_section = selected_section
    
    # ========== SECTION PREVIEW CARD ==========
    if selected_section:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
        
        # Get section properties
        weight = safe_scalar(df.loc[selected_section, weight_col])
        d = safe_scalar(df.loc[selected_section, 'd [mm]'])
        bf = safe_scalar(df.loc[selected_section, 'bf [mm]'])
        tf = safe_scalar(df.loc[selected_section, 'tf [mm]'])
        tw = safe_scalar(df.loc[selected_section, 'tw [mm]'])
        Zx = safe_scalar(df.loc[selected_section, 'Zx [cm3]'])
        Ix = safe_scalar(df.loc[selected_section, 'Ix [cm4]'])
        A = safe_scalar(df.loc[selected_section, 'A [cm2]'])
        
        st.markdown(f"""
        <div class="success-box">
        <h4 style="margin:0; color:#2E7D32;">✅ {selected_section}</h4>
        <hr style="margin:8px 0; border-color:#4caf50;">
        <b>Dimensions:</b><br>
        • d = {d:.0f} mm<br>
        • bf = {bf:.0f} mm<br>
        • tf = {tf:.1f} mm<br>
        • tw = {tw:.1f} mm<br>
        <b>Properties:</b><br>
        • A = {A:.1f} cm²<br>
        • Ix = {Ix:,.0f} cm⁴<br>
        • Zx = {Zx:,.0f} cm³<br>
        • Weight = {weight:.1f} kg/m
        </div>
        """, unsafe_allow_html=True)
        
        # ========== MINI CROSS-SECTION VISUALIZATION ==========
        st.markdown("#### 📊 Section Preview")
        
        fig_preview = create_section_preview(d, bf, tf, tw, selected_section)
        st.pyplot(fig_preview, use_container_width=True)
        plt.close(fig_preview)
    
    # ========== PROJECT INFORMATION ==========
    st.markdown("---")
    st.markdown("### 📁 Project Information")
    
    with st.expander("📝 Edit Project Info", expanded=False):
        if 'project_info' not in st.session_state:
            st.session_state.project_info = {
                'project_name': '',
                'project_no': '',
                'designer': '',
                'checker': '',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'revision': '0'
            }
        
        st.session_state.project_info['project_name'] = st.text_input(
            "Project Name:", 
            value=st.session_state.project_info['project_name'],
            key="proj_name"
        )
        st.session_state.project_info['project_no'] = st.text_input(
            "Project No.:", 
            value=st.session_state.project_info['project_no'],
            key="proj_no"
        )
        st.session_state.project_info['designer'] = st.text_input(
            "Designer:", 
            value=st.session_state.project_info['designer'],
            key="designer"
        )
        st.session_state.project_info['checker'] = st.text_input(
            "Checker:", 
            value=st.session_state.project_info['checker'],
            key="checker"
        )
        st.session_state.project_info['date'] = st.text_input(
            "Date:", 
            value=st.session_state.project_info['date'],
            key="date"
        )
        st.session_state.project_info['revision'] = st.text_input(
            "Revision:", 
            value=st.session_state.project_info['revision'],
            key="revision"
        )
    
    # Show current project info summary
    if st.session_state.project_info['project_name']:
        st.markdown(f"""
        <div class="metric-card">
        <b>📋 Current Project:</b><br>
        {st.session_state.project_info['project_name']}<br>
        <small>Rev. {st.session_state.project_info['revision']} | {st.session_state.project_info['date']}</small>
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 2: SECTION COMPARISON ====================
with tab2:
    st.markdown('<h2 class="section-header">📈 Advanced Section Comparison</h2>', unsafe_allow_html=True)
    
    # Selection interface
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sections_to_compare = st.multiselect(
            "Select Sections to Compare:",
            list(df.index),
            default=list(df.index)[:5] if len(df.index) >= 5 else list(df.index)
        )
    
    with col2:
        compare_Lb = st.slider("Lb for Comparison (m):", 0.1, 15.0, 3.0, 0.5)
    
    with col3:
        compare_KL = st.slider("KL for Comparison (m):", 0.1, 10.0, 3.0, 0.5)
    
    if sections_to_compare and selected_material:
        comparison_data = []
        
        for sec in sections_to_compare:
            try:
                weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
                weight = safe_scalar(df.loc[sec, weight_col])
                
                flex_result = aisc_360_16_f2_flexural_design(df, df_mat, sec, selected_material, compare_Lb)
                comp_result = aisc_360_16_e3_compression_design(df, df_mat, sec, selected_material, compare_KL, compare_KL)
                
                if flex_result and comp_result:
                    comparison_data.append({
                        'Section': sec,
                        'Weight (kg/m)': weight,
                        'φMn (t·m)': 0.9 * flex_result['Mn'],
                        'φPn (tons)': comp_result['phi_Pn'],
                        'Lp (m)': flex_result['Lp'],
                        'Lr (m)': flex_result['Lr'],
                        'Moment Efficiency': (0.9 * flex_result['Mn']) / weight,
                        'Compression Efficiency': comp_result['phi_Pn'] / weight
                    })
            except:
                continue
        
        if comparison_data:
            df_comparison = pd.DataFrame(comparison_data)
            
            # Enhanced Comparison Chart
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Moment Capacity', 'Compression Capacity',
                               'Moment Efficiency', 'Weight Comparison'),
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "bar"}, {"type": "bar"}]]
            )
            
            # Moment capacity
            fig.add_trace(go.Bar(
                x=df_comparison['Section'],
                y=df_comparison['φMn (t·m)'],
                marker_color='#667eea',
                name='φMn',
                showlegend=False
            ), row=1, col=1)
            
            # Compression capacity
            fig.add_trace(go.Bar(
                x=df_comparison['Section'],
                y=df_comparison['φPn (tons)'],
                marker_color='#2196f3',
                name='φPn',
                showlegend=False
            ), row=1, col=2)
            
            # Moment efficiency
            fig.add_trace(go.Bar(
                x=df_comparison['Section'],
                y=df_comparison['Moment Efficiency'],
                marker_color='#4caf50',
                name='Moment Eff.',
                showlegend=False
            ), row=2, col=1)
            
            # Weight
            fig.add_trace(go.Bar(
                x=df_comparison['Section'],
                y=df_comparison['Weight (kg/m)'],
                marker_color='#ff9800',
                name='Weight',
                showlegend=False
            ), row=2, col=2)
            
            layout = get_enhanced_plotly_layout()
            layout['height'] = 800
            layout['title'] = "AISC 360-16 Multi-Section Comparison"
            fig.update_layout(layout)
            
            st.plotly_chart(fig, use_container_width=True, config=create_enhanced_plotly_config())
            
            # Enhanced Comparison Table
            st.markdown("### 📊 Detailed Comparison Table")
            
            # Style the dataframe
            styled_df = df_comparison.style.format({
                'Weight (kg/m)': '{:.1f}',
                'φMn (t·m)': '{:.2f}',
                'φPn (tons)': '{:.2f}',
                'Lp (m)': '{:.3f}',
                'Lr (m)': '{:.3f}',
                'Moment Efficiency': '{:.3f}',
                'Compression Efficiency': '{:.3f}'
            }).background_gradient(cmap='Blues', subset=['φMn (t·m)', 'φPn (tons)'])
            
            st.dataframe(styled_df, use_container_width=True, height=400)
    else:
        st.warning("⚠️ Please select sections to compare")

# ==================== TAB 3: DESIGN EVALUATION & EXPORT ====================
# In Tab 3: Design Evaluation & Export section

# PDF Export Button
with col_export1:
    if PDF_AVAILABLE:
        if st.button("📄 Generate Professional Calculation Report", type="primary"):
            design_params = {
                'Mu': Mu_eval, 'Pu': Pu_eval,
                'Lb': Lb_eval, 'KL': KL_eval,
                'Cb': 1.0
            }
            
            # Get project info from session state
            project_info = st.session_state.get('project_info', {
                'project_name': 'N/A',
                'project_no': 'N/A',
                'designer': 'N/A',
                'checker': 'N/A',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'revision': '0'
            })
            
            with st.spinner('Generating professional calculation report...'):
                pdf_buffer = generate_professional_calculation_report(
                    df, df_mat, section, selected_material, 
                    st.session_state.evaluation_results, design_params, project_info
                )
            
            if pdf_buffer:
                # Create filename with project info
                proj_name = project_info.get('project_name', 'Project').replace(' ', '_')[:20]
                filename = f"Calc_{proj_name}_{section}_{datetime.now().strftime('%Y%m%d')}.pdf"
                
                st.download_button(
                    label="📥 Download Calculation Report (PDF)",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )
                st.success("✅ Professional calculation report generated!")
    else:
        st.warning("⚠️ PDF export requires reportlab library")
        st.code("pip install reportlab")

# ==================== TAB 4: DOCUMENTATION ====================
with tab4:
    st.markdown('<h2 class="section-header">📚 User Guide & AISC References</h2>', unsafe_allow_html=True)
    
    with st.expander("🎯 Application Features", expanded=True):
        st.markdown("""
        ### Professional UI/UX Enhancements v7.0
        
        **Visual Improvements:**
        - 🎨 Modern gradient color scheme with professional typography
        - 📊 Enhanced data tables with improved readability and alignment
        - 📈 Optimized charts with proper margins and label placement
        - 🎯 Clean, intuitive layout with logical information flow
        
        **Export Capabilities:**
        - 📄 **PDF Export:** Comprehensive calculation reports with professional formatting
        - 📊 **Excel Export:** Detailed analysis with formatted tables and styling
        - 📋 Both formats include input parameters, step-by-step calculations, and results
        
        **Analysis Tools:**
        - Flexural design per AISC 360-16 Chapter F2
        - Column design per AISC 360-16 Chapter E3
        - Beam-column interaction per AISC 360-16 Chapter H1
        - Multi-section comparison with efficiency metrics
        """)
    
    with st.expander("📖 AISC 360-16 References"):
        st.markdown("""
        ### Design Specifications
        
        **Chapter F2 - Lateral-Torsional Buckling:**
        - F2.1: Yielding (Lb ≤ Lp)
        - F2.2: Inelastic LTB (Lp < Lb ≤ Lr)
        - F2.3: Elastic LTB (Lb > Lr)
        
        **Chapter E3 - Flexural Buckling:**
        - E3.2(a): Inelastic buckling (λc ≤ 4.71√(E/Fy))
        - E3.2(b): Elastic buckling (λc > 4.71√(E/Fy))
        
        **Chapter H1 - Combined Forces:**
        - H1-1a: Pr/Pc ≥ 0.2
        - H1-1b: Pr/Pc < 0.2
        """)
    
    with st.expander("🚀 Quick Start Guide"):
        st.markdown("""
        ### Getting Started
        
        1. **Select Material:** Choose steel grade from sidebar
        2. **Select Section:** Pick steel section from dropdown
        3. **Choose Analysis:** Select design type in main tabs
        4. **Input Parameters:** Enter loads and lengths
        5. **View Results:** Analyze charts and metrics
        6. **Export Report:** Generate PDF or Excel documentation
        
        ### Export Instructions
        
        **PDF Reports:**
        - Professional formatting with AISC compliance
        - Includes material properties, section properties, and analysis results
        - Download directly from the browser
        
        **Excel Reports:**
        - Formatted spreadsheets with multiple sheets
        - Color-coded tables for easy reading
        - Can be edited and customized after export
        """)

# ==================== PROFESSIONAL FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; border-radius: 15px; margin-top: 2rem;'>
    <h3 style='margin: 0; font-weight: 700;'>AISC 360-16 Steel Design Professional v7.0</h3>
    <p style='margin: 0.5rem 0; font-size: 1.1rem;'>🎯 Professional UI/UX | 📊 Advanced Export | 📈 Enhanced Visualizations</p>
    <p style='margin: 0.5rem 0;'>📐 Full AISC Compliance: F2 Flexural | E3 Compression | H1 Combined Forces</p>
    <p style='margin: 0.5rem 0; font-size: 0.9rem; opacity: 0.9;'>
        <i>© 2024 - Professional Structural Engineering Tool</i>
    </p>
</div>
""", unsafe_allow_html=True)
