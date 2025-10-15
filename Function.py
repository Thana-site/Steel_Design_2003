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

# ==================== PROFESSIONAL SIDEBAR ====================
with st.sidebar:
    st.markdown("### 🔧 Design Configuration")
    st.markdown("---")
    
    material_list = list(df_mat.index)
    selected_material = st.selectbox(
        "⚙️ Steel Grade:",
        material_list,
        index=0,
        help="Select steel material grade per AISC 360-16"
    )
    st.session_state.selected_material = selected_material
    
    if selected_material:
        Fy = df_mat.loc[selected_material, "Yield Point (ksc)"]
        Fu = df_mat.loc[selected_material, "Tensile Strength (ksc)"]
        st.markdown(f"""
        <div class="info-box">
        <b>Selected: {selected_material}</b><br>
        • Fy = {Fy:.1f} ksc<br>
        • Fu = {Fu:.1f} ksc<br>
        • E = 2.04×10⁶ ksc
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📐 Section Selection")
    
    section_list = list(df.index)
    quick_section = st.selectbox(
        "Select Section:",
        ["None"] + section_list,
        help="Quick select a specific section"
    )
    
    if quick_section != "None":
        st.session_state.selected_section = quick_section
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
        weight = df.loc[quick_section, weight_col]
        
        st.markdown(f"""
        <div class="success-box">
        <b>{quick_section}</b><br>
        • Weight: {weight:.1f} kg/m<br>
        • Zx: {df.loc[quick_section, 'Zx [cm3]']:.0f} cm³
        </div>
        """, unsafe_allow_html=True)

# ==================== ENHANCED TABS ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Design Analysis",
    "📈 Section Comparison", 
    "📋 Design Evaluation & Export",
    "📚 Documentation"
])

# ==================== TAB 1: DESIGN ANALYSIS ====================
with tab1:
    st.markdown('<h2 class="section-header">📊 Comprehensive Design Analysis</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        # Analysis Type Selection
        analysis_type = st.radio(
            "Select Analysis Type:",
            ["Flexural Design (F2)", "Column Design (E3)", "Beam-Column (H1)"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if analysis_type == "Flexural Design (F2)":
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Input Parameters")
                Lb = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
                Cb = st.number_input("Cb Factor:", 1.0, 2.3, 1.0, 0.1)
                
                result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb, Cb)
                
                if result:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("φMn", f"{0.9*result['Mn']:.2f} t·m")
                    st.metric("Design Case", result['Case'])
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="critical-lengths-box">
                    <b>Critical Lengths:</b><br>
                    Lp = {result['Lp']:.3f} m<br>
                    Lr = {result['Lr']:.3f} m
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                if result:
                    # Generate capacity curve
                    Lb_points = np.linspace(0.1, 15, 200)
                    Mn_points = []
                    
                    for lb in Lb_points:
                        r = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, lb, Cb)
                        Mn_points.append(0.9 * r['Mn'] if r else 0)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=Lb_points, y=Mn_points,
                        mode='lines',
                        name='φMn',
                        line=dict(color='#667eea', width=3),
                        hovertemplate='Lb: %{x:.2f}m<br>φMn: %{y:.2f} t·m<extra></extra>'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=[Lb], y=[0.9*result['Mn']],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=15, symbol='star')
                    ))
                    
                    fig.add_vline(x=result['Lp'], line_dash="dash", line_color='#4caf50', line_width=2,
                                annotation_text=f"Lp={result['Lp']:.2f}m")
                    fig.add_vline(x=result['Lr'], line_dash="dash", line_color='#ff9800', line_width=2,
                                annotation_text=f"Lr={result['Lr']:.2f}m")
                    
                    layout = get_enhanced_plotly_layout()
                    layout['title'] = f"AISC F2: Flexural Analysis - {section}"
                    layout['xaxis']['title'] = "Unbraced Length, Lb (m)"
                    layout['yaxis']['title'] = "Design Moment, φMn (t·m)"
                    layout['height'] = 600
                    
                    fig.update_layout(layout)
                    st.plotly_chart(fig, use_container_width=True, config=create_enhanced_plotly_config())
        
        elif analysis_type == "Column Design (E3)":
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Input Parameters")
                KL = st.slider("Effective Length KL (m):", 0.1, 10.0, 3.0, 0.1)
                Pu = st.number_input("Applied Load Pu (tons):", 0.0, 500.0, 100.0, 10.0)
                
                comp_result = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, KL, KL)
                
                if comp_result:
                    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                    st.metric("φPn", f"{comp_result['phi_Pn']:.2f} tons")
                    st.metric("Buckling Mode", comp_result['buckling_mode'])
                    ratio = Pu / comp_result['phi_Pn']
                    st.metric("Utilization", f"{ratio:.3f}", 
                             delta="✓ PASS" if ratio <= 1.0 else "✗ FAIL")
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if comp_result:
                    # Generate capacity curve
                    lambda_points = np.linspace(1, 250, 250)
                    Pn_points = []
                    
                    Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
                    E = safe_scalar(df_mat.loc[selected_material, "E"])
                    Ag = safe_scalar(df.loc[section, 'A [cm2]'])
                    lambda_limit = 4.71 * safe_sqrt(E / Fy)
                    
                    for lc in lambda_points:
                        Fe = (math.pi**2 * E) / (lc**2)
                        if lc <= lambda_limit:
                            Fcr = (0.658**(Fy/Fe)) * Fy
                        else:
                            Fcr = 0.877 * Fe
                        Pn_points.append(0.9 * Fcr * Ag / 1000.0)
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=lambda_points, y=Pn_points,
                        mode='lines',
                        name='φPn',
                        line=dict(color='#2196f3', width=3)
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=[comp_result['lambda_c']], y=[comp_result['phi_Pn']],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=15, symbol='star')
                    ))
                    
                    fig.add_vline(x=lambda_limit, line_dash="dash", line_color='#ff9800', line_width=2,
                                annotation_text=f"λ limit={lambda_limit:.1f}")
                    
                    if Pu > 0:
                        fig.add_hline(y=Pu, line_dash="dash", line_color='#4caf50', line_width=2,
                                    annotation_text=f"Pu={Pu:.1f} tons")
                    
                    layout = get_enhanced_plotly_layout()
                    layout['title'] = f"AISC E3: Column Capacity - {section}"
                    layout['xaxis']['title'] = "Slenderness Ratio (KL/r)"
                    layout['yaxis']['title'] = "Design Strength, φPn (tons)"
                    layout['height'] = 600
                    
                    fig.update_layout(layout)
                    st.plotly_chart(fig, use_container_width=True, config=create_enhanced_plotly_config())
        
        else:  # Beam-Column H1
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Input Parameters")
                Pu_bc = st.number_input("Axial Load Pu (tons):", 0.0, 200.0, 50.0, 5.0, key="h1_pu")
                Mux = st.number_input("Moment Mux (t·m):", 0.0, 100.0, 30.0, 5.0, key="h1_mux")
                KL_bc = st.slider("Effective Length KL (m):", 0.1, 10.0, 3.0, 0.1, key="h1_kl")
                Lb_bc = st.slider("Unbraced Length Lb (m):", 0.1, 10.0, 3.0, 0.1, key="h1_lb")
                
                comp_result = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, KL_bc, KL_bc)
                flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_bc)
                
                if comp_result and flex_result:
                    phi_Pn = comp_result['phi_Pn']
                    phi_Mnx = 0.9 * flex_result['Mn']
                    
                    Zy = safe_scalar(df.loc[section, 'Zy [cm3]'])
                    Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
                    phi_Mny = 0.9 * 0.9 * Fy * Zy / 100000.0
                    
                    interaction_result = aisc_360_16_h1_interaction(Pu_bc, phi_Pn, Mux, phi_Mnx, 0, phi_Mny)
                    
                    if interaction_result:
                        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                        st.metric("Unity Check", f"{interaction_result['interaction_ratio']:.3f}")
                        st.metric("Equation", interaction_result['equation'])
                        status = "✓ PASS" if interaction_result['design_ok'] else "✗ FAIL"
                        st.metric("Status", status)
                        st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                if comp_result and flex_result and interaction_result:
                    # P-M Interaction Diagram
                    M_ratios = np.linspace(0, 1.2, 100)
                    P_ratios_h1a = []
                    P_ratios_h1b = []
                    
                    for m in M_ratios:
                        # H1-1a (Pr/Pc >= 0.2)
                        p_a = 1.0 - (9.0/8.0) * m
                        P_ratios_h1a.append(max(0, p_a))
                        
                        # H1-1b (Pr/Pc < 0.2)
                        p_b = 2.0 * (1.0 - m)
                        P_ratios_h1b.append(max(0, min(0.2, p_b)))
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=M_ratios, y=P_ratios_h1a,
                        mode='lines',
                        name='H1-1a (Pr/Pc ≥ 0.2)',
                        line=dict(color='#2196f3', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(33, 150, 243, 0.1)'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=M_ratios, y=P_ratios_h1b,
                        mode='lines',
                        name='H1-1b (Pr/Pc < 0.2)',
                        line=dict(color='#4caf50', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(76, 175, 80, 0.1)'
                    ))
                    
                    M_combined = interaction_result['Mrx_Mcx']
                    P_ratio = interaction_result['Pr_Pc']
                    
                    fig.add_trace(go.Scatter(
                        x=[M_combined], y=[P_ratio],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=20, symbol='star')
                    ))
                    
                    layout = get_enhanced_plotly_layout()
                    layout['title'] = f"AISC H1: P-M Interaction - {section}"
                    layout['xaxis']['title'] = "Moment Ratio (Mr/Mc)"
                    layout['yaxis']['title'] = "Axial Ratio (Pr/Pc)"
                    layout['height'] = 600
                    
                    fig.update_layout(layout)
                    st.plotly_chart(fig, use_container_width=True, config=create_enhanced_plotly_config())
    else:
        st.warning("⚠️ Please select a section from the sidebar")

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
with tab3:
    st.markdown('<h2 class="section-header">📋 Design Evaluation & Professional Export</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Design Parameters")
            Mu_eval = st.number_input("Design Moment Mu (t·m):", 0.0, 200.0, 50.0, 5.0, key="eval_mu")
            Pu_eval = st.number_input("Axial Load Pu (tons):", 0.0, 500.0, 100.0, 10.0, key="eval_pu")
        
        with col2:
            st.markdown("### Design Lengths")
            Lb_eval = st.number_input("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1, key="eval_lb")
            KL_eval = st.number_input("Effective Length KL (m):", 0.1, 20.0, 3.0, 0.1, key="eval_kl")
        
        if st.button("🔍 Perform Comprehensive Evaluation", type="primary"):
            design_loads = {'Mu': Mu_eval, 'Pu': Pu_eval}
            design_lengths = {'Lb': Lb_eval, 'KLx': KL_eval, 'KLy': KL_eval}
            
            evaluation = evaluate_section_design(df, df_mat, section, selected_material, design_loads, design_lengths)
            
            if evaluation:
                st.session_state.evaluation_results = evaluation
                
                # Overall Status
                if evaluation['design_check']['overall_adequate']:
                    st.markdown(f"""
                    <div class="success-box">
                    <h3>✅ DESIGN STATUS: ADEQUATE</h3>
                    <p><b>Moment Utilization:</b> {evaluation['flexural']['ratio']:.3f}</p>
                    <p><b>Axial Utilization:</b> {evaluation['compression']['ratio']:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="error-box">
                    <h3>❌ DESIGN STATUS: INADEQUATE</h3>
                    <p><b>Moment Utilization:</b> {evaluation['flexural']['ratio']:.3f}</p>
                    <p><b>Axial Utilization:</b> {evaluation['compression']['ratio']:.3f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detailed Results
                col_r1, col_r2 = st.columns(2)
                
                with col_r1:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("#### Flexural Analysis (F2)")
                    st.metric("φMn", f"{evaluation['flexural']['phi_Mn']:.2f} t·m")
                    st.metric("Utilization", f"{evaluation['flexural']['ratio']:.3f}")
                    st.write(f"**Zone:** {evaluation['flexural']['zone']}")
                    st.write(f"**Lp:** {evaluation['flexural']['Lp']:.3f} m")
                    st.write(f"**Lr:** {evaluation['flexural']['Lr']:.3f} m")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_r2:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("#### Compression Analysis (E3)")
                    st.metric("φPn", f"{evaluation['compression']['phi_Pn']:.2f} tons")
                    st.metric("Utilization", f"{evaluation['compression']['ratio']:.3f}")
                    st.write(f"**Mode:** {evaluation['compression']['mode']}")
                    st.write(f"**λc:** {evaluation['compression']['lambda_c']:.1f}")
                    st.write(f"**Fcr:** {evaluation['compression']['Fcr']:.1f} kgf/cm²")
                    st.markdown('</div>', unsafe_allow_html=True)
        
        # Export Section
        st.markdown("---")
        st.markdown("### 📥 Export Calculation Reports")
        
        if st.session_state.evaluation_results:
            col_export1, col_export2 = st.columns(2)
            
            # PDF Export
            with col_export1:
                if PDF_AVAILABLE:
                    if st.button("📄 Generate Professional PDF Report", type="primary"):
                        design_params = {
                            'Mu': Mu_eval, 'Pu': Pu_eval,
                            'Lb': Lb_eval, 'KL': KL_eval,
                            'Cb': 1.0
                        }
                        
                        with st.spinner('Generating professional PDF report...'):
                            pdf_buffer = generate_professional_pdf_report(
                                df, df_mat, section, selected_material, 
                                st.session_state.evaluation_results, design_params
                            )
                        
                        if pdf_buffer:
                            st.download_button(
                                label="📥 Download Professional PDF Report",
                                data=pdf_buffer,
                                file_name=f"AISC_Professional_Report_{section}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf"
                            )
                            st.success("✅ Professional PDF report generated successfully!")
                else:
                    st.warning("⚠️ PDF export requires reportlab and matplotlib libraries")
                    st.code("pip install reportlab matplotlib")
            
            # Excel Export
            with col_export2:
                if EXCEL_AVAILABLE:
                    if st.button("📊 Generate Enhanced Excel Report", type="primary"):
                        design_params = {
                            'Mu': Mu_eval, 'Pu': Pu_eval,
                            'Lb': Lb_eval, 'KL': KL_eval,
                            'Cb': 1.0
                        }
                        
                        with st.spinner('Generating enhanced Excel report...'):
                            excel_buffer = generate_enhanced_excel_report(
                                df, df_mat, section, selected_material, 
                                st.session_state.evaluation_results, design_params
                            )
                        
                        if excel_buffer:
                            st.download_button(
                                label="📥 Download Enhanced Excel Report",
                                data=excel_buffer,
                                file_name=f"AISC_Enhanced_Report_{section}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            st.success("✅ Enhanced Excel report with detailed calculations generated successfully!")
                else:
                    st.warning("⚠️ Excel export requires openpyxl library")
                    st.code("pip install openpyxl")
        else:
            st.info("ℹ️ Perform a design evaluation first to enable export functionality")

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
