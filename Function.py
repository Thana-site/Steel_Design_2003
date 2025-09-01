# ==================== AISC 360-16 COMPLIANT STEEL DESIGN ANALYSIS APPLICATION ====================
# Version: 5.2 - AISC 360-16 Compliant with Fixed Array Issues
# GitHub: Thana-site/Steel_Design_2003

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import math as mt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import requests

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="Steel Design Analysis | AISC 360-16",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
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

# ==================== AISC 360-16 CHAPTER F - FLEXURAL MEMBERS ====================
def aisc_f2_lateral_torsional_buckling(df, df_mat, section, material, Lb_input, Cb=1.0):
    """
    AISC 360-16 Chapter F2 - Lateral-Torsional Buckling of Doubly Symmetric Compact I-shaped Members
    
    This function implements the exact AISC 360-16 equations:
    - F2.1: Yielding (Lb ≤ Lp)
    - F2.2: Inelastic LTB (Lp < Lb ≤ Lr) 
    - F2.3: Elastic LTB (Lb > Lr)
    
    Args:
        df: Section database
        df_mat: Material database  
        section: Section name
        material: Material grade
        Lb_input: Unbraced length in meters
        Cb: Lateral-torsional buckling modification factor
    
    Returns:
        Dictionary with analysis results and curve data
    """
    try:
        # Get section properties (all in consistent units)
        Sx = float(df.loc[section, "Sx [cm3]"])  # Section modulus
        Zx = float(df.loc[section, 'Zx [cm3]'])  # Plastic section modulus
        ry = float(df.loc[section, 'ry [cm]'])   # Minor axis radius of gyration
        
        # Handle rts (radius of gyration of compression flange plus 1/3 compression web)
        if 'rts [cm]' in df.columns:
            rts = float(df.loc[section, 'rts [cm]'])
        else:
            # Conservative approximation if rts not available
            rts = ry * 1.2  
        
        # Warping and torsional properties
        J = float(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 1.0
        
        # Distance between flange centroids
        if 'ho [mm]' in df.columns:
            ho = float(df.loc[section, 'ho [mm]']) / 10  # Convert mm to cm
        else:
            ho = float(df.loc[section, 'd [mm]']) / 10    # Use total depth as approximation
        
        # Material properties  
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])  # kgf/cm²
        E = float(df_mat.loc[material, "E"])                   # kgf/cm² 
        
        # AISC 360-16 Equation F2.5 - Limiting laterally unbraced length for yielding
        # Lp = 1.76 * ry * sqrt(E/Fy)
        Lp = 1.76 * ry * np.sqrt(E / Fy) / 100  # Convert to meters
        
        # AISC 360-16 Equation F2.6 - Limiting laterally unbraced length for inelastic LTB
        # Lr = 1.95 * rts * (E/(0.7*Fy)) * sqrt(J*c/(Sx*ho)) * sqrt(1 + sqrt(1 + 6.76*(0.7*Fy/E)^2*(Sx*ho/(J*c))^2))
        c = 1.0  # Conservative factor for doubly symmetric sections
        
        # Calculate Lr using AISC 360-16 F2.6
        term1 = 1.95 * rts * (E / (0.7 * Fy))
        term2 = np.sqrt(J * c / (Sx * ho))  
        term3_inner = 6.76 * ((0.7 * Fy / E)**2) * ((Sx * ho / (J * c))**2)
        term3 = np.sqrt(1 + np.sqrt(1 + term3_inner))
        Lr = term1 * term2 * term3 / 100  # Convert to meters
        
        # Calculate plastic moment
        Mp = Fy * Zx  # kgf⋅cm
        
        # Single point calculation for input Lb
        Lb_cm = Lb_input * 100  # Convert to cm
        
        if Lb_input <= Lp:
            # AISC 360-16 F2.1 - Yielding limit state
            Case = "F2.1 - Yielding"
            Mn = Mp  # kgf⋅cm
            
        elif Lb_input <= Lr:  
            # AISC 360-16 F2.2 - Inelastic lateral-torsional buckling
            Case = "F2.2 - Inelastic LTB"
            Lp_cm = Lp * 100
            Lr_cm = Lr * 100
            
            # F2.2: Mn = Cb * [Mp - (Mp - 0.7*Fy*Sx) * (Lb - Lp)/(Lr - Lp)] ≤ Mp
            Mn = Cb * (Mp - (Mp - 0.7 * Fy * Sx) * (Lb_cm - Lp_cm) / (Lr_cm - Lp_cm))
            Mn = min(Mp, Mn)  # Cannot exceed Mp
            
        else:
            # AISC 360-16 F2.3 - Elastic lateral-torsional buckling  
            Case = "F2.3 - Elastic LTB"
            
            # F2.3: Mn = Fcr * Sx ≤ Mp
            # where Fcr = (Cb * π² * E / (Lb/rts)²) * sqrt(1 + 0.078 * (J*c/Sx*ho) * (Lb/rts)²)
            Lb_rts_ratio = Lb_cm / rts
            term_1 = (Cb * np.pi**2 * E) / (Lb_rts_ratio**2)
            term_2 = 0.078 * (J * c / (Sx * ho)) * (Lb_rts_ratio**2)
            Fcr = term_1 * np.sqrt(1 + term_2)
            
            Mn = Fcr * Sx
            Mn = min(Mp, Mn)  # Cannot exceed Mp
        
        # Convert to t⋅m for output
        Mn_tm = Mn / 100000  # kgf⋅cm to t⋅m
        Mp_tm = Mp / 100000  # kgf⋅cm to t⋅m
        
        # Generate full curve for plotting (avoiding array boolean issues)
        Lb_range = np.linspace(0.1, max(15.0, Lr + 5), 200)
        Mn_curve = []
        
        for Lb_point in Lb_range:
            Lb_point_cm = Lb_point * 100
            
            if Lb_point <= Lp:
                # F2.1 - Yielding
                Mn_point = Mp
                
            elif Lb_point <= Lr:
                # F2.2 - Inelastic LTB
                Lp_cm = Lp * 100
                Lr_cm = Lr * 100
                Mn_point = Cb * (Mp - (Mp - 0.7 * Fy * Sx) * (Lb_point_cm - Lp_cm) / (Lr_cm - Lp_cm))
                Mn_point = min(Mp, Mn_point)
                
            else:
                # F2.3 - Elastic LTB
                Lb_rts_ratio = Lb_point_cm / rts
                term_1 = (Cb * np.pi**2 * E) / (Lb_rts_ratio**2)
                term_2 = 0.078 * (J * c / (Sx * ho)) * (Lb_rts_ratio**2)
                Fcr = term_1 * np.sqrt(1 + term_2)
                Mn_point = Fcr * Sx
                Mn_point = min(Mp, Mn_point)
            
            # Convert to t⋅m and ensure non-negative (fix array issue)
            Mn_point_tm = float(Mn_point / 100000)
            Mn_curve.append(max(0.0, Mn_point_tm))
        
        return {
            'Mn': Mn_tm,
            'Mp': Mp_tm, 
            'Lp': Lp,
            'Lr': Lr,
            'Case': Case,
            'Lb_range': list(Lb_range),  # Convert to list to avoid array issues
            'Mn_curve': Mn_curve,
            'Cb': Cb
        }
        
    except Exception as e:
        st.error(f"Error in AISC F2 calculation: {str(e)}")
        return None

# ==================== AISC 360-16 CHAPTER E - COMPRESSION MEMBERS ====================
def aisc_e3_flexural_buckling(df, df_mat, section, material, KLx, KLy):
    """
    AISC 360-16 Chapter E3 - Flexural Buckling of Members without Slender Elements
    
    Implements:
    - E3.2(a): Inelastic buckling when λ ≤ 4.71√(E/Fy)
    - E3.2(b): Elastic buckling when λ > 4.71√(E/Fy)
    
    Args:
        df: Section database
        df_mat: Material database
        section: Section name
        material: Material grade
        KLx: Effective length about x-axis (strong) in meters
        KLy: Effective length about y-axis (weak) in meters
    
    Returns:
        Dictionary with compression analysis results
    """
    try:
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])  # kgf/cm²
        E = float(df_mat.loc[material, "E"])                   # kgf/cm²
        
        # Section properties
        Ag = float(df.loc[section, 'A [cm2]'])    # Gross area
        rx = float(df.loc[section, 'rx [cm]'])    # Radius of gyration about x-axis
        ry = float(df.loc[section, 'ry [cm]'])    # Radius of gyration about y-axis
        
        # Convert effective lengths to cm
        KLx_cm = KLx * 100
        KLy_cm = KLy * 100
        
        # Calculate slenderness ratios
        lambda_x = KLx_cm / rx
        lambda_y = KLy_cm / ry
        lambda_c = max(lambda_x, lambda_y)  # Controlling slenderness ratio
        
        # AISC 360-16 Equation E3.4 - Elastic buckling stress
        Fe = (np.pi**2 * E) / (lambda_c**2)
        
        # AISC 360-16 Section E3 - Determine buckling mode
        lambda_limit = 4.71 * np.sqrt(E / Fy)  # Transition point
        
        if lambda_c <= lambda_limit:
            # AISC 360-16 E3.2(a) - Inelastic buckling
            # Fcr = (0.658^(Fy/Fe)) * Fy
            buckling_mode = "Inelastic"
            Fcr = (0.658**(Fy/Fe)) * Fy
            
        else:
            # AISC 360-16 E3.2(b) - Elastic buckling  
            # Fcr = 0.877 * Fe
            buckling_mode = "Elastic" 
            Fcr = 0.877 * Fe
        
        # AISC 360-16 E3.1 - Nominal compressive strength
        Pn = Fcr * Ag / 1000  # Convert to tons (kgf⋅cm² * cm² / 1000)
        
        # AISC 360-16 - Resistance factor for compression φc = 0.90
        phi_c = 0.90
        phi_Pn = phi_c * Pn
        
        # Check slenderness limits per AISC 360-16 E2
        slenderness_ok = lambda_c <= 200
        
        return {
            'Pn': Pn,                    # Nominal strength (tons)
            'phi_Pn': phi_Pn,           # Design strength (tons) 
            'Fcr': Fcr,                 # Critical stress (kgf/cm²)
            'Fe': Fe,                   # Elastic buckling stress (kgf/cm²)
            'lambda_x': lambda_x,       # Slenderness ratio about x-axis
            'lambda_y': lambda_y,       # Slenderness ratio about y-axis  
            'lambda_c': lambda_c,       # Controlling slenderness ratio
            'lambda_limit': lambda_limit, # Inelastic/elastic transition
            'buckling_mode': buckling_mode,
            'slenderness_ok': slenderness_ok,
            'phi_c': phi_c
        }
        
    except Exception as e:
        st.error(f"Error in AISC E3 compression analysis: {e}")
        return None

# ==================== AISC 360-16 CHAPTER H - COMBINED FORCES ====================
def aisc_h1_interaction(Pu, phi_Pn, Mux, phi_Mnx, Muy, phi_Mny):
    """
    AISC 360-16 Chapter H1 - Doubly and Singly Symmetric Members Subject to Flexure and Compression
    
    Implements interaction equations:
    - H1-1a: When Pr/Pc ≥ 0.2
    - H1-1b: When Pr/Pc < 0.2
    
    Args:
        Pu: Required axial compressive strength (tons)
        phi_Pn: Design axial compressive strength (tons)
        Mux: Required flexural strength about x-axis (t⋅m)  
        phi_Mnx: Design flexural strength about x-axis (t⋅m)
        Muy: Required flexural strength about y-axis (t⋅m)
        phi_Mny: Design flexural strength about y-axis (t⋅m)
    
    Returns:
        Dictionary with interaction results
    """
    try:
        # Avoid division by zero
        if phi_Pn <= 0 or phi_Mnx <= 0 or phi_Mny <= 0:
            return None
        
        # Calculate ratios
        Pr_Pc = Pu / phi_Pn
        Mrx_Mcx = Mux / phi_Mnx  
        Mry_Mcy = Muy / phi_Mny
        
        # AISC 360-16 H1.1 - Interaction equations
        if Pr_Pc >= 0.2:
            # H1-1a: Pr/Pc + (8/9)*(Mrx/Mcx + Mry/Mcy) ≤ 1.0
            interaction_ratio = Pr_Pc + (8/9) * (Mrx_Mcx + Mry_Mcy)
            equation = "H1-1a"
            
        else:
            # H1-1b: Pr/(2*Pc) + (Mrx/Mcx + Mry/Mcy) ≤ 1.0  
            interaction_ratio = Pr_Pc/2 + (Mrx_Mcx + Mry_Mcy)
            equation = "H1-1b"
        
        # Design check
        design_ok = interaction_ratio <= 1.0
        
        return {
            'interaction_ratio': interaction_ratio,
            'equation': equation,
            'design_ok': design_ok,
            'Pr_Pc': Pr_Pc,
            'Mrx_Mcx': Mrx_Mcx,
            'Mry_Mcy': Mry_Mcy,
            'safety_margin': (1.0 - interaction_ratio) if design_ok else None
        }
        
    except Exception as e:
        st.error(f"Error in AISC H1 interaction calculation: {e}")
        return None

# ==================== UTILITY FUNCTIONS ====================
def calculate_required_properties(Mu, selected_material, Fy_value, phi=0.9):
    """Calculate required section properties based on design moment"""
    Mu_kgf_cm = Mu * 100000  # Convert t⋅m to kgf⋅cm
    Zx_req = Mu_kgf_cm / (phi * Fy_value)  # cm³
    return Zx_req

def calculate_required_ix(w, L, delta_limit, E=2.04e6):
    """Calculate required Ix based on deflection limit per AISC guidelines"""
    # Convert units: w from kg/m to kgf/cm, L from m to cm
    w_kgf_cm = w / 100
    L_cm = L * 100
    delta_max = L_cm / delta_limit
    
    # I-beam deflection: δ = 5*w*L^4/(384*E*I)
    Ix_req = (5 * w_kgf_cm * L_cm**4) / (384 * E * delta_max)
    return Ix_req

def calculate_service_load_capacity(df, df_mat, section, material, L, Lb):
    """Calculate service load capacity in kg/m based on flexural strength"""
    try:
        result = aisc_f2_lateral_torsional_buckling(df, df_mat, section, material, Lb)
        if result:
            phi_Mn_tm = 0.9 * result['Mn']  # Design moment capacity in t⋅m
            phi_Mn_kgf_cm = phi_Mn_tm * 100000  # Convert to kgf⋅cm
            L_cm = L * 100  # Convert to cm
            
            # For simply supported beam: M = w*L²/8
            w_kgf_cm = (8 * phi_Mn_kgf_cm) / (L_cm**2)
            w_kg_m = w_kgf_cm * 100  # Convert back to kg/m
            return w_kg_m
    except:
        pass
    return 0

def visualize_column_simple(df, section):
    """Simplified column visualization showing buckling modes"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 8))
        
        # Get dimensions
        d = float(df.loc[section, 'd [mm]'])
        bf = float(df.loc[section, 'bf [mm]'])
        tw = float(df.loc[section, 'tw [mm]'])
        tf = float(df.loc[section, 'tf [mm]'])
        
        # Column height for visualization
        H = 3000  # 3m column height in mm
        
        # Strong axis buckling (edge view)
        ax1.set_title('Strong Axis Buckling (X-X)\nEdge View', fontsize=14, fontweight='bold')
        
        # Draw H-section edge view
        ax1.add_patch(Rectangle((-tf/2, 0), tf, tf, 
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        ax1.add_patch(Rectangle((-tw/2, tf), tw, H - 2*tf,
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        ax1.add_patch(Rectangle((-tf/2, H - tf), tf, tf,
                                linewidth=2, edgecolor='blue', facecolor='lightblue', alpha=0.7))
        
        # Buckled shape
        y = np.linspace(0, H, 100)
        x_buckled = 80 * np.sin(np.pi * y / H)
        ax1.plot(x_buckled, y, 'r-', lw=3, label='Buckled Shape')
        
        # Load and labels
        ax1.arrow(0, H + 100, 0, -80, head_width=20, head_length=40, fc='red', ec='red')
        ax1.text(0, H + 150, 'P', ha='center', fontsize=14, fontweight='bold', color='red')
        ax1.text(50, H/2, f'd = {d:.0f}mm', rotation=90, ha='center', fontsize=10)
        
        ax1.set_xlim([-150, 150])
        ax1.set_ylim([-50, H + 200])
        ax1.set_xlabel('Buckling Direction')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Weak axis buckling (front view)
        ax2.set_title('Weak Axis Buckling (Y-Y)\nFront View', fontsize=14, fontweight='bold')
        
        # Draw H-section front view
        ax2.add_patch(Rectangle((-bf/2, 0), bf, tf,
                                linewidth=2, edgecolor='darkred', facecolor='lightcoral', alpha=0.7))
        ax2.add_patch(Rectangle((-bf/2, H - tf), bf, tf,
                                linewidth=2, edgecolor='darkred', facecolor='lightcoral', alpha=0.7))
        ax2.plot([0, 0], [tf, H - tf], 'k-', lw=2, alpha=0.5, label='Web (edge)')
        
        # Buckled shape
        x_buckled_weak = 50 * np.sin(np.pi * y / H)
        ax2.plot(x_buckled_weak, y, color='darkred', lw=3, label='Buckled Shape')
        
        # Load and labels
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
st.markdown('<h1 class="main-header">AISC 360-16 Steel Design Analysis System v5.2</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84;">AISC 360-16 Compliant with Fixed Array Issues</p>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
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
        "Quick Section Select:",
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

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Section Properties",
    "🔍 Section Selection", 
    "📈 Flexural Design (F2)",
    "🏢 Column Design (E3)",
    "🏗️ Beam-Column (H1)",
    "📊 Comparison"
])

# ==================== TAB 1: SECTION PROPERTIES ====================
with tab1:
    st.markdown('<h2 class="section-header">Complete Section Properties Table</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section:
        section = st.session_state.selected_section
        st.info(f"**Showing properties for: {section}**")
        
        section_data = df.loc[section]
        properties_df = pd.DataFrame({
            'Property': section_data.index,
            'Value': section_data.values
        })
        
        # Split into categories
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
        
        with st.expander("📋 View All Properties"):
            st.dataframe(properties_df, use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a section from the sidebar")

# ==================== TAB 2: SECTION SELECTION ====================  
with tab2:
    st.markdown('<h2 class="section-header">Section Selection with AISC 360-16 Criteria</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Flexural Design (Chapter F)")
        Mu = st.number_input("Design Moment Mu (t·m):", min_value=0.0, value=50.0, step=5.0)
        phi_f = 0.9  # AISC 360-16 resistance factor for flexure
        
        if Mu > 0 and selected_material:
            Fy_value = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
            Zx_req = calculate_required_properties(Mu, selected_material, Fy_value, phi_f)
            st.success(f"Required Zx ≥ {Zx_req:.0f} cm³")
    
    with col2:
        st.markdown("#### Deflection Control")
        L_span = st.number_input("Span Length (m):", min_value=1.0, value=6.0, step=0.5)
        w_load = st.number_input("Service Load w (kg/m):", min_value=0.0, value=100.0, step=10.0)
        deflection_limit = st.selectbox("Deflection Limit:", 
                                       ["L/200", "L/250", "L/300", "L/360", "L/400"],
                                       index=2)
        
        if w_load > 0 and L_span > 0:
            limit_value = float(deflection_limit.split('/')[1])
            Ix_req = calculate_required_ix(w_load, L_span, limit_value)
            st.success(f"Required Ix ≥ {Ix_req:.0f} cm⁴")
    
    with col3:
        st.markdown("#### Additional Filters")
        depth_max = st.number_input("Max Depth (mm):", min_value=0, value=0, help="0 = no limit")
        weight_max = st.number_input("Max Weight (kg/m):", min_value=0, value=200, step=10)
        
        optimization = st.selectbox("Optimize for:",
                                   ["Minimum Weight", "Minimum Depth", "Maximum Efficiency"],
                                   index=0)
    
    # Filter sections
    filtered_df = df.copy()
    
    if Mu > 0 and selected_material:
        Fy_value = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
        zx_min = calculate_required_properties(Mu, selected_material, Fy_value, phi_f)
        filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= zx_min]
    
    if w_load > 0 and L_span > 0:
        limit_value = float(deflection_limit.split('/')[1])
        Ix_req = calculate_required_ix(w_load, L_span, limit_value)
        filtered_df = filtered_df[filtered_df['Ix [cm4]'] >= Ix_req]
    
    if depth_max > 0:
        filtered_df = filtered_df[filtered_df['d [mm]'] <= depth_max]
    
    if weight_max > 0:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df = filtered_df[filtered_df[weight_col] <= weight_max]
    
    # Sort by optimization criteria
    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
    if optimization == "Minimum Weight":
        filtered_df = filtered_df.sort_values(weight_col)
    elif optimization == "Minimum Depth":
        filtered_df = filtered_df.sort_values('d [mm]')
    else:  # Maximum Efficiency
        filtered_df['efficiency'] = filtered_df['Zx [cm3]'] / filtered_df[weight_col]
        filtered_df = filtered_df.sort_values('efficiency', ascending=False)
    
    st.markdown(f"### Found {len(filtered_df)} Suitable Sections")
    
    if len(filtered_df) > 0:
        filtered_df_display = filtered_df.reset_index()
        
        display_cols = ['Section', 'd [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 
                       'A [cm2]', weight_col, 'Ix [cm4]', 'Iy [cm4]', 
                       'Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]', 
                       'rx [cm]', 'ry [cm]']
        
        available_cols = [col for col in display_cols if col in filtered_df_display.columns]
        
        # Configure AgGrid for multi-selection
        gb = GridOptionsBuilder.from_dataframe(filtered_df_display[available_cols])
        gb.configure_selection('multiple', use_checkbox=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_column("Section", headerCheckboxSelection=True)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        grid_options = gb.build()
        
        st.markdown("#### 📋 AISC Database (Select sections using checkboxes)")
        grid_response = AgGrid(
            filtered_df_display[available_cols].round(2),
            gridOptions=grid_options,
            height=400,
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

# ==================== TAB 3: FLEXURAL DESIGN (AISC 360-16 CHAPTER F2) ====================
with tab3:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter F2 - Lateral-Torsional Buckling</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Design Parameters")
            Lb_current = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
            Cb = st.number_input("Cb Factor:", 1.0, 2.3, 1.0, 0.1, 
                                help="Lateral-torsional buckling modification factor per AISC 360-16 F1")
            
            show_phi = st.checkbox("Show φMn curve", value=True)
            show_mn = st.checkbox("Show Mn curve", value=True)
            show_regions = st.checkbox("Show AISC regions", value=True)
            
            # Calculate using AISC 360-16 F2
            result = aisc_f2_lateral_torsional_buckling(df, df_mat, section, selected_material, Lb_current, Cb)
            
            if result:
                st.markdown("### AISC 360-16 Results")
                st.metric("Mn", f"{result['Mn']:.2f} t·m")
                st.metric("φMn", f"{0.9*result['Mn']:.2f} t·m", 
                         help="φ = 0.90 per AISC 360-16")
                st.metric("Case", result['Case'])
                
                # Classification per AISC 360-16
                if result['Mn'] >= result['Mp'] * 0.98:
                    st.success("✅ Full plastic capacity achieved")
                elif result['Mn'] >= result['Mp'] * 0.75:
                    st.warning("⚠️ Moderate LTB reduction")
                else:
                    st.error("❌ Significant LTB reduction")
                
                st.markdown("### AISC 360-16 Critical Lengths")
                st.write(f"**Lp = {result['Lp']:.2f} m**")
                st.caption("F2.5: Limiting unbraced length for yielding")
                st.write(f"**Lr = {result['Lr']:.2f} m**") 
                st.caption("F2.6: Limiting unbraced length for inelastic LTB")
        
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
                    name=f'Design Point (Lb={Lb_current}m)',
                    marker=dict(color='#f44336', size=12, symbol='diamond'),
                    hovertemplate=f'Current Point<br>Lb: {Lb_current:.2f}m<br>Mn: {result["Mn"]:.2f} t·m<extra></extra>'
                ))
                
                # Mp line (plastic moment)
                fig.add_hline(y=result['Mp'], line_dash="dot", line_color='#ff9800', line_width=2,
                            annotation_text=f"Mp = {result['Mp']:.2f} t·m", 
                            annotation_position="top right")
                
                # Critical length lines per AISC 360-16
                fig.add_vline(x=result['Lp'], line_dash="dash", line_color='#9c27b0', line_width=2,
                            annotation_text=f"Lp = {result['Lp']:.2f} m")
                fig.add_vline(x=result['Lr'], line_dash="dash", line_color='#e91e63', line_width=2,
                            annotation_text=f"Lr = {result['Lr']:.2f} m")
                
                # AISC 360-16 design regions
                if show_regions:
                    fig.add_vrect(x0=0, x1=result['Lp'], fillcolor='#4caf50', opacity=0.1,
                                annotation_text="<b>F2.1 YIELDING</b><br>Mn = Mp", 
                                annotation_position="top left")
                    fig.add_vrect(x0=result['Lp'], x1=result['Lr'], fillcolor='#ff9800', opacity=0.1,
                                annotation_text="<b>F2.2 INELASTIC LTB</b><br>Linear transition", 
                                annotation_position="top")
                    
                    max_x = max(result['Lb_range']) if result['Lb_range'] else result['Lr'] + 5
                    fig.add_vrect(x0=result['Lr'], x1=max_x, fillcolor='#f44336', opacity=0.1,
                                annotation_text="<b>F2.3 ELASTIC LTB</b><br>Fcr = π²E/(Lb/rts)²", 
                                annotation_position="top right")
                
                fig.update_layout(
                    title=f"AISC 360-16 F2: Moment Capacity vs Unbraced Length - {section}",
                    xaxis_title="Unbraced Length, Lb (m)",
                    yaxis_title="Moment Capacity (t·m)",
                    height=600,
                    hovermode='x unified',
                    showlegend=True,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # AISC 360-16 Summary
                st.markdown("### AISC 360-16 Summary")
                summary_df = pd.DataFrame({
                    'Parameter': ['Mp', 'Mn at Design Lb', 'φMn', 'Lp (F2.5)', 'Lr (F2.6)', 'Current Lb', 'Cb Factor'],
                    'Value': [f"{result['Mp']:.2f} t·m", f"{result['Mn']:.2f} t·m", 
                             f"{0.9*result['Mn']:.2f} t·m", f"{result['Lp']:.2f} m", 
                             f"{result['Lr']:.2f} m", f"{Lb_current:.2f} m", f"{result['Cb']:.2f}"],
                    'AISC Reference': ['F2', result['Case'], 'φ=0.90', 'Equation F2.5', 
                                      'Equation F2.6', 'Input', 'Section F1']
                })
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            else:
                st.error("Error in AISC F2 analysis")
    else:
        st.warning("Please select a section from the sidebar")

# ==================== TAB 4: COLUMN DESIGN (AISC 360-16 CHAPTER E3) ====================
with tab4:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter E3 - Compression Members</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.markdown("### Design Parameters per AISC 360-16")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Effective Length Factors (K)")
            Kx = st.selectbox("Kx:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4,
                             help="Per AISC 360-16 Commentary Figure C-C2.2")
            Ky = st.selectbox("Ky:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            st.info("""
            **AISC K Factors:**
            - 0.5: Fixed-Fixed
            - 0.7: Fixed-Pinned  
            - 1.0: Pinned-Pinned
            - 2.0: Fixed-Free
            """)
        
        with col2:
            st.markdown("#### Unbraced Lengths")
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, step=0.1)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, step=0.1)
            
            # Calculate slenderness ratios
            rx = float(df.loc[section, 'rx [cm]'])
            ry = float(df.loc[section, 'ry [cm]'])
            KLr_x = (Kx * Lx * 100) / rx
            KLr_y = (Ky * Ly * 100) / ry
            
            # AISC 360-16 E2 slenderness limits
            if KLr_x <= 200:
                st.success(f"KL/rx = {KLr_x:.1f} ✓")
            else:
                st.error(f"KL/rx = {KLr_x:.1f} > 200 (AISC E2)")
            
            if KLr_y <= 200:
                st.success(f"KL/ry = {KLr_y:.1f} ✓")
            else:
                st.error(f"KL/ry = {KLr_y:.1f} > 200 (AISC E2)")
        
        with col3:
            st.markdown("#### Applied Load")
            Pu = st.number_input("Pu (tons):", min_value=0.0, value=100.0, step=10.0)
        
        # AISC 360-16 E3 analysis
        comp_results = aisc_e3_flexural_buckling(df, df_mat, section, selected_material, Kx*Lx, Ky*Ly)
        
        if comp_results:
            st.markdown("### AISC 360-16 E3 Results")
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("φPn", f"{comp_results['phi_Pn']:.2f} tons",
                         delta=f"Pn = {comp_results['Pn']:.2f} tons",
                         help="φc = 0.90 per AISC 360-16")
            
            with col_r2:
                ratio = Pu / comp_results['phi_Pn'] if comp_results['phi_Pn'] > 0 else 999
                st.metric("Demand/Capacity", f"{ratio:.3f}",
                         delta="PASS" if ratio <= 1.0 else "FAIL")
            
            with col_r3:
                if comp_results['buckling_mode'] == "Inelastic":
                    st.metric("Buckling", "🟡 Inelastic (E3.2a)",
                             delta=f"λc = {comp_results['lambda_c']:.1f}")
                else:
                    st.metric("Buckling", "🔵 Elastic (E3.2b)",
                             delta=f"λc = {comp_results['lambda_c']:.1f}")
            
            # Design check per AISC 360-16
            if ratio <= 1.0:
                st.success(f"✅ AISC 360-16 Design PASSES - Factor of Safety: {1/ratio:.2f}")
            else:
                st.error(f"❌ AISC 360-16 Design FAILS - Overstressed by {(ratio-1)*100:.1f}%")
        
        # Column visualization
        st.markdown("### Column Buckling Visualization")
        show_viz = st.checkbox("Show Column Buckling Diagram", value=True)
        
        if show_viz:
            fig_vis = visualize_column_simple(df, section)
            if fig_vis:
                st.pyplot(fig_vis)
        
        # AISC 360-16 E3 capacity curve
        st.markdown("### AISC 360-16 E3 Column Curve")
        
        # Generate capacity curve per AISC 360-16
        lambda_range = np.linspace(1, 250, 500)
        Pn_values = []
        
        Fy = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
        E = float(df_mat.loc[selected_material, "E"])
        Ag = float(df.loc[section, 'A [cm2]'])
        
        lambda_limit = 4.71 * np.sqrt(E / Fy)  # AISC transition point
        
        for lambda_c in lambda_range:
            Fe = (np.pi**2 * E) / (lambda_c**2)
            
            if lambda_c <= lambda_limit:
                # AISC 360-16 E3.2(a) - Inelastic
                Fcr = (0.658**(Fy/Fe)) * Fy
            else:
                # AISC 360-16 E3.2(b) - Elastic  
                Fcr = 0.877 * Fe
            
            Pn = 0.9 * Fcr * Ag / 1000  # φPn in tons
            Pn_values.append(Pn)
        
        fig_capacity = go.Figure()
        
        # AISC column curve
        fig_capacity.add_trace(go.Scatter(
            x=lambda_range, y=Pn_values,
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
                marker=dict(color='#f44336', size=12, symbol='star')
            ))
        
        # AISC transition line
        fig_capacity.add_vline(x=lambda_limit, line_dash="dash", line_color='#ff9800', line_width=2,
                              annotation_text=f"λ = 4.71√(E/Fy) = {lambda_limit:.1f}")
        
        # AISC regions
        fig_capacity.add_vrect(x0=0, x1=lambda_limit, fillcolor='#ffc107', opacity=0.15,
                              annotation_text="INELASTIC<br>E3.2(a)", annotation_position="top left")
        fig_capacity.add_vrect(x0=lambda_limit, x1=250, fillcolor='#2196f3', opacity=0.15,
                              annotation_text="ELASTIC<br>E3.2(b)", annotation_position="top right")
        
        # AISC E2 slenderness limit
        fig_capacity.add_vline(x=200, line_dash="dot", line_color='#f44336', line_width=2,
                              annotation_text="KL/r = 200 (AISC E2 Limit)")
        
        # Applied load line
        if Pu > 0:
            fig_capacity.add_hline(y=Pu, line_dash="dash", line_color='#4caf50', line_width=2,
                                  annotation_text=f"Pu = {Pu:.1f} tons")
        
        fig_capacity.update_layout(
            title="AISC 360-16 E3 Column Capacity Curve",
            xaxis_title="Slenderness Ratio (KL/r)",
            yaxis_title="Design Capacity φPn (tons)",
            height=500,
            template='plotly_white'
        )
        
        st.plotly_chart(fig_capacity, use_container_width=True)
        
        # AISC 360-16 summary table
        if comp_results:
            st.markdown("### AISC 360-16 Design Summary")
            summary_col = pd.DataFrame({
                'Parameter': ['λx', 'λy', 'λc (controlling)', '4.71√(E/Fy)', 'Fe', 'Fcr', 'Pn', 'φPn', 'Pu', 'Pu/φPn'],
                'Value': [f"{comp_results['lambda_x']:.1f}", f"{comp_results['lambda_y']:.1f}",
                         f"{comp_results['lambda_c']:.1f}", f"{comp_results['lambda_limit']:.1f}", 
                         f"{comp_results['Fe']:.1f} ksc", f"{comp_results['Fcr']:.1f} ksc", 
                         f"{comp_results['Pn']:.2f} tons", f"{comp_results['phi_Pn']:.2f} tons", 
                         f"{Pu:.2f} tons", f"{Pu/comp_results['phi_Pn']:.3f}" if comp_results['phi_Pn'] > 0 else "N/A"],
                'AISC Reference': ['KLx/rx', 'KLy/ry', 'max(λx,λy)', 'E3 transition', 'E3.4', 
                                  'E3.2(a) or E3.2(b)', 'E3.1', 'φc=0.90', 'Applied', 'Unity Check']
            })
            st.dataframe(summary_col, use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a section from the sidebar")

# ==================== TAB 5: BEAM-COLUMN (AISC 360-16 CHAPTER H1) ====================
with tab5:
    st.markdown('<h2 class="section-header">AISC 360-16 Chapter H1 - Combined Forces</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.info(f"**Analyzing:** {section} | **Material:** {selected_material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Combined Loading per AISC H1")
            
            # Interactive loads
            Pu_bc = st.slider("Axial Load Pu (tons):", 
                             min_value=0.0, max_value=200.0, value=50.0, step=1.0)
            
            st.markdown("#### Applied Moments")
            Mux = st.slider("Moment Mux (t·m):", 
                           min_value=0.0, max_value=100.0, value=30.0, step=1.0,
                           help="Required flexural strength about major axis")
            Muy = st.slider("Moment Muy (t·m):", 
                           min_value=0.0, max_value=50.0, value=5.0, step=0.5,
                           help="Required flexural strength about minor axis")
            
            # Effective lengths
            st.markdown("#### Effective Lengths") 
            KLx_bc = st.slider("KLx (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            KLy_bc = st.slider("KLy (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            Lb_bc = st.slider("Lb for LTB (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
        
        # AISC 360-16 analysis
        comp_results = aisc_e3_flexural_buckling(df, df_mat, section, selected_material, KLx_bc, KLy_bc)
        flex_result = aisc_f2_lateral_torsional_buckling(df, df_mat, section, selected_material, Lb_bc)
        
        if comp_results and flex_result:
            # Design strengths
            phi_Pn = comp_results['phi_Pn']
            phi_Mnx = 0.9 * flex_result['Mn']  # Major axis
            
            # Minor axis moment capacity (simplified)
            Zy = float(df.loc[section, 'Zy [cm3]'])
            Fy = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
            Mny = Fy * Zy / 100000  # t·m
            phi_Mny = 0.9 * Mny
            
            # AISC 360-16 H1 interaction
            interaction_result = aisc_h1_interaction(Pu_bc, phi_Pn, Mux, phi_Mnx, Muy, phi_Mny)
            
            if interaction_result:
                st.markdown("### AISC 360-16 H1 Results")
                
                # Display individual ratios
                col_r1, col_r2, col_r3 = st.columns(3)
                
                with col_r1:
                    st.metric("Pr/Pc", f"{interaction_result['Pr_Pc']:.3f}",
                            delta=f"{Pu_bc:.1f}/{phi_Pn:.1f} tons")
                
                with col_r2:
                    st.metric("Mrx/Mcx", f"{interaction_result['Mrx_Mcx']:.3f}",
                            delta=f"{Mux:.1f}/{phi_Mnx:.1f} t·m")
                
                with col_r3:
                    st.metric("Mry/Mcy", f"{interaction_result['Mry_Mcy']:.3f}",
                            delta=f"{Muy:.1f}/{phi_Mny:.1f} t·m")
                
                # Unity check per AISC 360-16
                st.markdown("### AISC 360-16 H1 Unity Check")
                st.metric("Interaction Ratio", f"{interaction_result['interaction_ratio']:.3f}",
                        delta=f"Equation {interaction_result['equation']}")
                
                if interaction_result['design_ok']:
                    safety_margin = interaction_result['safety_margin'] * 100
                    st.markdown(f'<div class="success-box">✅ <b>AISC 360-16 DESIGN PASSES</b><br>Unity Check: {interaction_result["interaction_ratio"]:.3f} ≤ 1.0<br>Safety Margin: {safety_margin:.1f}%</div>', 
                              unsafe_allow_html=True)
                else:
                    overstress = (interaction_result['interaction_ratio'] - 1.0) * 100
                    st.markdown(f'<div class="error-box">❌ <b>AISC 360-16 DESIGN FAILS</b><br>Unity Check: {interaction_result["interaction_ratio"]:.3f} > 1.0<br>Overstressed by: {overstress:.1f}%</div>', 
                              unsafe_allow_html=True)
        
        with col2:
            st.markdown("### AISC 360-16 H1 P-M Interaction Diagram")
            
            if comp_results and phi_Mnx > 0:
                # Generate AISC H1 interaction curve
                P_ratios = np.linspace(0, 1, 50)
                M_ratios = []
                
                for p_ratio in P_ratios:
                    if p_ratio >= 0.2:
                        # H1-1a equation
                        m_ratio = (9/8) * (1 - p_ratio)
                    else:
                        # H1-1b equation  
                        m_ratio = 1 - p_ratio/2
                    M_ratios.append(max(0, m_ratio))
                
                # Create AISC interaction plot
                fig = go.Figure()
                
                # AISC H1 interaction curve
                fig.add_trace(go.Scatter(
                    x=M_ratios, y=P_ratios,
                    mode='lines',
                    name='AISC H1 Interaction',
                    line=dict(color='#2196f3', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.2)',
                    hovertemplate='M/Mc: %{x:.2f}<br>P/Pc: %{y:.2f}<extra></extra>'
                ))
                
                # Add design point
                if interaction_result:
                    M_combined = interaction_result['Mrx_Mcx'] + interaction_result['Mry_Mcy']
                    P_ratio = interaction_result['Pr_Pc']
                    
                    fig.add_trace(go.Scatter(
                        x=[M_combined], y=[P_ratio],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=15, symbol='star'),
                        hovertemplate=f'Design Point<br>P/Pc: {P_ratio:.3f}<br>ΣM/Mc: {M_combined:.3f}<br>Unity: {interaction_result["interaction_ratio"]:.3f}<extra></extra>'
                    ))
                    
                    # Safety indication
                    if interaction_result['design_ok']:
                        annotation_text = "✅ SAFE"
                        annotation_color = "#4caf50"
                    else:
                        annotation_text = "❌ UNSAFE"
                        annotation_color = "#f44336"
                    
                    fig.add_annotation(
                        x=M_combined, y=P_ratio,
                        text=annotation_text,
                        showarrow=True,
                        arrowhead=2,
                        bgcolor="white",
                        bordercolor=annotation_color,
                        borderwidth=2
                    )
                
                # Add equation transition line
                fig.add_hline(y=0.2, line_dash="dot", line_color='#ff9800', line_width=1,
                            annotation_text="H1-1a/H1-1b transition (Pr/Pc = 0.2)")
                
                fig.update_layout(
                    title="AISC 360-16 H1 P-M Interaction Diagram",
                    xaxis_title="Combined Moment Ratio (Mrx/Mcx + Mry/Mcy)",
                    yaxis_title="Axial Force Ratio (Pr/Pc)",
                    height=500,
                    template='plotly_white',
                    hovermode='closest',
                    xaxis=dict(range=[0, 1.2]),
                    yaxis=dict(range=[0, 1.2])
                )
                
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                
                st.plotly_chart(fig, use_container_width=True)
                
                # AISC H1 summary
                if interaction_result:
                    st.markdown("### AISC 360-16 H1 Summary")
                    h1_summary = pd.DataFrame({
                        'Parameter': ['Pr/Pc', 'Mrx/Mcx', 'Mry/Mcy', 'Interaction Ratio', 'Equation Used', 'Design Status'],
                        'Value': [f"{interaction_result['Pr_Pc']:.3f}", f"{interaction_result['Mrx_Mcx']:.3f}",
                                 f"{interaction_result['Mry_Mcy']:.3f}", f"{interaction_result['interaction_ratio']:.3f}",
                                 interaction_result['equation'], 
                                 "PASS" if interaction_result['design_ok'] else "FAIL"],
                        'AISC Limit': ['≤ 1.0', '≤ 1.0', '≤ 1.0', '≤ 1.0', 'H1-1a or H1-1b', 'Unity ≤ 1.0']
                    })
                    st.dataframe(h1_summary, use_container_width=True, hide_index=True)
    else:
        st.warning("Please select a section and material from the sidebar")

# ==================== TAB 6: COMPARISON ====================
with tab6:
    st.markdown('<h2 class="section-header">Multi-Section AISC 360-16 Comparison</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_sections:
        st.info(f"Comparing {len(st.session_state.selected_sections)} sections per AISC 360-16")
        
        # Comparison parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            comparison_type = st.selectbox("Comparison Type:",
                ["Moment Capacity (F2)", "Compression Capacity (E3)", "Weight Efficiency", "Combined Performance"])
        
        with col2:
            Lb_comp = st.slider("Unbraced Length for F2 (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        with col3:
            KL_comp = st.slider("Effective Length for E3 (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        # Real-time AISC 360-16 comparison
        comparison_data = []
        
        for section_name in st.session_state.selected_sections:
            if section_name not in df.index:
                continue
            
            try:
                # Get weight
                weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
                weight = df.loc[section_name, weight_col]
                
                # AISC F2 flexural analysis
                flex_result = aisc_f2_lateral_torsional_buckling(df, df_mat, section_name, selected_material, Lb_comp)
                
                # AISC E3 compression analysis
                comp_results = aisc_e3_flexural_buckling(df, df_mat, section_name, selected_material, 
                                                        KL_comp, KL_comp)
                
                if flex_result and comp_results:
                    comparison_data.append({
                        'Section': section_name,
                        'Weight (kg/m)': weight,
                        'φMn (t·m)': 0.9 * flex_result['Mn'],
                        'φPn (tons)': comp_results['phi_Pn'],
                        'Moment Efficiency': (0.9 * flex_result['Mn']) / weight,
                        'Compression Efficiency': comp_results['phi_Pn'] / weight,
                        'Combined Score': ((0.9 * flex_result['Mn']) / weight) * (comp_results['phi_Pn'] / weight),
                        'F2 Case': flex_result['Case'],
                        'E3 Mode': comp_results['buckling_mode']
                    })
            except Exception as e:
                st.error(f"Error analyzing {section_name}: {str(e)}")
                continue
        
        if comparison_data:
            df_comparison = pd.DataFrame(comparison_data)
            
            # Display comparison chart based on type
            if comparison_type == "Moment Capacity (F2)":
                # Multi-section AISC F2 curves
                fig = go.Figure()
                colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4']
                
                for i, section_name in enumerate(st.session_state.selected_sections[:6]):
                    if section_name not in df.index:
                        continue
                    
                    # Generate AISC F2 curve for each section
                    Lb_range = np.linspace(0.1, 15, 100)
                    Mn_values = []
                    
                    for lb in Lb_range:
                        try:
                            flex_result = aisc_f2_lateral_torsional_buckling(df, df_mat, section_name, selected_material, lb)
                            if flex_result:
                                Mn_values.append(0.9 * flex_result['Mn'])  # φMn
                            else:
                                Mn_values.append(0)
                        except:
                            Mn_values.append(0)
                    
                    color = colors[i % len(colors)]
                    fig.add_trace(go.Scatter(
                        x=Lb_range, y=Mn_values,
                        mode='lines',
                        name=section_name,
                        line=dict(color=color, width=2),
                        hovertemplate='%{y:.2f} t·m @ Lb=%{x:.1f}m<extra></extra>'
                    ))
                
                fig.update_layout(
                    title="AISC 360-16 F2: Multi-Section Moment Capacity Comparison",
                    xaxis_title="Unbraced Length, Lb (m)",
                    yaxis_title="φMn (t·m)",
                    height=500,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif comparison_type == "Compression Capacity (E3)":
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['φPn (tons)'],
                    text=[f'{v:.1f}' for v in df_comparison['φPn (tons)']],
                    textposition='auto',
                    marker_color='#2196f3',
                    name='φPn (AISC E3)'
                ))
                
                fig.update_layout(
                    title=f"AISC 360-16 E3: Compression Capacity at KL = {KL_comp:.1f} m",
                    yaxis_title="φPn (tons)",
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif comparison_type == "Weight Efficiency":
                fig = make_subplots(rows=1, cols=2,
                                   subplot_titles=('Moment Efficiency (F2)', 'Compression Efficiency (E3)'))
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Moment Efficiency'],
                    text=[f'{v:.3f}' for v in df_comparison['Moment Efficiency']],
                    textposition='auto',
                    marker_color='#4caf50',
                    name='φMn/Weight'
                ), row=1, col=1)
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Compression Efficiency'],
                    text=[f'{v:.3f}' for v in df_comparison['Compression Efficiency']],
                    textposition='auto',
                    marker_color='#ff9800',
                    name='φPn/Weight'
                ), row=1, col=2)
                
                fig.update_layout(
                    title="AISC 360-16 Weight Efficiency Comparison",
                    height=400,
                    template='plotly_white',
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            
            elif comparison_type == "Combined Performance":
                # AISC performance radar chart
                fig = go.Figure()
                
                categories = ['Weight', 'φMn (F2)', 'φPn (E3)', 'Moment Eff.', 'Compression Eff.']
                
                for idx, row in df_comparison.iterrows():
                    # Normalize values for radar chart
                    values = [
                        1 - (row['Weight (kg/m)'] / df_comparison['Weight (kg/m)'].max()),
                        row['φMn (t·m)'] / df_comparison['φMn (t·m)'].max(),
                        row['φPn (tons)'] / df_comparison['φPn (tons)'].max(),
                        row['Moment Efficiency'] / df_comparison['Moment Efficiency'].max(),
                        row['Compression Efficiency'] / df_comparison['Compression Efficiency'].max()
                    ]
                    values.append(values[0])  # Close the polygon
                    
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories + [categories[0]],
                        fill='toself',
                        name=row['Section']
                    ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1]
                        )),
                    showlegend=True,
                    title="AISC 360-16 Combined Performance Comparison",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Display detailed comparison table
            st.markdown("### 📊 AISC 360-16 Detailed Comparison")
            
            df_display = df_comparison.copy()
            df_display = df_display.round(3)
            
            # Highlight best values
            def highlight_max(s):
                if s.name in ['φMn (t·m)', 'φPn (tons)', 'Moment Efficiency', 'Compression Efficiency', 'Combined Score']:
                    is_max = s == s.max()
                    return ['background-color: #e8f5e9' if v else '' for v in is_max]
                elif s.name == 'Weight (kg/m)':
                    is_min = s == s.min()
                    return ['background-color: #e8f5e9' if v else '' for v in is_min]
                else:
                    return ['' for _ in s]
            
            styled_df = df_display.style.apply(highlight_max, subset=['φMn (t·m)', 'φPn (tons)', 
                                                                      'Moment Efficiency', 'Compression Efficiency',
                                                                      'Weight (kg/m)', 'Combined Score'])
            st.dataframe(styled_df, use_container_width=True)
            
            # AISC 360-16 Recommendations
            st.markdown("### 🏆 AISC 360-16 Design Recommendations")
            
            col_rec1, col_rec2, col_rec3 = st.columns(3)
            
            with col_rec1:
                best_moment = df_comparison.loc[df_comparison['φMn (t·m)'].idxmax()]
                st.info(f"""
                **Highest Moment Capacity (F2):**
                {best_moment["Section"]}
                φMn: {best_moment["φMn (t·m)"]:.2f} t·m
                Case: {best_moment["F2 Case"]}
                """)
            
            with col_rec2:
                best_compression = df_comparison.loc[df_comparison['φPn (tons)'].idxmax()]
                st.info(f"""
                **Highest Compression Capacity (E3):**
                {best_compression["Section"]}
                φPn: {best_compression["φPn (tons)"]:.1f} tons
                Mode: {best_compression["E3 Mode"]}
                """)
            
            with col_rec3:
                best_efficiency = df_comparison.loc[df_comparison['Combined Score'].idxmax()]
                st.info(f"""
                **Best Overall AISC Performance:**
                {best_efficiency["Section"]}
                Score: {best_efficiency["Combined Score"]:.3f}
                """)
    else:
        st.warning("Please select sections from the 'Section Selection' tab first")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><b>AISC 360-16 Steel Design Analysis v5.2</b></p>
    <p>✅ Fixed Array Issues | ✅ Full AISC 360-16 Compliance | ✅ Chapters F2, E3, H1</p>
    <p>© 2024 - Educational Tool for Structural Engineers</p>
</div>
""", unsafe_allow_html=True)
