# ==================== ENHANCED AISC 360-16 STEEL DESIGN WEB APP ====================
# Version: 6.0 - Advanced Design Evaluation & Calculation Reports
# Enhanced Features: Design Summary, Critical Lengths Display, Calculation Notes

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import math
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from datetime import datetime
import io

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="AISC 360-16 Steel Design Professional",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== ENHANCED CSS ====================
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 0.5rem;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: white;
        border-radius: 8px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #0066cc;
        color: white;
    }
    
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a237e;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    
    .section-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #283593;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }
    
    .evaluation-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .critical-lengths-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .calculation-note {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        margin: 1rem 0;
    }
    
    .aisc-equation {
        background-color: #e7f3ff;
        border-left: 4px solid #2196f3;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
    
    .design-summary {
        background: #ffffff;
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .info-box {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .success-box {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .warning-box {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    .error-box {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
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
if 'section_lb_values' not in st.session_state:
    st.session_state.section_lb_values = {}
if 'calculation_report' not in st.session_state:
    st.session_state.calculation_report = ""

# ==================== HELPER FUNCTIONS ====================
@st.cache_data
def load_data():
    """Load steel section and material databases"""
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        return df, df_mat, True
    except Exception as e:
        st.error(f"Error loading data: {e}")
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

def safe_max(a, b):
    """Safe max function that handles numpy arrays"""
    return max(safe_scalar(a), safe_scalar(b))

def safe_min(a, b):
    """Safe min function that handles numpy arrays"""
    return min(safe_scalar(a), safe_scalar(b))

def safe_sqrt(value):
    """Safe square root that ensures non-negative input"""
    val = safe_scalar(value)
    return math.sqrt(abs(val)) if val >= 0 else 0.0

# ==================== ENHANCED DESIGN EVALUATION FUNCTION ====================
def evaluate_section_design(df, df_mat, section, material, design_loads, design_lengths):
    """
    Advanced section evaluation function that provides comprehensive design assessment
    
    Args:
        df: Section database
        df_mat: Material database
        section: Section name
        material: Material grade
        design_loads: Dict with Mu, Pu values
        design_lengths: Dict with Lb, KLx, KLy values
    
    Returns:
        Comprehensive evaluation dictionary
    """
    try:
        # Get basic properties
        weight = safe_scalar(df.loc[section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in df.columns else df.loc[section, 'w [kg/m]'])
        Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
        Sx = safe_scalar(df.loc[section, 'Sx [cm3]'])
        Ix = safe_scalar(df.loc[section, 'Ix [cm4]'])
        Iy = safe_scalar(df.loc[section, 'Iy [cm4]'])
        rx = safe_scalar(df.loc[section, 'rx [cm]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        # Material properties
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        
        # Flexural analysis
        flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section, material, design_lengths['Lb'])
        
        # Compression analysis  
        comp_result = aisc_360_16_e3_compression_design(df, df_mat, section, material, 
                                                       design_lengths['KLx'], design_lengths['KLy'])
        
        # Calculate efficiency metrics
        if flex_result and comp_result:
            phi_Mn = 0.9 * flex_result['Mn']
            phi_Pn = comp_result['phi_Pn']
            
            # Design ratios
            moment_ratio = design_loads['Mu'] / phi_Mn if phi_Mn > 0 else 999
            axial_ratio = design_loads['Pu'] / phi_Pn if phi_Pn > 0 else 999
            
            # Efficiency metrics
            moment_efficiency = phi_Mn / weight if weight > 0 else 0
            compression_efficiency = phi_Pn / weight if weight > 0 else 0
            
            # Overall assessment
            flexural_adequate = moment_ratio <= 1.0
            compression_adequate = axial_ratio <= 1.0
            overall_adequate = flexural_adequate and compression_adequate
            
            # Critical lengths assessment
            Lp = flex_result['Lp']
            Lr = flex_result['Lr'] 
            current_Lb = design_lengths['Lb']
            
            if current_Lb <= Lp:
                flexural_zone = "Yielding (F2.1)"
                flexural_status = "Optimal"
            elif current_Lb <= Lr:
                flexural_zone = "Inelastic LTB (F2.2)"
                flexural_status = "Good"
            else:
                flexural_zone = "Elastic LTB (F2.3)"
                flexural_status = "Check if acceptable"
            
            return {
                'section': section,
                'material': material,
                'weight': weight,
                'properties': {
                    'Zx': Zx, 'Sx': Sx, 'Ix': Ix, 'Iy': Iy, 'rx': rx, 'ry': ry
                },
                'flexural': {
                    'Mn': flex_result['Mn'],
                    'phi_Mn': phi_Mn,
                    'Mp': flex_result['Mp'],
                    'Lp': Lp,
                    'Lr': Lr,
                    'case': flex_result['Case'],
                    'zone': flexural_zone,
                    'status': flexural_status,
                    'ratio': moment_ratio,
                    'adequate': flexural_adequate,
                    'efficiency': moment_efficiency
                },
                'compression': {
                    'Pn': comp_result['Pn'],
                    'phi_Pn': phi_Pn,
                    'Fcr': comp_result['Fcr'],
                    'lambda_c': comp_result['lambda_c'],
                    'mode': comp_result['buckling_mode'],
                    'ratio': axial_ratio,
                    'adequate': compression_adequate,
                    'efficiency': compression_efficiency
                },
                'design_check': {
                    'overall_adequate': overall_adequate,
                    'moment_utilization': moment_ratio,
                    'axial_utilization': axial_ratio,
                    'safety_factor_moment': 1/moment_ratio if moment_ratio > 0 else float('inf'),
                    'safety_factor_axial': 1/axial_ratio if axial_ratio > 0 else float('inf')
                }
            }
    except Exception as e:
        st.error(f"Error in section evaluation: {e}")
        return None

# ==================== CALCULATION REPORT GENERATOR ====================
def generate_calculation_report(df, df_mat, section, material, analysis_type, parameters, results):
    """
    Generate detailed calculation report with AISC equations and step-by-step calculations
    """
    report = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Header
    report.append("=" * 80)
    report.append("AISC 360-16 STEEL DESIGN CALCULATION REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {timestamp}")
    report.append(f"Section: {section}")
    report.append(f"Material: {material}")
    report.append(f"Analysis: {analysis_type}")
    report.append("")
    
    # Material Properties
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    Fu = safe_scalar(df_mat.loc[material, "Tensile Strength (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    report.append("MATERIAL PROPERTIES:")
    report.append("-" * 40)
    report.append(f"Steel Grade: {material}")
    report.append(f"Yield Strength, Fy = {Fy:.1f} kgf/cm²")
    report.append(f"Tensile Strength, Fu = {Fu:.1f} kgf/cm²") 
    report.append(f"Modulus of Elasticity, E = {E:.0f} kgf/cm²")
    report.append("")
    
    # Section Properties
    report.append("SECTION PROPERTIES:")
    report.append("-" * 40)
    props = ['d [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 'A [cm2]', 
             'Ix [cm4]', 'Iy [cm4]', 'Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]',
             'rx [cm]', 'ry [cm]']
    
    for prop in props:
        if prop in df.columns:
            value = safe_scalar(df.loc[section, prop])
            report.append(f"{prop.split('[')[0].strip():<4} = {value:.2f} {prop.split('[')[1].replace(']','') if '[' in prop else ''}")
    
    report.append("")
    
    # Analysis-specific calculations
    if analysis_type == "Flexural Design (F2)":
        report.extend(_generate_f2_calculations(df, df_mat, section, material, parameters, results))
    elif analysis_type == "Compression Design (E3)":
        report.extend(_generate_e3_calculations(df, df_mat, section, material, parameters, results))
    elif analysis_type == "Combined Forces (H1)":
        report.extend(_generate_h1_calculations(df, df_mat, section, material, parameters, results))
    
    # Footer
    report.append("")
    report.append("=" * 80)
    report.append("END OF CALCULATION REPORT")
    report.append("=" * 80)
    
    return "\n".join(report)

def _generate_f2_calculations(df, df_mat, section, material, parameters, results):
    """Generate F2 flexural design calculations"""
    calc = []
    
    # Get parameters
    Lb = parameters.get('Lb', 0)
    Cb = parameters.get('Cb', 1.0)
    
    # Section properties
    Sx = safe_scalar(df.loc[section, "Sx [cm3]"])
    Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
    ry = safe_scalar(df.loc[section, 'ry [cm]'])
    
    # Material
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    calc.append("AISC 360-16 CHAPTER F2 - LATERAL-TORSIONAL BUCKLING ANALYSIS:")
    calc.append("=" * 60)
    calc.append("")
    
    calc.append("INPUT PARAMETERS:")
    calc.append(f"Unbraced Length, Lb = {Lb:.2f} m")
    calc.append(f"Lateral-torsional buckling modification factor, Cb = {Cb:.2f}")
    calc.append("")
    
    # Step 1: Calculate Lp
    calc.append("STEP 1: Calculate limiting laterally unbraced length for yielding")
    calc.append("AISC 360-16 Equation F2.5:")
    calc.append("Lp = 1.76 * ry * √(E/Fy)")
    Lp = 1.76 * ry * safe_sqrt(E / Fy) / 100.0
    calc.append(f"Lp = 1.76 × {ry:.2f} × √({E:.0f}/{Fy:.1f})")
    calc.append(f"Lp = {Lp:.3f} m")
    calc.append("")
    
    # Step 2: Calculate Lr (simplified for report)
    calc.append("STEP 2: Calculate limiting laterally unbraced length for inelastic LTB")
    calc.append("AISC 360-16 Equation F2.6 (complex equation - see code for full implementation)")
    if results:
        Lr = results.get('Lr', 0)
        calc.append(f"Lr = {Lr:.3f} m")
    calc.append("")
    
    # Step 3: Calculate Mp
    calc.append("STEP 3: Calculate plastic moment")
    calc.append("Mp = Fy × Zx")
    Mp = Fy * Zx
    calc.append(f"Mp = {Fy:.1f} × {Zx:.1f} = {Mp:.0f} kgf⋅cm")
    Mp_tm = Mp / 100000
    calc.append(f"Mp = {Mp_tm:.3f} t⋅m")
    calc.append("")
    
    # Step 4: Determine case and calculate Mn
    calc.append("STEP 4: Determine applicable case and calculate nominal moment")
    if results:
        case = results.get('Case', '')
        Mn = results.get('Mn', 0)
        
        if Lb <= Lp:
            calc.append("Since Lb ≤ Lp:")
            calc.append("AISC 360-16 F2.1 - Yielding limit state applies")
            calc.append("Mn = Mp")
        elif results and Lb <= results.get('Lr', float('inf')):
            calc.append("Since Lp < Lb ≤ Lr:")
            calc.append("AISC 360-16 F2.2 - Inelastic lateral-torsional buckling applies")
            calc.append("Mn = Cb × [Mp - (Mp - 0.7×Fy×Sx) × (Lb - Lp)/(Lr - Lp)] ≤ Mp")
        else:
            calc.append("Since Lb > Lr:")
            calc.append("AISC 360-16 F2.3 - Elastic lateral-torsional buckling applies")
            calc.append("Mn = Fcr × Sx ≤ Mp")
        
        calc.append(f"Case: {case}")
        calc.append(f"Mn = {Mn:.3f} t⋅m")
    
    calc.append("")
    calc.append("STEP 5: Calculate design moment")
    calc.append("φMn = φ × Mn")
    calc.append("φ = 0.90 (AISC 360-16 F1)")
    if results:
        phi_Mn = 0.9 * results.get('Mn', 0)
        calc.append(f"φMn = 0.90 × {results.get('Mn', 0):.3f} = {phi_Mn:.3f} t⋅m")
    
    return calc

def _generate_e3_calculations(df, df_mat, section, material, parameters, results):
    """Generate E3 compression design calculations"""
    calc = []
    
    # Get parameters
    KLx = parameters.get('KLx', 0)
    KLy = parameters.get('KLy', 0)
    
    # Section properties
    Ag = safe_scalar(df.loc[section, 'A [cm2]'])
    rx = safe_scalar(df.loc[section, 'rx [cm]'])
    ry = safe_scalar(df.loc[section, 'ry [cm]'])
    
    # Material
    Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
    E = safe_scalar(df_mat.loc[material, "E"])
    
    calc.append("AISC 360-16 CHAPTER E3 - FLEXURAL BUCKLING ANALYSIS:")
    calc.append("=" * 60)
    calc.append("")
    
    calc.append("INPUT PARAMETERS:")
    calc.append(f"Effective length about x-axis, KLx = {KLx:.2f} m")
    calc.append(f"Effective length about y-axis, KLy = {KLy:.2f} m")
    calc.append("")
    
    # Step 1: Calculate slenderness ratios
    calc.append("STEP 1: Calculate slenderness ratios")
    lambda_x = (KLx * 100) / rx
    lambda_y = (KLy * 100) / ry
    lambda_c = max(lambda_x, lambda_y)
    
    calc.append(f"λx = KLx / rx = {KLx*100:.1f} / {rx:.2f} = {lambda_x:.1f}")
    calc.append(f"λy = KLy / ry = {KLy*100:.1f} / {ry:.2f} = {lambda_y:.1f}")
    calc.append(f"λc = max(λx, λy) = {lambda_c:.1f}")
    calc.append("")
    
    # Step 2: Check slenderness limit
    calc.append("STEP 2: Check slenderness limit per AISC 360-16 E2")
    calc.append("KL/r ≤ 200")
    if lambda_c <= 200:
        calc.append(f"λc = {lambda_c:.1f} ≤ 200 ✓ OK")
    else:
        calc.append(f"λc = {lambda_c:.1f} > 200 ✗ EXCEEDS LIMIT")
    calc.append("")
    
    # Step 3: Determine buckling mode
    calc.append("STEP 3: Determine buckling mode")
    lambda_limit = 4.71 * safe_sqrt(E / Fy)
    calc.append("Transition point: 4.71√(E/Fy)")
    calc.append(f"4.71√({E:.0f}/{Fy:.1f}) = {lambda_limit:.1f}")
    calc.append("")
    
    # Step 4: Calculate critical stress
    calc.append("STEP 4: Calculate critical stress")
    Fe = (math.pi**2 * E) / (lambda_c**2)
    calc.append("AISC 360-16 Equation E3.4:")
    calc.append("Fe = π²E / λc²")
    calc.append(f"Fe = π² × {E:.0f} / {lambda_c:.1f}² = {Fe:.1f} kgf/cm²")
    calc.append("")
    
    if lambda_c <= lambda_limit:
        calc.append("Since λc ≤ 4.71√(E/Fy):")
        calc.append("AISC 360-16 E3.2(a) - Inelastic buckling")
        calc.append("Fcr = [0.658^(Fy/Fe)] × Fy")
        Fcr = (0.658**(Fy/Fe)) * Fy
        calc.append(f"Fcr = [0.658^({Fy:.1f}/{Fe:.1f})] × {Fy:.1f} = {Fcr:.1f} kgf/cm²")
    else:
        calc.append("Since λc > 4.71√(E/Fy):")
        calc.append("AISC 360-16 E3.2(b) - Elastic buckling")
        calc.append("Fcr = 0.877 × Fe")
        Fcr = 0.877 * Fe
        calc.append(f"Fcr = 0.877 × {Fe:.1f} = {Fcr:.1f} kgf/cm²")
    
    calc.append("")
    
    # Step 5: Calculate nominal strength
    calc.append("STEP 5: Calculate nominal compressive strength")
    calc.append("AISC 360-16 E3.1:")
    calc.append("Pn = Fcr × Ag")
    Pn = Fcr * Ag / 1000
    calc.append(f"Pn = {Fcr:.1f} × {Ag:.1f} / 1000 = {Pn:.2f} tons")
    calc.append("")
    
    calc.append("STEP 6: Calculate design strength")
    calc.append("φPn = φc × Pn")
    calc.append("φc = 0.90 (AISC 360-16 E1)")
    phi_Pn = 0.9 * Pn
    calc.append(f"φPn = 0.90 × {Pn:.2f} = {phi_Pn:.2f} tons")
    
    return calc

def _generate_h1_calculations(df, df_mat, section, material, parameters, results):
    """Generate H1 interaction calculations"""
    calc = []
    
    calc.append("AISC 360-16 CHAPTER H1 - COMBINED FORCES ANALYSIS:")
    calc.append("=" * 60)
    calc.append("")
    
    # Add H1 specific calculations here
    calc.append("H1 interaction equations and calculations...")
    calc.append("(Implementation details for H1 analysis)")
    
    return calc

# ==================== AISC 360-16 DESIGN FUNCTIONS ====================
def aisc_360_16_f2_flexural_design(df, df_mat, section, material, Lb_input, Cb=1.0):
    """AISC 360-16 F2 - Lateral-Torsional Buckling Analysis"""
    try:
        # Get section properties and ensure they are scalars
        Sx = safe_scalar(df.loc[section, "Sx [cm3]"])
        Zx = safe_scalar(df.loc[section, 'Zx [cm3]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        # Handle rts
        if 'rts [cm]' in df.columns:
            rts = safe_scalar(df.loc[section, 'rts [cm]'])
        else:
            rts = ry * 1.2
        
        # Torsional properties
        J = safe_scalar(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 1.0
        
        # Distance between flange centroids
        if 'ho [mm]' in df.columns:
            ho = safe_scalar(df.loc[section, 'ho [mm]']) / 10.0
        else:
            ho = safe_scalar(df.loc[section, 'd [mm]']) / 10.0
        
        # Material properties
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        # Convert input to scalar
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
        
        # Plastic moment capacity
        Mp = Fy * Zx
        
        # Single point calculation
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
            Mn = safe_min(Mp, Mn)
        else:
            Case = "F2.3 - Elastic LTB"
            Lb_cm = Lb * 100.0
            Lb_rts_ratio = Lb_cm / rts
            
            term_1 = (Cb * math.pi**2 * E) / (Lb_rts_ratio**2)
            term_2 = 0.078 * (J * c / (Sx * ho)) * (Lb_rts_ratio**2)
            Fcr = term_1 * safe_sqrt(1.0 + term_2)
            
            Mn = Fcr * Sx
            Mn = safe_min(Mp, Mn)
        
        # Convert to t⋅m
        Mn_tm = Mn / 100000.0
        Mp_tm = Mp / 100000.0
        
        # Generate curve data
        Lb_points = []
        Mn_points = []
        
        max_Lb = safe_max(15.0, Lr + 5.0)
        n_points = 200
        step = (max_Lb - 0.1) / (n_points - 1)
        
        for i in range(n_points):
            Lb_point = 0.1 + i * step
            Lb_points.append(Lb_point)
            
            if Lb_point <= Lp:
                Mn_point = Mp
            elif Lb_point <= Lr:
                Lb_point_cm = Lb_point * 100.0
                Lp_cm = Lp * 100.0
                Lr_cm = Lr * 100.0
                
                Mp_minus_Mr = Mp - 0.7 * Fy * Sx
                length_ratio = (Lb_point_cm - Lp_cm) / (Lr_cm - Lp_cm)
                Mn_point = Cb * (Mp - Mp_minus_Mr * length_ratio)
                Mn_point = safe_min(Mp, Mn_point)
            else:
                Lb_point_cm = Lb_point * 100.0
                Lb_rts_ratio = Lb_point_cm / rts
                
                term_1 = (Cb * math.pi**2 * E) / (Lb_rts_ratio**2)
                term_2 = 0.078 * (J * c / (Sx * ho)) * (Lb_rts_ratio**2)
                Fcr = term_1 * safe_sqrt(1.0 + term_2)
                
                Mn_point = Fcr * Sx
                Mn_point = safe_min(Mp, Mn_point)
            
            Mn_point_tm = Mn_point / 100000.0
            Mn_points.append(safe_max(0.0, Mn_point_tm))
        
        return {
            'Mn': Mn_tm,
            'Mp': Mp_tm,
            'Lp': Lp,
            'Lr': Lr, 
            'Case': Case,
            'Lb_range': Lb_points,
            'Mn_curve': Mn_points,
            'Cb': Cb
        }
        
    except Exception as e:
        st.error(f"Error in AISC 360-16 F2 calculation: {str(e)}")
        return None

def aisc_360_16_e3_compression_design(df, df_mat, section, material, KLx, KLy):
    """AISC 360-16 E3 - Flexural Buckling Analysis"""
    try:
        # Material properties
        Fy = safe_scalar(df_mat.loc[material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[material, "E"])
        
        # Section properties
        Ag = safe_scalar(df.loc[section, 'A [cm2]'])
        rx = safe_scalar(df.loc[section, 'rx [cm]'])
        ry = safe_scalar(df.loc[section, 'ry [cm]'])
        
        # Convert effective lengths
        KLx_scalar = safe_scalar(KLx) * 100.0
        KLy_scalar = safe_scalar(KLy) * 100.0
        
        # Calculate slenderness ratios
        lambda_x = KLx_scalar / rx
        lambda_y = KLy_scalar / ry
        lambda_c = safe_max(lambda_x, lambda_y)
        
        # AISC 360-16 Equation E3.4
        Fe = (math.pi**2 * E) / (lambda_c**2)
        
        # Determine buckling mode
        lambda_limit = 4.71 * safe_sqrt(E / Fy)
        
        if lambda_c <= lambda_limit:
            buckling_mode = "Inelastic"
            exponent = Fy / Fe
            Fcr = (0.658 ** exponent) * Fy
        else:
            buckling_mode = "Elastic"
            Fcr = 0.877 * Fe
        
        # Nominal compressive strength
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
        # Convert all inputs to scalars
        Pu = safe_scalar(Pu)
        phi_Pn = safe_scalar(phi_Pn) 
        Mux = safe_scalar(Mux)
        phi_Mnx = safe_scalar(phi_Mnx)
        Muy = safe_scalar(Muy)
        phi_Mny = safe_scalar(phi_Mny)
        
        if phi_Pn <= 0.0 or phi_Mnx <= 0.0 or phi_Mny <= 0.0:
            return None
        
        # Calculate ratios
        Pr_Pc = Pu / phi_Pn
        Mrx_Mcx = Mux / phi_Mnx
        Mry_Mcy = Muy / phi_Mny
        
        # AISC 360-16 H1.1
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

# ==================== UTILITY FUNCTIONS ====================
def calculate_required_zx(Mu, Fy, phi=0.9):
    """Calculate required plastic section modulus"""
    Mu = safe_scalar(Mu)
    Fy = safe_scalar(Fy)
    phi = safe_scalar(phi)
    
    Mu_kgf_cm = Mu * 100000.0
    Zx_req = Mu_kgf_cm / (phi * Fy)
    return Zx_req

def calculate_required_ix(w, L, delta_limit, E=2.04e6):
    """Calculate required moment of inertia"""
    w = safe_scalar(w)
    L = safe_scalar(L)
    delta_limit = safe_scalar(delta_limit)
    E = safe_scalar(E)
    
    w_kgf_cm = w / 100.0
    L_cm = L * 100.0
    delta_max = L_cm / delta_limit
    
    Ix_req = (5.0 * w_kgf_cm * L_cm**4) / (384.0 * E * delta_max)
    return Ix_req

def visualize_column_simple(df, section):
    """Simplified column visualization"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 8))
        
        d = safe_scalar(df.loc[section, 'd [mm]'])
        bf = safe_scalar(df.loc[section, 'bf [mm]'])
        tw = safe_scalar(df.loc[section, 'tw [mm]'])
        tf = safe_scalar(df.loc[section, 'tf [mm]'])
        
        H = 3000
        
        # Strong axis buckling
        ax1.set_title('Strong Axis Buckling (X-X)\nEdge View', fontsize=14, fontweight='bold')
        
        ax1.add_patch(Rectangle((-tf/2, 0), tf, tf, 
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        ax1.add_patch(Rectangle((-tw/2, tf), tw, H - 2*tf,
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        ax1.add_patch(Rectangle((-tf/2, H - tf), tf, tf,
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        
        y_vals = [i for i in range(0, H+1, H//100)]
        x_buckled = [80 * math.sin(math.pi * y / H) for y in y_vals]
        ax1.plot(x_buckled, y_vals, 'r-', lw=3, label='Buckled Shape')
        
        ax1.arrow(0, H + 100, 0, -80, head_width=20, head_length=40, fc='red', ec='red')
        ax1.text(0, H + 150, 'P', ha='center', fontsize=14, fontweight='bold', color='red')
        ax1.text(50, H/2, f'd = {d:.0f}mm', rotation=90, ha='center', fontsize=10)
        
        ax1.set_xlim([-150, 150])
        ax1.set_ylim([-50, H + 200])
        ax1.set_xlabel('Buckling Direction')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Weak axis buckling
        ax2.set_title('Weak Axis Buckling (Y-Y)\nFront View', fontsize=14, fontweight='bold')
        
        ax2.add_patch(Rectangle((-bf/2, 0), bf, tf,
                                linewidth=2, edgecolor='darkred', facecolor='lightcoral', alpha=0.7))
        ax2.add_patch(Rectangle((-bf/2, H - tf), bf, tf,
                                linewidth=2, edgecolor='darkred', facecolor='lightcoral', alpha=0.7))
        ax2.plot([0, 0], [tf, H - tf], 'k-', lw=2, alpha=0.5, label='Web (edge)')
        
        x_buckled_weak = [50 * math.sin(math.pi * y / H) for y in y_vals]
        ax2.plot(x_buckled_weak, y_vals, color='darkred', lw=3, label='Buckled Shape')
        
        ax2.arrow(0, H + 100, 0, -80, head_width=bf/8, head_length=40, fc='red', ec='red')
        ax2.text(0, H + 150, 'P', ha='center', fontsize=14, fontweight='bold', color='red')
        ax2.text(0, H + 50, f'bf = {bf:.0f}mm', ha='center', fontsize=10)
        
        ax2.set_xlim([-bf*0.7, bf*0.7])
        ax2.set_ylim([-50, H + 200])
        ax2.set_xlabel('Buckling Direction')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        plt.suptitle(f'Column Buckling Analysis - Section: {section}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Error in visualization: {e}")
        return None

# ==================== LOAD DATA ====================
df, df_mat, success = load_data()

if not success:
    st.error("Failed to load data. Please check your internet connection.")
    st.stop()

# ==================== MAIN HEADER ====================
st.markdown('<h1 class="main-header">AISC 360-16 Steel Design Professional v6.0</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84;">Advanced Design Evaluation & Calculation Reports</p>', unsafe_allow_html=True)

# ==================== ENHANCED SIDEBAR ====================
with st.sidebar:
    st.markdown("### Design Configuration")
    
    material_list = list(df_mat.index)
    selected_material = st.selectbox(
        "Steel Grade:",
        material_list,
        index=0,
        help="Select steel material grade per AISC 360-16"
    )
    st.session_state.selected_material = selected_material
    
    if selected_material:
        Fy = df_mat.loc[selected_material, "Yield Point (ksc)"]
        Fu = df_mat.loc[selected_material, "Tensile Strength (ksc)"]
        st.info(f"""
        **Selected Grade: {selected_material}**
        - Fy = {Fy} ksc
        - Fu = {Fu} ksc
        - E = 2.04×10⁶ ksc
        """)
    
    st.markdown("---")
    
    section_list = list(df.index)
    quick_section = st.selectbox(
        "Section Selection:",
        ["None"] + section_list,
        help="Quick select a specific section"
    )
    
    if quick_section != "None":
        st.session_state.selected_section = quick_section
        weight = df.loc[quick_section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in df.columns else df.loc[quick_section, 'w [kg/m]']
        st.success(f"""
        **{quick_section}**
        - Weight: {weight:.1f} kg/m
        - Zx: {df.loc[quick_section, 'Zx [cm3]']:.0f} cm³
        """)
        
        # Enhanced Critical Lengths Display
        if selected_material:
            st.markdown("---")
            st.markdown('<div class="critical-lengths-box">', unsafe_allow_html=True)
            st.markdown("### Critical Lengths Preview")
            
            # Calculate critical lengths for quick preview
            try:
                preview_result = aisc_360_16_f2_flexural_design(df, df_mat, quick_section, selected_material, 3.0)
                if preview_result:
                    st.write(f"**Lp = {preview_result['Lp']:.2f} m**")
                    st.caption("Yielding limit (F2.5)")
                    st.write(f"**Lr = {preview_result['Lr']:.2f} m**")
                    st.caption("Inelastic LTB limit (F2.6)")
                    
                    # Zone classification for Lb = 3m
                    if 3.0 <= preview_result['Lp']:
                        st.success("✅ Yielding zone at Lb=3m")
                    elif 3.0 <= preview_result['Lr']:
                        st.warning("⚠️ Inelastic LTB zone at Lb=3m")
                    else:
                        st.error("❌ Elastic LTB zone at Lb=3m")
            except:
                st.error("Error calculating critical lengths")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ==================== ENHANCED TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Section Properties",
    "🔍 Section Selection", 
    "📈 Flexural Design (F2)",
    "🏢 Column Design (E3)",
    "🏗️ Beam-Column (H1)",
    "📊 Comparison",
    "📋 Design Evaluation"
])

# ==================== TAB 1: ENHANCED SECTION PROPERTIES ====================
with tab1:
    st.markdown('<h2 class="section-header">Complete Section Properties & AISC References</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section:
        section = st.session_state.selected_section
        st.info(f"**Properties for: {section}**")
        
        section_data = df.loc[section]
        properties_df = pd.DataFrame({
            'Property': section_data.index,
            'Value': section_data.values
        })
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Geometric Properties")
            geo_props = ['d [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 'A [cm2]', 
                        'Unit Weight [kg/m]', 'w [kg/m]']
            geo_df = properties_df[properties_df['Property'].isin([p for p in geo_props if p in properties_df['Property'].values])]
            st.dataframe(geo_df, use_container_width=True, hide_index=True)
            
            st.markdown("#### Section Moduli")
            mod_props = ['Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]']
            mod_df = properties_df[properties_df['Property'].isin([p for p in mod_props if p in properties_df['Property'].values])]
            st.dataframe(mod_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### Moment of Inertia")
            inertia_props = ['Ix [cm4]', 'Iy [cm4]', 'rx [cm]', 'ry [cm]']
            inertia_df = properties_df[properties_df['Property'].isin([p for p in inertia_props if p in properties_df['Property'].values])]
            st.dataframe(inertia_df, use_container_width=True, hide_index=True)
            
            st.markdown("#### Stability Properties")
            stab_props = ['Lp [cm]', 'Lr [cm]', 'j [cm4]', 'ho [mm]', 'rts [cm6]', 'rts [cm]']
            stab_df = properties_df[properties_df['Property'].isin([p for p in stab_props if p in properties_df['Property'].values])]
            if not stab_df.empty:
                st.dataframe(stab_df, use_container_width=True, hide_index=True)
        
        # Enhanced Critical Lengths Analysis
        if selected_material:
            st.markdown("### AISC 360-16 Critical Lengths Analysis")
            
            try:
                # Calculate for multiple Cb values
                cb_values = [1.0, 1.14, 1.67, 2.27]
                critical_data = []
                
                for cb in cb_values:
                    result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, 3.0, cb)
                    if result:
                        critical_data.append({
                            'Cb': cb,
                            'Lp (m)': result['Lp'],
                            'Lr (m)': result['Lr'],
                            'Mp (t⋅m)': result['Mp'],
                            'Mn at 3m (t⋅m)': result['Mn']
                        })
                
                if critical_data:
                    critical_df = pd.DataFrame(critical_data)
                    st.dataframe(critical_df.round(3), use_container_width=True, hide_index=True)
                    
                    st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
                    st.markdown("**AISC 360-16 Equations:**")
                    st.markdown("- **F2.5:** Lp = 1.76 × ry × √(E/Fy)")
                    st.markdown("- **F2.6:** Lr = complex equation involving rts, J, Sx, ho")
                    st.markdown('</div>', unsafe_allow_html=True)
            except:
                st.error("Error in critical lengths analysis")
        
        with st.expander("📋 View All Properties with AISC References"):
            # Enhanced properties table with AISC references
            enhanced_props = properties_df.copy()
            enhanced_props['AISC Use'] = enhanced_props['Property'].map({
                'Zx [cm3]': 'Plastic moment Mp = Fy × Zx (F2)',
                'Sx [cm3]': 'Elastic moment, LTB calculations (F2)',
                'Ix [cm4]': 'Deflection calculations',
                'Iy [cm4]': 'Weak axis bending',
                'rx [cm]': 'Strong axis slenderness λx = KLx/rx (E3)',
                'ry [cm]': 'Weak axis slenderness, Lp calculation (E3, F2)',
                'd [mm]': 'Overall depth',
                'bf [mm]': 'Flange width',
                'tw [mm]': 'Web thickness',
                'tf [mm]': 'Flange thickness',
                'A [cm2]': 'Compression strength Pn = Fcr × Ag (E3)'
            })
            st.dataframe(enhanced_props, use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a section from the sidebar")

# ==================== TAB 2: ENHANCED SECTION SELECTION ====================  
with tab2:
    st.markdown('<h2 class="section-header">Advanced Section Selection with AISC 360-16 Criteria</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Flexural Requirements (F2)")
        Mu = st.number_input("Design Moment Mu (t·m):", min_value=0.0, value=50.0, step=5.0)
        phi_f = 0.9
        
        if Mu > 0 and selected_material:
            Fy_value = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
            Zx_req = calculate_required_zx(Mu, Fy_value, phi_f)
            st.success(f"Required Zx ≥ {Zx_req:.0f} cm³")
            
            st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
            st.markdown("**AISC F2.1:** Mn = Mp = Fy × Zx")
            st.markdown(f"Required: Zx ≥ Mu/(φ×Fy) = {Mu}/(0.9×{Fy_value}) = {Zx_req:.0f} cm³")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### Deflection Control")
        L_span = st.number_input("Span Length (m):", min_value=1.0, value=6.0, step=0.5)
        w_load = st.number_input("Service Load w (kg/m):", min_value=0.0, value=100.0, step=10.0)
        deflection_limit = st.selectbox("Deflection Limit:", 
                                       ["L/200", "L/250", "L/300", "L/360", "L/400"],
                                       index=2)
        
        if w_load > 0 and L_span > 0:
            limit_value = safe_scalar(deflection_limit.split('/')[1])
            Ix_req = calculate_required_ix(w_load, L_span, limit_value)
            st.success(f"Required Ix ≥ {Ix_req:.0f} cm⁴")
            
            st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
            st.markdown("**Deflection:** δ = 5wL⁴/(384EI)")
            st.markdown(f"Max δ = L/{limit_value} = {L_span*100/limit_value:.1f} cm")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("#### Advanced Filters")
        depth_max = st.number_input("Max Depth (mm):", min_value=0, value=0)
        weight_max = st.number_input("Max Weight (kg/m):", min_value=0, value=200, step=10)
        
        optimization = st.selectbox("Optimize for:",
                                   ["Minimum Weight", "Minimum Depth", "Maximum Efficiency", "Best Lp/Lr Ratio"],
                                   index=0)
    
    # Filter sections
    filtered_df = df.copy()
    
    if Mu > 0 and selected_material:
        Fy_value = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
        zx_min = calculate_required_zx(Mu, Fy_value, phi_f)
        filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= zx_min]
    
    if w_load > 0 and L_span > 0:
        limit_value = safe_scalar(deflection_limit.split('/')[1])
        Ix_req = calculate_required_ix(w_load, L_span, limit_value)
        filtered_df = filtered_df[filtered_df['Ix [cm4]'] >= Ix_req]
    
    if depth_max > 0:
        filtered_df = filtered_df[filtered_df['d [mm]'] <= depth_max]
    
    if weight_max > 0:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df = filtered_df[filtered_df[weight_col] <= weight_max]
    
    # Enhanced sorting with critical lengths
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
    
    if optimization == "Best Lp/Lr Ratio" and selected_material:
        # Calculate Lp/Lr ratio for each section
        lp_lr_ratios = []
        for idx in filtered_df.index:
            try:
                result = aisc_360_16_f2_flexural_design(df, df_mat, idx, selected_material, 3.0)
                if result and result['Lr'] > 0:
                    ratio = result['Lp'] / result['Lr']
                    lp_lr_ratios.append(ratio)
                else:
                    lp_lr_ratios.append(0)
            except:
                lp_lr_ratios.append(0)
        
        filtered_df['Lp_Lr_Ratio'] = lp_lr_ratios
        filtered_df = filtered_df.sort_values('Lp_Lr_Ratio', ascending=False)
    elif optimization == "Minimum Weight":
        filtered_df = filtered_df.sort_values(weight_col)
    elif optimization == "Minimum Depth":
        filtered_df = filtered_df.sort_values('d [mm]')
    else:  # Maximum Efficiency
        filtered_df['efficiency'] = filtered_df['Zx [cm3]'] / filtered_df[weight_col]
        filtered_df = filtered_df.sort_values('efficiency', ascending=False)
    
    st.markdown(f"### Found {len(filtered_df)} Suitable Sections")
    
    if len(filtered_df) > 0:
        # Enhanced display with critical lengths
        if st.checkbox("Show Critical Lengths (Lp, Lr)", value=True):
            # Calculate critical lengths for filtered sections (top 10 for performance)
            display_sections = filtered_df.head(10).copy()
            
            if selected_material:
                lp_values = []
                lr_values = []
                
                for idx in display_sections.index:
                    try:
                        result = aisc_360_16_f2_flexural_design(df, df_mat, idx, selected_material, 3.0)
                        if result:
                            lp_values.append(result['Lp'])
                            lr_values.append(result['Lr'])
                        else:
                            lp_values.append(0)
                            lr_values.append(0)
                    except:
                        lp_values.append(0)
                        lr_values.append(0)
                
                display_sections['Lp [m]'] = lp_values
                display_sections['Lr [m]'] = lr_values
            
            filtered_df_display = display_sections.reset_index()
        else:
            filtered_df_display = filtered_df.reset_index()
        
        display_cols = ['Section', 'd [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 
                       'A [cm2]', weight_col, 'Ix [cm4]', 'Iy [cm4]', 
                       'Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]', 
                       'rx [cm]', 'ry [cm]']
        
        # Add critical lengths if calculated
        if 'Lp [m]' in filtered_df_display.columns:
            display_cols.extend(['Lp [m]', 'Lr [m]'])
        
        available_cols = [col for col in display_cols if col in filtered_df_display.columns]
        
        # Configure AgGrid for multi-selection
        gb = GridOptionsBuilder.from_dataframe(filtered_df_display[available_cols])
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        gb.configure_column("Section", headerCheckboxSelection=True)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        
        # Highlight critical length columns
        if 'Lp [m]' in available_cols:
            gb.configure_column("Lp [m]", cellStyle={'background-color': '#e8f5e9'})
            gb.configure_column("Lr [m]", cellStyle={'background-color': '#fff3e0'})
        
        grid_options = gb.build()
        
        st.markdown("#### 📋 AISC Database with Critical Lengths")
        grid_response = AgGrid(
            filtered_df_display[available_cols].round(3),
            gridOptions=grid_options,
            height=450,
            width='100%',
            theme='streamlit',
            update_mode=GridUpdateMode.SELECTION_CHANGED
        )
        
        # Handle selected rows
        selected_rows = grid_response.get('selected_rows', None)
        if selected_rows is not None and not selected_rows.empty:
            selected_sections = selected_rows['Section'].tolist()
            st.session_state.selected_sections = selected_sections
            
            st.success(f"Selected {len(selected_sections)} sections for AISC 360-16 analysis")

# ==================== TAB 3: ENHANCED FLEXURAL DESIGN ====================
with tab3:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter F2 - Enhanced Flexural Design</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Design Parameters")
            Lb_current = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
            Cb = st.number_input("Cb Factor:", 1.0, 2.3, 1.0, 0.1, 
                                help="AISC 360-16 F1 - Lateral-torsional buckling modification factor")
            
            show_phi = st.checkbox("Show φMn", value=True)
            show_mn = st.checkbox("Show Mn", value=True)
            show_regions = st.checkbox("Show AISC regions", value=True)
            
            # Generate calculation report button
            if st.button("Generate F2 Calculation Report"):
                result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_current, Cb)
                if result:
                    parameters = {'Lb': Lb_current, 'Cb': Cb}
                    report = generate_calculation_report(df, df_mat, section, selected_material, 
                                                       "Flexural Design (F2)", parameters, result)
                    st.session_state.calculation_report = report
                    st.success("Calculation report generated! Check the Design Evaluation tab.")
            
            # AISC F2 analysis
            result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_current, Cb)
            
            if result:
                st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 Results")
                st.metric("Mn", f"{result['Mn']:.2f} t·m")
                st.metric("φMn", f"{0.9*result['Mn']:.2f} t·m")
                st.metric("Design Case", result['Case'])
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Enhanced classification
                if result['Mn'] >= result['Mp'] * 0.98:
                    st.success("Full plastic capacity achieved")
                elif result['Mn'] >= result['Mp'] * 0.75:
                    st.warning("Moderate LTB reduction")
                else:
                    st.error("Significant LTB reduction")
                
                st.markdown('<div class="critical-lengths-box">', unsafe_allow_html=True)
                st.markdown("### Critical Lengths")
                st.write(f"**Lp = {result['Lp']:.3f} m**")
                st.caption("F2.5: Yielding limit")
                st.write(f"**Lr = {result['Lr']:.3f} m**") 
                st.caption("F2.6: Inelastic LTB limit")
                
                # Zone indicator
                if Lb_current <= result['Lp']:
                    st.success("Current Lb in YIELDING zone")
                elif Lb_current <= result['Lr']:
                    st.warning("Current Lb in INELASTIC LTB zone")
                else:
                    st.error("Current Lb in ELASTIC LTB zone")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # AISC equations display
                st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 Equations Applied")
                if result['Case'] == "F2.1 - Yielding":
                    st.markdown("**F2.1:** Mn = Mp = Fy × Zx")
                elif result['Case'] == "F2.2 - Inelastic LTB":
                    st.markdown("**F2.2:** Mn = Cb[Mp - (Mp - 0.7FySx)(Lb-Lp)/(Lr-Lp)] ≤ Mp")
                else:
                    st.markdown("**F2.3:** Mn = FcrSx where Fcr includes LTB effects")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            if result:
                fig = go.Figure()
                
                # Mn curve
                if show_mn:
                    fig.add_trace(go.Scatter(
                        x=result['Lb_range'], 
                        y=result['Mn_curve'],
                        mode='lines',
                        name='Mn (AISC F2)',
                        line=dict(color='#1976d2', width=3),
                        hovertemplate='Lb: %{x:.2f}m<br>Mn: %{y:.2f} t·m<extra></extra>'
                    ))
                
                # φMn curve  
                if show_phi:
                    phi_Mn_curve = [0.9 * m for m in result['Mn_curve']]
                    fig.add_trace(go.Scatter(
                        x=result['Lb_range'], 
                        y=phi_Mn_curve,
                        mode='lines',
                        name='φMn (φ=0.90)',
                        line=dict(color='#4caf50', width=2, dash='dash'),
                        hovertemplate='Lb: %{x:.2f}m<br>φMn: %{y:.2f} t·m<extra></extra>'
                    ))
                
                # Current design point
                fig.add_trace(go.Scatter(
                    x=[Lb_current], 
                    y=[result['Mn']],
                    mode='markers',
                    name=f'Design Point',
                    marker=dict(color='#f44336', size=15, symbol='diamond'),
                    hovertemplate=f'Lb: {Lb_current:.2f}m<br>Mn: {result["Mn"]:.2f} t·m<extra></extra>'
                ))
                
                # Mp line
                fig.add_hline(y=result['Mp'], line_dash="dot", line_color='#ff9800', line_width=2,
                            annotation_text=f"Mp = {result['Mp']:.2f} t·m")
                
                # Critical lengths
                fig.add_vline(x=result['Lp'], line_dash="dash", line_color='#9c27b0', line_width=3,
                            annotation_text=f"Lp = {result['Lp']:.3f} m")
                fig.add_vline(x=result['Lr'], line_dash="dash", line_color='#e91e63', line_width=3,
                            annotation_text=f"Lr = {result['Lr']:.3f} m")
                
                # Enhanced AISC regions
                if show_regions:
                    fig.add_vrect(x0=0, x1=result['Lp'], fillcolor='#4caf50', opacity=0.15,
                                annotation_text="<b>F2.1 YIELDING</b><br>Mn = Mp", 
                                annotation_position="top left", annotation_font_size=12)
                    fig.add_vrect(x0=result['Lp'], x1=result['Lr'], fillcolor='#ff9800', opacity=0.15,
                                annotation_text="<b>F2.2 INELASTIC LTB</b><br>Linear transition", 
                                annotation_position="top", annotation_font_size=12)
                    
                    max_x = result['Lb_range'][-1] if result['Lb_range'] else result['Lr'] + 5
                    fig.add_vrect(x0=result['Lr'], x1=max_x, fillcolor='#f44336', opacity=0.15,
                                annotation_text="<b>F2.3 ELASTIC LTB</b><br>Fcr based", 
                                annotation_position="top right", annotation_font_size=12)
                
                fig.update_layout(
                    title=f"AISC 360-16 F2: Enhanced Analysis - {section}",
                    xaxis_title="Unbraced Length, Lb (m)",
                    yaxis_title="Moment Capacity (t·m)",
                    height=650,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Enhanced summary with AISC references
                st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 Design Summary")
                summary_df = pd.DataFrame({
                    'Parameter': ['Mp', 'Mn', 'φMn', 'Lp', 'Lr', 'Lb', 'Cb', 'Case'],
                    'Value': [f"{result['Mp']:.3f} t·m", f"{result['Mn']:.3f} t·m", 
                             f"{0.9*result['Mn']:.3f} t·m", f"{result['Lp']:.3f} m", 
                             f"{result['Lr']:.3f} m", f"{Lb_current:.2f} m", f"{result['Cb']:.2f}",
                             result['Case']],
                    'AISC Ref': ['Fy×Zx', result['Case'], 'φ=0.90', 'Eq. F2.5', 'Eq. F2.6', 
                                'Input', 'F1', 'F2.1/F2.2/F2.3']
                })
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("Error in AISC F2 analysis")
    else:
        st.warning("Please select a section from the sidebar")

# Continue with other tabs...
# ==================== TAB 4: ENHANCED COLUMN DESIGN ====================
with tab4:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter E3 - Enhanced Column Design</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Effective Length Factors")
            Kx = st.selectbox("Kx:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4,
                             help="AISC Commentary Figure C-C2.2")
            Ky = st.selectbox("Ky:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            
            st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
            st.markdown("**K Factors:**")
            st.markdown("- 0.5: Fixed-Fixed")
            st.markdown("- 0.7: Fixed-Pinned")  
            st.markdown("- 1.0: Pinned-Pinned")
            st.markdown("- 2.0: Fixed-Free")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Unbraced Lengths")
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, step=0.1)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, step=0.1)
            
            # Slenderness ratios
            rx = safe_scalar(df.loc[section, 'rx [cm]'])
            ry = safe_scalar(df.loc[section, 'ry [cm]'])
            KLr_x = (Kx * Lx * 100) / rx
            KLr_y = (Ky * Ly * 100) / ry
            
            st.markdown('<div class="critical-lengths-box">', unsafe_allow_html=True)
            st.markdown("#### Slenderness Check")
            if KLr_x <= 200:
                st.success(f"KL/rx = {KLr_x:.1f} ✓")
            else:
                st.error(f"KL/rx = {KLr_x:.1f} > 200")
            
            if KLr_y <= 200:
                st.success(f"KL/ry = {KLr_y:.1f} ✓")
            else:
                st.error(f"KL/ry = {KLr_y:.1f} > 200")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown("#### Applied Load & Report")
            Pu = st.number_input("Pu (tons):", min_value=0.0, value=100.0, step=10.0)
            
            # Generate E3 calculation report
            if st.button("Generate E3 Report"):
                comp_results = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, Kx*Lx, Ky*Ly)
                if comp_results:
                    parameters = {'KLx': Kx*Lx, 'KLy': Ky*Ly, 'Pu': Pu}
                    report = generate_calculation_report(df, df_mat, section, selected_material, 
                                                       "Compression Design (E3)", parameters, comp_results)
                    st.session_state.calculation_report = report
                    st.success("E3 calculation report generated!")
        
        # AISC E3 analysis
        comp_results = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, Kx*Lx, Ky*Ly)
        
        if comp_results:
            st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
            st.markdown("### AISC 360-16 E3 Results")
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("φPn", f"{comp_results['phi_Pn']:.2f} tons", help="φc = 0.90")
            
            with col_r2:
                ratio = Pu / comp_results['phi_Pn'] if comp_results['phi_Pn'] > 0 else 999
                st.metric("Demand/Capacity", f"{ratio:.3f}",
                         delta="PASS" if ratio <= 1.0 else "FAIL")
            
            with col_r3:
                st.metric("Buckling Mode", comp_results['buckling_mode'],
                         delta=f"λc = {comp_results['lambda_c']:.1f}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Design check with enhanced feedback
            if ratio <= 1.0:
                st.success(f"AISC 360-16 Design PASSES - Safety Factor: {1/ratio:.2f}")
            else:
                st.error(f"AISC 360-16 Design FAILS - Overstressed by {(ratio-1)*100:.1f}%")
            
            # AISC equations display
            st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
            st.markdown("### AISC 360-16 Equations Applied")
            if comp_results['buckling_mode'] == "Inelastic":
                st.markdown("**E3.2(a):** Fcr = [0.658^(Fy/Fe)] × Fy")
                st.markdown(f"λc = {comp_results['lambda_c']:.1f} ≤ 4.71√(E/Fy) = {comp_results['lambda_limit']:.1f}")
            else:
                st.markdown("**E3.2(b):** Fcr = 0.877 × Fe")
                st.markdown(f"λc = {comp_results['lambda_c']:.1f} > 4.71√(E/Fy) = {comp_results['lambda_limit']:.1f}")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Enhanced visualization
        st.markdown("### Column Buckling Analysis")
        show_viz = st.checkbox("Show Buckling Diagram", value=True)
        
        if show_viz:
            fig_vis = visualize_column_simple(df, section)
            if fig_vis:
                st.pyplot(fig_vis)
        
        # Enhanced AISC E3 capacity curve with annotations
        st.markdown("### AISC 360-16 E3 Column Curve with Design Point")
        
        # Generate capacity curve
        lambda_points = []
        Pn_points = []
        
        Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
        E = safe_scalar(df_mat.loc[selected_material, "E"])
        Ag = safe_scalar(df.loc[section, 'A [cm2]'])
        
        lambda_limit = 4.71 * safe_sqrt(E / Fy)
        
        for i in range(250):
            lambda_c = 1.0 + i
            lambda_points.append(lambda_c)
            
            Fe = (math.pi**2 * E) / (lambda_c**2)
            
            if lambda_c <= lambda_limit:
                Fcr = (0.658**(Fy/Fe)) * Fy
            else:
                Fcr = 0.877 * Fe
            
            Pn = 0.9 * Fcr * Ag / 1000.0
            Pn_points.append(Pn)
        
        fig_capacity = go.Figure()
        
        # AISC column curve
        fig_capacity.add_trace(go.Scatter(
            x=lambda_points, y=Pn_points,
            mode='lines',
            name='φPn (AISC E3)',
            line=dict(color='#1976d2', width=3),
            hovertemplate='KL/r: %{x:.1f}<br>φPn: %{y:.2f} tons<extra></extra>'
        ))
        
        # Current design point
        if comp_results:
            current_lambda = comp_results['lambda_c']
            fig_capacity.add_trace(go.Scatter(
                x=[current_lambda], y=[comp_results['phi_Pn']],
                mode='markers',
                name='Design Point',
                marker=dict(color='#f44336', size=15, symbol='star'),
                hovertemplate=f'Design Point<br>λc: {current_lambda:.1f}<br>φPn: {comp_results["phi_Pn"]:.2f} tons<extra></extra>'
            ))
        
        # Enhanced annotations
        fig_capacity.add_vline(x=lambda_limit, line_dash="dash", line_color='#ff9800', line_width=3,
                              annotation_text=f"4.71√(E/Fy) = {lambda_limit:.1f}")
        
        # Regions with equations
        fig_capacity.add_vrect(x0=0, x1=lambda_limit, fillcolor='#ffc107', opacity=0.15,
                              annotation_text="INELASTIC E3.2(a)<br>Fcr = [0.658^(Fy/Fe)]Fy", 
                              annotation_font_size=11)
        fig_capacity.add_vrect(x0=lambda_limit, x1=250, fillcolor='#2196f3', opacity=0.15,
                              annotation_text="ELASTIC E3.2(b)<br>Fcr = 0.877Fe", 
                              annotation_font_size=11)
        
        # Limits
        fig_capacity.add_vline(x=200, line_dash="dot", line_color='#f44336', line_width=2,
                              annotation_text="KL/r = 200 (E2 Limit)")
        
        if Pu > 0:
            fig_capacity.add_hline(y=Pu, line_dash="dash", line_color='#4caf50', line_width=2,
                                  annotation_text=f"Pu = {Pu:.1f} tons")
        
        fig_capacity.update_layout(
            title="AISC 360-16 E3 Enhanced Column Capacity",
            xaxis_title="Slenderness Ratio (KL/r)",
            yaxis_title="φPn (tons)",
            height=550,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_capacity, use_container_width=True)
        
        # Enhanced summary
        if comp_results:
            st.markdown('<div class="design-summary">', unsafe_allow_html=True)
            st.markdown("### AISC 360-16 E3 Design Summary")
            summary_col = pd.DataFrame({
                'Parameter': ['λc', '4.71√(E/Fy)', 'Fe', 'Fcr', 'Pn', 'φPn', 'Pu', 'Pu/φPn'],
                'Value': [f"{comp_results['lambda_c']:.1f}", f"{comp_results['lambda_limit']:.1f}", 
                         f"{comp_results['Fe']:.1f} ksc", f"{comp_results['Fcr']:.1f} ksc", 
                         f"{comp_results['Pn']:.2f} tons", f"{comp_results['phi_Pn']:.2f} tons", 
                         f"{Pu:.2f} tons", f"{Pu/comp_results['phi_Pn']:.3f}" if comp_results['phi_Pn'] > 0 else "N/A"],
                'AISC Ref': ['max(λx,λy)', 'E3 transition', 'E3.4', 'E3.2(a)/(b)', 'E3.1', 'φc=0.90', 'Applied', 'Unity Check']
            })
            st.dataframe(summary_col, use_container_width=True, hide_index=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Please select a section from sidebar")

# ==================== TAB 5: ENHANCED BEAM-COLUMN ====================
with tab5:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter H1 - Enhanced Combined Forces</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
            st.markdown("### Combined Loading Parameters")
            
            Pu_bc = st.slider("Axial Load Pu (tons):", 0.0, 200.0, 50.0, 1.0)
            
            st.markdown("#### Applied Moments")
            Mux = st.slider("Mux (t·m):", 0.0, 100.0, 30.0, 1.0,
                           help="Required flexural strength about major axis")
            Muy = st.slider("Muy (t·m):", 0.0, 50.0, 5.0, 0.5,
                           help="Required flexural strength about minor axis")
            
            st.markdown("#### Effective Lengths") 
            KLx_bc = st.slider("KLx (m):", 0.1, 10.0, 3.0, 0.1)
            KLy_bc = st.slider("KLy (m):", 0.1, 10.0, 3.0, 0.1)
            Lb_bc = st.slider("Lb (m):", 0.1, 10.0, 3.0, 0.1)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Generate H1 calculation report
            if st.button("Generate H1 Report"):
                comp_results = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, KLx_bc, KLy_bc)
                flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_bc)
                
                if comp_results and flex_result:
                    parameters = {'Pu': Pu_bc, 'Mux': Mux, 'Muy': Muy, 
                                 'KLx': KLx_bc, 'KLy': KLy_bc, 'Lb': Lb_bc}
                    
                    # Calculate interaction for report
                    phi_Pn = comp_results['phi_Pn']
                    phi_Mnx = 0.9 * flex_result['Mn']
                    Zy = safe_scalar(df.loc[section, 'Zy [cm3]'])
                    Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
                    phi_Mny = 0.9 * 0.9 * Fy * Zy / 100000.0
                    
                    interaction_result = aisc_360_16_h1_interaction(Pu_bc, phi_Pn, Mux, phi_Mnx, Muy, phi_Mny)
                    
                    report = generate_calculation_report(df, df_mat, section, selected_material, 
                                                       "Combined Forces (H1)", parameters, interaction_result)
                    st.session_state.calculation_report = report
                    st.success("H1 calculation report generated!")
        
        # AISC analyses
        comp_results = aisc_360_16_e3_compression_design(df, df_mat, section, selected_material, KLx_bc, KLy_bc)
        flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_bc)
        
        if comp_results and flex_result:
            # Design strengths
            phi_Pn = comp_results['phi_Pn']
            phi_Mnx = 0.9 * flex_result['Mn']
            
            # Minor axis (simplified)
            Zy = safe_scalar(df.loc[section, 'Zy [cm3]'])
            Fy = safe_scalar(df_mat.loc[selected_material, "Yield Point (ksc)"])
            Mny = Fy * Zy / 100000.0
            phi_Mny = 0.9 * Mny
            
            # AISC H1 interaction
            interaction_result = aisc_360_16_h1_interaction(Pu_bc, phi_Pn, Mux, phi_Mnx, Muy, phi_Mny)
            
            if interaction_result:
                st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 H1 Results")
                
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("Pr/Pc", f"{interaction_result['Pr_Pc']:.3f}",
                             help="Required/Available axial strength ratio")
                
                with col_r2:
                    st.metric("Mrx/Mcx", f"{interaction_result['Mrx_Mcx']:.3f}",
                             help="Major axis moment ratio")
                
                with col_r3:
                    st.metric("Mry/Mcy", f"{interaction_result['Mry_Mcy']:.3f}",
                             help="Minor axis moment ratio")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Unity check with enhanced feedback
                st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 H1 Unity Check")
                st.metric("Interaction Ratio", f"{interaction_result['interaction_ratio']:.3f}",
                        delta=f"Equation {interaction_result['equation']}")
                
                if interaction_result['design_ok']:
                    safety_margin = interaction_result['safety_margin'] * 100
                    st.markdown(f'<div class="success-box">✅ <b>AISC 360-16 H1 PASSES</b><br>Unity: {interaction_result["interaction_ratio"]:.3f} ≤ 1.0<br>Safety Margin: {safety_margin:.1f}%</div>', 
                              unsafe_allow_html=True)
                else:
                    overstress = (interaction_result['interaction_ratio'] - 1.0) * 100
                    st.markdown(f'<div class="error-box">❌ <b>AISC 360-16 H1 FAILS</b><br>Unity: {interaction_result["interaction_ratio"]:.3f} > 1.0<br>Overstressed by: {overstress:.1f}%</div>', 
                              unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # AISC equations display
                st.markdown('<div class="aisc-equation">', unsafe_allow_html=True)
                st.markdown("### AISC 360-16 H1 Equations Applied")
                if interaction_result['Pr_Pc'] >= 0.2:
                    st.markdown("**H1-1a (Pr/Pc ≥ 0.2):** Pr/Pc + (8/9)(Mrx/Mcx + Mry/Mcy) ≤ 1.0")
                else:
                    st.markdown("**H1-1b (Pr/Pc < 0.2):** Pr/(2Pc) + (Mrx/Mcx + Mry/Mcy) ≤ 1.0")
                st.markdown(f"Applied: {interaction_result['equation']}")
                st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("### AISC 360-16 H1 Interactive P-M Diagram")
            
            if comp_results and phi_Mnx > 0:
                # Generate enhanced H1 interaction curve
                P_ratios = []
                M_ratios = []
                
                for i in range(101):  # 0 to 1 in 0.01 increments for smoother curve
                    p_ratio = i * 0.01
                    P_ratios.append(p_ratio)
                    
                    if p_ratio >= 0.2:
                        # H1-1a equation
                        m_ratio = (9.0/8.0) * (1.0 - p_ratio)
                    else:
                        # H1-1b equation  
                        m_ratio = 1.0 - p_ratio/2.0
                    
                    M_ratios.append(safe_max(0.0, m_ratio))
                
                fig = go.Figure()
                
                # Enhanced AISC H1 curve
                fig.add_trace(go.Scatter(
                    x=M_ratios, y=P_ratios,
                    mode='lines',
                    name='AISC H1 Interaction',
                    line=dict(color='#2196f3', width=4),
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.15)',
                    hovertemplate='M ratio: %{x:.3f}<br>P ratio: %{y:.3f}<br>Safe Zone<extra></extra>'
                ))
                
                # Design point
                if interaction_result:
                    M_combined = interaction_result['Mrx_Mcx'] + interaction_result['Mry_Mcy']
                    P_ratio = interaction_result['Pr_Pc']
                    
                    fig.add_trace(go.Scatter(
                        x=[M_combined], y=[P_ratio],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=20, symbol='star'),
                        hovertemplate=f'Design Point<br>P/Pc: {P_ratio:.3f}<br>ΣM/Mc: {M_combined:.3f}<br>Unity: {interaction_result["interaction_ratio"]:.3f}<br>Equation: {interaction_result["equation"]}<extra></extra>'
                    ))
                    
                    # Enhanced status annotation with equation info
                    if interaction_result['design_ok']:
                        annotation_text = f"✅ SAFE<br>{interaction_result['equation']}"
                        annotation_color = "#4caf50"
                    else:
                        annotation_text = f"❌ UNSAFE<br>{interaction_result['equation']}"
                        annotation_color = "#f44336"
                    
                    fig.add_annotation(
                        x=M_combined + 0.05, y=P_ratio + 0.05,
                        text=annotation_text,
                        showarrow=True,
                        arrowhead=2,
                        bgcolor="white",
                        bordercolor=annotation_color,
                        borderwidth=2,
                        font=dict(size=12)
                    )
                
                # Enhanced transition line
                fig.add_hline(y=0.2, line_dash="dot", line_color='#ff9800', line_width=2,
                            annotation_text="Pr/Pc = 0.2 (H1-1a/H1-1b transition)")
                
                # Region annotations
                fig.add_annotation(x=0.5, y=0.6, text="H1-1a Region<br>Pr/Pc ≥ 0.2", 
                                 bgcolor="rgba(255,152,0,0.1)", bordercolor="#ff9800", showarrow=False)
                fig.add_annotation(x=0.7, y=0.1, text="H1-1b Region<br>Pr/Pc < 0.2", 
                                 bgcolor="rgba(76,175,80,0.1)", bordercolor="#4caf50", showarrow=False)
                
                fig.update_layout(
                    title="AISC 360-16 H1 Enhanced P-M Interaction Diagram",
                    xaxis_title="Combined Moment Ratio (Mrx/Mcx + Mry/Mcy)",
                    yaxis_title="Axial Force Ratio (Pr/Pc)",
                    height=600,
                    template='plotly_white',
                    hovermode='closest',
                    xaxis=dict(range=[0, 1.3], showgrid=True, gridcolor='lightgray'),
                    yaxis=dict(range=[0, 1.1], showgrid=True, gridcolor='lightgray')
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Enhanced H1 summary with capacities
                if interaction_result:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("### AISC 360-16 H1 Design Summary")
                    h1_summary = pd.DataFrame({
                        'Component': ['Axial (E3)', 'Major Moment (F2)', 'Minor Moment', 'H1 Interaction'],
                        'Required': [f"{Pu_bc:.1f} tons", f"{Mux:.1f} t⋅m", f"{Muy:.1f} t⋅m", 
                                   f"{interaction_result['interaction_ratio']:.3f}"],
                        'Available': [f"{phi_Pn:.1f} tons", f"{phi_Mnx:.1f} t⋅m", f"{phi_Mny:.1f} t⋅m", "1.000"],
                        'Ratio': [f"{interaction_result['Pr_Pc']:.3f}", f"{interaction_result['Mrx_Mcx']:.3f}",
                                 f"{interaction_result['Mry_Mcy']:.3f}", f"{interaction_result['equation']}"],
                        'Status': ["✓" if interaction_result['Pr_Pc'] <= 1.0 else "✗",
                                  "✓" if interaction_result['Mrx_Mcx'] <= 1.0 else "✗",
                                  "✓" if interaction_result['Mry_Mcy'] <= 1.0 else "✗",
                                  "✓" if interaction_result['design_ok'] else "✗"]
                    })
                    st.dataframe(h1_summary, use_container_width=True, hide_index=True)
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Please select a section and material from the sidebar")

# ==================== TAB 6: ENHANCED COMPARISON ====================
with tab6:
    st.markdown('<h2 class="section-header">AISC 360-16 Advanced Multi-Section Comparison</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_sections:
        st.info(f"Comparing {len(st.session_state.selected_sections)} sections per AISC 360-16")
        
        # Enhanced comparison parameters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            comparison_type = st.selectbox("Analysis Type:",
                ["Moment Capacity (F2)", "Compression Capacity (E3)", "Weight Efficiency", 
                 "Combined Performance", "Critical Lengths Analysis"])
        
        with col2:
            Lb_comp = st.slider("Lb for F2 (m):", 0.1, 20.0, 3.0, 0.1)
        
        with col3:
            KL_comp = st.slider("KL for E3 (m):", 0.1, 20.0, 3.0, 0.1)
            
        with col4:
            export_results = st.button("Export Comparison")
        
        # Enhanced AISC comparison with critical lengths
        comparison_data = []
        
        for section_name in st.session_state.selected_sections:
            if section_name not in df.index:
                continue
            
            try:
                weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
                weight = safe_scalar(df.loc[section_name, weight_col])
                
                # AISC F2 analysis
                flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section_name, selected_material, Lb_comp)
                
                # AISC E3 analysis
                comp_results = aisc_360_16_e3_compression_design(df, df_mat, section_name, selected_material, KL_comp, KL_comp)
                
                if flex_result and comp_results:
                    comparison_data.append({
                        'Section': section_name,
                        'Weight (kg/m)': weight,
                        'φMn (t·m)': 0.9 * flex_result['Mn'],
                        'φPn (tons)': comp_results['phi_Pn'],
                        'Lp (m)': flex_result['Lp'],
                        'Lr (m)': flex_result['Lr'],
                        'F2 Case': flex_result['Case'],
                        'E3 Mode': comp_results['buckling_mode'],
                        'Moment Efficiency': (0.9 * flex_result['Mn']) / weight,
                        'Compression Efficiency': comp_results['phi_Pn'] / weight,
                        'Lp/Lr Ratio': flex_result['Lp'] / flex_result['Lr'] if flex_result['Lr'] > 0 else 0,
                        'Combined Score': ((0.9 * flex_result['Mn']) / weight) * (comp_results['phi_Pn'] / weight)
                    })
            except Exception as e:
                st.warning(f"Error analyzing {section_name}: {str(e)}")
                continue
        
        if comparison_data:
            df_comparison = pd.DataFrame(comparison_data)
            
            # Enhanced comparison charts
            if comparison_type == "Moment Capacity (F2)":
                st.markdown("### AISC F2 Multi-Section Moment Capacity Curves")
                
                fig = go.Figure()
                colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4', 
                         '#795548', '#607d8b', '#e91e63', '#3f51b5']
                
                for i, section_name in enumerate(st.session_state.selected_sections[:10]):  # Limit for performance
                    if section_name not in df.index:
                        continue
                    
                    # Generate F2 curve for each section
                    Lb_points = []
                    Mn_points = []
                    
                    for j in range(150):  # 150 points from 0.1 to 15m
                        lb = 0.1 + j * 0.1
                        Lb_points.append(lb)
                        
                        try:
                            flex_result = aisc_360_16_f2_flexural_design(df, df_mat, section_name, selected_material, lb)
                            if flex_result:
                                Mn_points.append(0.9 * flex_result['Mn'])
                            else:
                                Mn_points.append(0)
                        except:
                            Mn_points.append(0)
                    
                    color = colors[i % len(colors)]
                    fig.add_trace(go.Scatter(
                        x=Lb_points, y=Mn_points,
                        mode='lines',
                        name=section_name,
                        line=dict(color=color, width=3),
                        hovertemplate='%{fullData.name}<br>Lb: %{x:.1f}m<br>φMn: %{y:.2f} t·m<extra></extra>'
                    ))
                    
                    # Add critical length markers for this section
                    section_data = df_comparison[df_comparison['Section'] == section_name]
                    if not section_data.empty:
                        Lp = section_data['Lp (m)'].iloc[0]
                        Lr = section_data['Lr (m)'].iloc[0]
                        
                        # Find Mn at Lp and Lr for markers
                        Lp_index = min(range(len(Lb_points)), key=lambda i: abs(Lb_points[i] - Lp))
                        Lr_index = min(range(len(Lb_points)), key=lambda i: abs(Lb_points[i] - Lr))
                        
                        # Add Lp marker
                        fig.add_trace(go.Scatter(
                            x=[Lp], y=[Mn_points[Lp_index]],
                            mode='markers',
                            name=f'{section_name} Lp',
                            marker=dict(color=color, size=8, symbol='circle'),
                            showlegend=False,
                            hovertemplate=f'{section_name}<br>Lp: {Lp:.3f}m<br>φMn: {Mn_points[Lp_index]:.2f} t·m<extra></extra>'
                        ))
                        
                        # Add Lr marker
                        fig.add_trace(go.Scatter(
                            x=[Lr], y=[Mn_points[Lr_index]],
                            mode='markers',
                            name=f'{section_name} Lr',
                            marker=dict(color=color, size=8, symbol='square'),
                            showlegend=False,
                            hovertemplate=f'{section_name}<br>Lr: {Lr:.3f}m<br>φMn: {Mn_points[Lr_index]:.2f} t·m<extra></extra>'
                        ))
                
                # Add design point line
                fig.add_vline(x=Lb_comp, line_dash="dash", line_color='red', line_width=2,
                            annotation_text=f"Design Lb = {Lb_comp:.1f} m")
                
                fig.update_layout(
                    title="AISC 360-16 F2: Multi-Section Comparison with Critical Lengths",
                    xaxis_title="Unbraced Length, Lb (m)",
                    yaxis_title="φMn (t·m)",
                    height=600,
                    template='plotly_white',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Critical lengths summary table
                st.markdown("### Critical Lengths Summary")
                critical_summary = df_comparison[['Section', 'Lp (m)', 'Lr (m)', 'Lp/Lr Ratio', 'F2 Case']].copy()
                
                def highlight_best_lp_lr(s):
                    if s.name == 'Lp (m)':
                        is_max = s == s.max()
                        return ['background-color: #e8f5e9' if v else '' for v in is_max]
                    elif s.name == 'Lr (m)':
                        is_max = s == s.max()
                        return ['background-color: #fff3e0' if v else '' for v in is_max]
                    else:
                        return ['' for _ in s]
                
                styled_critical = critical_summary.style.apply(highlight_best_lp_lr).format({
                    'Lp (m)': '{:.3f}',
                    'Lr (m)': '{:.3f}',
                    'Lp/Lr Ratio': '{:.3f}'
                })
                
                st.dataframe(styled_critical, use_container_width=True, hide_index=True)
                
            elif comparison_type == "Critical Lengths Analysis":
                st.markdown("### AISC F2 Critical Lengths Detailed Analysis")
                
                # Critical lengths visualization
                fig_critical = go.Figure()
                
                sections = df_comparison['Section'].tolist()
                lp_values = df_comparison['Lp (m)'].tolist()
                lr_values = df_comparison['Lr (m)'].tolist()
                
                fig_critical.add_trace(go.Bar(
                    name='Lp (Yielding Limit)',
                    x=sections,
                    y=lp_values,
                    marker_color='#4caf50',
                    hovertemplate='%{x}<br>Lp: %{y:.3f} m<extra></extra>'
                ))
                
                fig_critical.add_trace(go.Bar(
                    name='Lr (Inelastic LTB Limit)',
                    x=sections,
                    y=lr_values,
                    marker_color='#ff9800',
                    hovertemplate='%{x}<br>Lr: %{y:.3f} m<extra></extra>'
                ))
                
                # Add design point line
                fig_critical.add_hline(y=Lb_comp, line_dash="dash", line_color='red', line_width=3,
                                     annotation_text=f"Design Lb = {Lb_comp:.1f} m")
                
                fig_critical.update_layout(
                    title="Critical Lengths Comparison (Lp & Lr per AISC F2.5 & F2.6)",
                    xaxis_title="Steel Sections",
                    yaxis_title="Length (m)",
                    height=500,
                    template='plotly_white',
                    barmode='group'
                )
                
                st.plotly_chart(fig_critical, use_container_width=True)
                
                # Zone classification for current Lb
                st.markdown("### Zone Classification for Current Design")
                zone_data = []
                for _, row in df_comparison.iterrows():
                    if Lb_comp <= row['Lp (m)']:
                        zone = "✅ Yielding (F2.1)"
                        status = "Optimal"
                    elif Lb_comp <= row['Lr (m)']:
                        zone = "⚠️ Inelastic LTB (F2.2)"
                        status = "Good"
                    else:
                        zone = "❌ Elastic LTB (F2.3)"
                        status = "Check Required"
                    
                    zone_data.append({
                        'Section': row['Section'],
                        'Zone at Lb=' + f"{Lb_comp:.1f}m": zone,
                        'Status': status,
                        'Lp (m)': f"{row['Lp (m)']:.3f}",
                        'Lr (m)': f"{row['Lr (m)']:.3f}"
                    })
                
                zone_df = pd.DataFrame(zone_data)
                st.dataframe(zone_df, use_container_width=True, hide_index=True)
                
            elif comparison_type == "Compression Capacity (E3)":
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['φPn (tons)'],
                    text=[f'{v:.1f}' for v in df_comparison['φPn (tons)']],
                    textposition='auto',
                    marker_color='#2196f3',
                    name='φPn (AISC E3)',
                    hovertemplate='%{x}<br>φPn: %{y:.1f} tons<br>Mode: %{customdata}<extra></extra>',
                    customdata=df_comparison['E3 Mode']
                ))
                
                fig.update_layout(
                    title=f"AISC 360-16 E3: Compression Capacity at KL = {KL_comp:.1f} m",
                    xaxis_title="Steel Sections",
                    yaxis_title="φPn (tons)",
                    height=500,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif comparison_type == "Weight Efficiency":
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=('Moment Efficiency', 'Compression Efficiency', 
                                   'Combined Efficiency Score', 'Weight Comparison'),
                    specs=[[{"type": "bar"}, {"type": "bar"}],
                           [{"type": "bar"}, {"type": "bar"}]]
                )
                
                # Moment efficiency
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Moment Efficiency'],
                    marker_color='#4caf50',
                    name='φMn/Weight',
                    showlegend=False
                ), row=1, col=1)
                
                # Compression efficiency
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Compression Efficiency'],
                    marker_color='#ff9800',
                    name='φPn/Weight',
                    showlegend=False
                ), row=1, col=2)
                
                # Combined score
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Combined Score'],
                    marker_color='#9c27b0',
                    name='Combined Score',
                    showlegend=False
                ), row=2, col=1)
                
                # Weight comparison
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Weight (kg/m)'],
                    marker_color='#607d8b',
                    name='Weight',
                    showlegend=False
                ), row=2, col=2)
                
                fig.update_layout(
                    title="AISC 360-16 Comprehensive Efficiency Analysis",
                    height=700,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            elif comparison_type == "Combined Performance":
                # Enhanced radar chart
                fig = go.Figure()
                
                categories = ['Weight Efficiency', 'φMn Capacity', 'φPn Capacity', 
                             'Lp Length', 'Lr Length', 'Overall Score']
                
                for idx, row in df_comparison.iterrows():
                    # Normalize values for radar chart (higher is better)
                    values = [
                        1 - (row['Weight (kg/m)'] / df_comparison['Weight (kg/m)'].max()),  # Lower weight is better
                        row['φMn (t·m)'] / df_comparison['φMn (t·m)'].max(),
                        row['φPn (tons)'] / df_comparison['φPn (tons)'].max(),
                        row['Lp (m)'] / df_comparison['Lp (m)'].max(),
                        row['Lr (m)'] / df_comparison['Lr (m)'].max(),
                        row['Combined Score'] / df_comparison['Combined Score'].max()
                    ]
                    values.append(values[0])  # Close the polygon
                    
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories + [categories[0]],
                        fill='toself',
                        name=row['Section'],
                        opacity=0.7
                    ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]
                        )),
                    showlegend=True,
                    title="AISC 360-16 Combined Performance Radar Chart",
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Enhanced comparison table
            st.markdown("### 📊 AISC 360-16 Detailed Comparison Table")
            
            df_display = df_comparison.copy()
            df_display = df_display.round(4)
            
            # Highlight best values
            def highlight_optimal(s):
                if s.name in ['φMn (t·m)', 'φPn (tons)', 'Lp (m)', 'Lr (m)', 
                             'Moment Efficiency', 'Compression Efficiency', 'Combined Score']:
                    is_max = s == s.max()
                    return ['background-color: #e8f5e9; font-weight: bold' if v else '' for v in is_max]
                elif s.name == 'Weight (kg/m)':
                    is_min = s == s.min()
                    return ['background-color: #e8f5e9; font-weight: bold' if v else '' for v in is_min]
                else:
                    return ['' for _ in s]
            
            styled_df = df_display.style.apply(highlight_optimal)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Enhanced recommendations with AISC context
            st.markdown("### 🏆 AISC 360-16 Design Recommendations")
            
            col_rec1, col_rec2, col_rec3, col_rec4 = st.columns(4)
            
            with col_rec1:
                best_moment = df_comparison.loc[df_comparison['φMn (t·m)'].idxmax()]
                st.info(f"""
                **Best F2 Moment Capacity:**
                {best_moment["Section"]}
                φMn: {best_moment["φMn (t·m)"]:.2f} t·m
                Case: {best_moment["F2 Case"]}
                """)
            
            with col_rec2:
                best_compression = df_comparison.loc[df_comparison['φPn (tons)'].idxmax()]
                st.info(f"""
                **Best E3 Compression:**
                {best_compression["Section"]}
                φPn: {best_compression["φPn (tons)"]:.1f} tons
                Mode: {best_compression["E3 Mode"]}
                """)
            
            with col_rec3:
                best_lp = df_comparison.loc[df_comparison['Lp (m)'].idxmax()]
                st.info(f"""
                **Best Critical Length Lp:**
                {best_lp["Section"]}
                Lp: {best_lp["Lp (m)"]:.3f} m
                (F2.5 Yielding Limit)
                """)
            
            with col_rec4:
                lightest = df_comparison.loc[df_comparison['Weight (kg/m)'].idxmin()]
                st.info(f"""
                **Lightest Section:**
                {lightest["Section"]}
                Weight: {lightest["Weight (kg/m)"]:.1f} kg/m
                Efficiency Leader
                """)
            
            # Export functionality
            if export_results:
                csv = df_comparison.to_csv(index=False)
                st.download_button(
                    label="📥 Download Comparison Results (CSV)",
                    data=csv,
                    file_name=f"aisc_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime='text/csv'
                )
                
    else:
        st.warning("⚠️ Please select sections from the 'Section Selection' tab first")
        st.markdown("""
        ### 📖 How to Use Enhanced Comparison Tool:
        1. Go to **Section Selection** tab
        2. Input your design requirements (Mu, deflection, etc.)
        3. Select multiple sections using checkboxes
        4. Return here for advanced AISC 360-16 comparison
        
        **Enhanced Features:**
        - Real-time critical lengths (Lp, Lr) calculation
        - Zone classification for any unbraced length
        - Multi-section moment capacity curves with critical points
        - Weight efficiency analysis with AISC context
        - Export capabilities for further analysis
        """)

# ==================== TAB 7: DESIGN EVALUATION & CALCULATION REPORTS ====================
with tab7:
    st.markdown('<h2 class="section-header">AISC 360-16 Design Evaluation & Calculation Reports</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.markdown('<div class="evaluation-card">', unsafe_allow_html=True)
        st.markdown(f"### Comprehensive Design Evaluation: {section}")
        st.markdown(f"**Material:** {selected_material}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Design input parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Design Loads")
            Mu_eval = st.number_input("Design Moment Mu (t·m):", min_value=0.0, value=50.0, step=1.0, key="eval_mu")
            Pu_eval = st.number_input("Axial Load Pu (tons):", min_value=0.0, value=25.0, step=1.0, key="eval_pu")
        
        with col2:
            st.markdown("#### Design Lengths")
            Lb_eval = st.number_input("Unbraced Length Lb (m):", min_value=0.1, value=3.0, step=0.1, key="eval_lb")
            KL_eval = st.number_input("Effective Length KL (m):", min_value=0.1, value=3.0, step=0.1, key="eval_kl")
        
        with col3:
            st.markdown("#### Analysis Options")
            analysis_detail = st.selectbox("Detail Level:", ["Summary", "Detailed", "Full Report"])
            include_calcs = st.checkbox("Include Step-by-Step Calculations", value=True)
        
        # Perform comprehensive evaluation
        if st.button("🔍 Perform AISC 360-16 Evaluation", type="primary"):
            
            # Prepare evaluation parameters
            design_loads = {'Mu': Mu_eval, 'Pu': Pu_eval}
            design_lengths = {'Lb': Lb_eval, 'KLx': KL_eval, 'KLy': KL_eval}
            
            # Perform evaluation
            evaluation = evaluate_section_design(df, df_mat, section, selected_material, design_loads, design_lengths)
            
            if evaluation:
                # Display comprehensive results
                st.markdown("## 📊 AISC 360-16 Design Evaluation Results")
                
                # Overall assessment banner
                if evaluation['design_check']['overall_adequate']:
                    st.markdown('<div class="success-box">', unsafe_allow_html=True)
                    st.markdown("### ✅ OVERALL DESIGN STATUS: ADEQUATE")
                    st.markdown(f"**Safety Factors:** Moment = {evaluation['design_check']['safety_factor_moment']:.2f}, Axial = {evaluation['design_check']['safety_factor_axial']:.2f}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="error-box">', unsafe_allow_html=True)
                    st.markdown("### ❌ OVERALL DESIGN STATUS: INADEQUATE")
                    st.markdown("**Action Required:** Section or design parameters need revision")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Detailed component analysis
                col_eval1, col_eval2, col_eval3 = st.columns(3)
                
                with col_eval1:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("#### Flexural Analysis (F2)")
                    st.metric("φMn", f"{evaluation['flexural']['phi_Mn']:.2f} t·m")
                    st.metric("Utilization", f"{evaluation['flexural']['ratio']:.3f}")
                    st.metric("Zone", evaluation['flexural']['zone'])
                    st.write(f"**Status:** {evaluation['flexural']['status']}")
                    st.write(f"**Case:** {evaluation['flexural']['case']}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_eval2:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("#### Compression Analysis (E3)")
                    st.metric("φPn", f"{evaluation['compression']['phi_Pn']:.2f} tons")
                    st.metric("Utilization", f"{evaluation['compression']['ratio']:.3f}")
                    st.metric("Mode", evaluation['compression']['mode'])
                    st.write(f"**λc:** {evaluation['compression']['lambda_c']:.1f}")
                    st.write(f"**Fcr:** {evaluation['compression']['Fcr']:.1f} kgf/cm²")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_eval3:
                    st.markdown('<div class="design-summary">', unsafe_allow_html=True)
                    st.markdown("#### Efficiency Metrics")
                    st.metric("Weight", f"{evaluation['weight']:.1f} kg/m")
                    st.metric("Moment Eff.", f"{evaluation['flexural']['efficiency']:.3f}")
                    st.metric("Compression Eff.", f"{evaluation['compression']['efficiency']:.3f}")
                    st.write(f"**Lp:** {evaluation['flexural']['Lp']:.3f} m")
                    st.write(f"**Lr:** {evaluation['flexural']['Lr']:.3f} m")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Critical lengths visualization for evaluated section
                st.markdown("### Critical Lengths Analysis for Evaluated Design")
                
                fig_eval = go.Figure()
                
                # Get the flexural result for full curve
                flex_eval = aisc_360_16_f2_flexural_design(df, df_mat, section, selected_material, Lb_eval)
                
                if flex_eval:
                    # Moment capacity curve
                    fig_eval.add_trace(go.Scatter(
                        x=flex_eval['Lb_range'],
                        y=flex_eval['Mn_curve'],
                        mode='lines',
                        name='Mn',
                        line=dict(color='#1976d2', width=3)
                    ))
                    
                    # Design point
                    fig_eval.add_trace(go.Scatter(
                        x=[Lb_eval],
                        y=[evaluation['flexural']['Mn']],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=15, symbol='star'),
                        hovertemplate=f'Design Point<br>Lb: {Lb_eval:.2f}m<br>Mn: {evaluation["flexural"]["Mn"]:.2f} t·m<br>Zone: {evaluation["flexural"]["zone"]}<extra></extra>'
                    ))
                    
                    # Critical lengths
                    fig_eval.add_vline(x=evaluation['flexural']['Lp'], line_dash="dash", line_color='#4caf50', line_width=3,
                                     annotation_text=f"Lp = {evaluation['flexural']['Lp']:.3f} m")
                    fig_eval.add_vline(x=evaluation['flexural']['Lr'], line_dash="dash", line_color='#ff9800', line_width=3,
                                     annotation_text=f"Lr = {evaluation['flexural']['Lr']:.3f} m")
                    
                    # Zone coloring based on design point
                    if Lb_eval <= evaluation['flexural']['Lp']:
                        fig_eval.add_vrect(x0=0, x1=evaluation['flexural']['Lp'], fillcolor='#4caf50', opacity=0.2,
                                         annotation_text="CURRENT ZONE<br>F2.1 YIELDING", annotation_position="top left")
                    elif Lb_eval <= evaluation['flexural']['Lr']:
                        fig_eval.add_vrect(x0=evaluation['flexural']['Lp'], x1=evaluation['flexural']['Lr'], fillcolor='#ff9800', opacity=0.2,
                                         annotation_text="CURRENT ZONE<br>F2.2 INELASTIC LTB", annotation_position="top")
                    else:
                        max_x = max(flex_eval['Lb_range'])
                        fig_eval.add_vrect(x0=evaluation['flexural']['Lr'], x1=max_x, fillcolor='#f44336', opacity=0.2,
                                         annotation_text="CURRENT ZONE<br>F2.3 ELASTIC LTB", annotation_position="top right")
                    
                    fig_eval.update_layout(
                        title=f"Design Evaluation: {section} at Lb = {Lb_eval:.2f}m",
                        xaxis_title="Unbraced Length, Lb (m)",
                        yaxis_title="Moment Capacity (t·m)",
                        height=500,
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig_eval, use_container_width=True)
        
        # Calculation report display
        if st.session_state.calculation_report:
            st.markdown("### 📄 Generated Calculation Report")
            
            col_report1, col_report2 = st.columns([3, 1])
            
            with col_report1:
                st.markdown('<div class="calculation-note">', unsafe_allow_html=True)
                st.text(st.session_state.calculation_report)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col_report2:
                # Download report
                report_filename = f"AISC_Calc_Report_{section}_{selected_material}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                
                st.download_button(
                    label="📥 Download Report",
                    data=st.session_state.calculation_report,
                    file_name=report_filename,
                    mime='text/plain',
                    help="Download the calculation report as a text file"
                )
                
                if st.button("🗑️ Clear Report"):
                    st.session_state.calculation_report = ""
                    st.experimental_rerun()
        
        # Quick evaluation for all selected sections
        if st.session_state.selected_sections and len(st.session_state.selected_sections) > 1:
            st.markdown("### 🔄 Quick Evaluation of All Selected Sections")
            
            if st.button("Evaluate All Selected Sections"):
                design_loads = {'Mu': Mu_eval, 'Pu': Pu_eval}
                design_lengths = {'Lb': Lb_eval, 'KLx': KL_eval, 'KLy': KL_eval}
                
                quick_eval_results = []
                
                for section_name in st.session_state.selected_sections:
                    if section_name in df.index:
                        eval_result = evaluate_section_design(df, df_mat, section_name, selected_material, design_loads, design_lengths)
                        
                        if eval_result:
                            quick_eval_results.append({
                                'Section': section_name,
                                'Overall Status': "✅ PASS" if eval_result['design_check']['overall_adequate'] else "❌ FAIL",
                                'Moment Ratio': f"{eval_result['flexural']['ratio']:.3f}",
                                'Axial Ratio': f"{eval_result['compression']['ratio']:.3f}",
                                'F2 Zone': eval_result['flexural']['zone'],
                                'E3 Mode': eval_result['compression']['mode'],
                                'Weight (kg/m)': f"{eval_result['weight']:.1f}",
                                'Safety Factor (Min)': f"{min(eval_result['design_check']['safety_factor_moment'], eval_result['design_check']['safety_factor_axial']):.2f}"
                            })
                
                if quick_eval_results:
                    quick_df = pd.DataFrame(quick_eval_results)
                    
                    # Style the dataframe
                    def color_status(val):
                        color = '#d4edda' if '✅' in val else '#f8d7da'
                        return f'background-color: {color}'
                    
                    styled_quick = quick_df.style.applymap(color_status, subset=['Overall Status'])
                    st.dataframe(styled_quick, use_container_width=True, hide_index=True)
                    
                    # Summary statistics
                    passing_sections = len([r for r in quick_eval_results if "✅" in r['Overall Status']])
                    st.success(f"✅ {passing_sections} of {len(quick_eval_results)} sections PASS the design criteria")
    
    else:
        st.warning("⚠️ Please select a section and material from the sidebar")
        
        st.markdown("""
        ### 📖 Design Evaluation Features:
        
        **Comprehensive Analysis:**
        - Complete AISC 360-16 F2 flexural analysis
        - Complete AISC 360-16 E3 compression analysis  
        - Critical lengths calculation and zone classification
        - Efficiency metrics and recommendations
        
        **Calculation Reports:**
        - Step-by-step AISC equation application
        - Material and section properties documentation
        - Detailed intermediate calculations
        - Professional format for submission
        
        **Multi-Section Evaluation:**
        - Batch processing of selected sections
        - Comparative adequacy assessment
        - Quick pass/fail summary
        - Export capabilities for project documentation
        
        **Enhanced Features:**
        - Real-time design zone visualization
        - Interactive critical length analysis
        - Safety factor calculations
        - Professional report generation
        """)

# ==================== ENHANCED FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; margin: 1rem 0;'>
    <h3><b>AISC 360-16 Steel Design Professional v6.0</b></h3>
    <p><b>🎯 Enhanced Features:</b> Advanced Design Evaluation | Critical Lengths Display | Calculation Reports</p>
    <p><b>📐 AISC Compliance:</b> F2 Flexural | E3 Compression | H1 Combined Forces | Complete Equations</p>
    <p><b>🔧 Professional Tools:</b> Multi-Section Comparison | Zone Analysis | Export Capabilities</p>
    <p><i>© 2024 - Professional Tool for Structural Engineers</i></p>
</div>
""", unsafe_allow_html=True)
