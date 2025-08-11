# Complete Steel Design Analysis Application with Beam-Column Analysis
# GitHub: Thana-site/Steel_Design_2003
# Version: 2.0 with Beam-Column Analysis

# ==================== IMPORTS ====================
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math as mt
import numpy as np
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder
import os
import requests
import json

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="Steel Design Analysis",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #ff7f0e;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 0.5rem 0;
    }
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28a745;
        margin: 0.5rem 0;
    }
    .comparison-table {
        border: 2px solid #1f77b4;
        border-radius: 10px;
        padding: 1rem;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FILE PATHS ====================
file_path = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-Material.csv"
file_path_chf = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-CHF.csv"

# ==================== SESSION STATE INITIALIZATION ====================
def safe_session_state_init():
    """Safely initialize session state variables"""
    try:
        if 'selected_sections' not in st.session_state:
            st.session_state.selected_sections = []
        if 'input_mode' not in st.session_state:
            st.session_state.input_mode = "slider"
        if 'section_lb_values' not in st.session_state:
            st.session_state.section_lb_values = {}
        if 'option' not in st.session_state:
            st.session_state.option = None
        if 'option_mat' not in st.session_state:
            st.session_state.option_mat = None
    except Exception as e:
        st.error(f"Error initializing session state: {e}")

# Call safe initialization
safe_session_state_init()

# ==================== DATA LOADING FUNCTIONS ====================
@st.cache_data
def check_url(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        st.error(f"URL check error: {e}")
        return False

@st.cache_data
def load_data():
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        df_chf = pd.read_csv(file_path_chf, index_col=0, encoding="utf-8")
        
        if df.empty or df_mat.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False
        return df, df_mat, df_chf, True
    except Exception as e:
        st.error(f"An error occurred while loading the files: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False

# ==================== HELPER FUNCTIONS ====================
def validate_section_data(df_selected):
    """Validate selected section data"""
    required_columns = ['Section']
    missing_columns = [col for col in required_columns if col not in df_selected.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {missing_columns}"
    
    return True, "Data validation passed"

def safe_analysis(section, df, df_mat, option_mat, lb_value):
    """Perform safe analysis with error handling"""
    try:
        if section not in df.index:
            return None, f"Section {section} not found in database"
        
        result = F2(df, df_mat, section, option_mat, lb_value)
        return result, None
    except Exception as e:
        return None, f"Analysis error for {section}: {str(e)}"

def standardize_column_names(df):
    """Standardize column names"""
    column_mapping = {
        'w [kg/m]': 'Unit Weight [kg/m]',
        'Weight [kg/m]': 'Unit Weight [kg/m]',
        'Unit weight [kg/m]': 'Unit Weight [kg/m]'
    }
    
    for old_name, new_name in column_mapping.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    
    return df

def safe_get_weight(df, section):
    """Safely get weight value"""
    weight_columns = ['Unit Weight [kg/m]', 'w [kg/m]', 'Weight [kg/m]']
    
    for col in weight_columns:
        if col in df.columns:
            try:
                weight = float(df.loc[section, col])
                return weight
            except (KeyError, ValueError, TypeError):
                continue
    
    st.warning(f"⚠️ Weight not found for section {section}")
    return 0.0

# ==================== STEEL ANALYSIS FUNCTIONS ====================
def Flexural_classify(df, df_mat, option, option_mat):
    """Classification for flexural members"""
    if option_mat not in df_mat.index:
        raise KeyError(f"Option '{option_mat}' not found in the DataFrame.")
    
    if "Yield Point (ksc)" not in df_mat.columns or "E" not in df_mat.columns:
        raise KeyError("'Yield Point (ksc)' or 'E' column not found in the DataFrame.")

    Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
    E = float(df_mat.loc[option_mat, "E"])

    lamw = float(df.loc[option, 'h/tw'])
    lamf = float(df.loc[option, '0.5bf/tf'])
    
    lamw_limp = 3.76 * mt.sqrt(E / Fy)
    lamw_limr = 5.70 * mt.sqrt(E / Fy)

    lamf_limp = 0.38 * mt.sqrt(E / Fy)
    lamf_limr = 1.00 * mt.sqrt(E / Fy)

    if lamw < lamw_limp:
        Classify_Web_Flexural = "Compact Web"
    elif lamw_limp < lamw < lamw_limr:
        Classify_Web_Flexural = "Non-Compact Web"
    else:
        Classify_Web_Flexural = "Slender Web"
        
    if lamf < lamf_limp:
        Classify_flange_Flexural = "Compact Flange"
    elif lamf_limp < lamf < lamf_limr:
        Classify_flange_Flexural = "Non-Compact Flange"
    else:
        Classify_flange_Flexural = "Slender Flange"

    return lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural

def compression_classify(df, df_mat, option, option_mat):
    """Classification for compression members"""
    Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
    E = float(df_mat.loc[option_mat, "E"])          
    lamw = float(df.loc[option, 'h/tw'])
    lamf = float(df.loc[option, '0.5bf/tf'])
    lamw_lim = 1.49 * mt.sqrt(E / Fy)
    lamf_lim = 0.56 * mt.sqrt(E / Fy)
    
    if lamw < lamw_lim:
        Classify_Web_Compression = "Non-Slender Web"
    else:
        Classify_Web_Compression = "Slender Web"
        
    if lamf < lamf_lim:
        Classify_flange_Compression = "Non-Slender Flange"
    else:
        Classify_flange_Compression = "Slender Flange"
        
    return lamf, lamw, lamw_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression

def F2(df, df_mat, option, option_mat, Lb):
    """F2 Analysis for doubly symmetric compact I-shaped members"""
    Cb = 1
    section = option
    Lb = Lb * 100  # Convert Lb to cm
    Lp = float(df.loc[section, "Lp [cm]"])
    Lr = float(df.loc[section, "Lr [cm]"])
    S_Major = float(df.loc[section, "Sx [cm3]"])
    Z_Major = float(df.loc[section, 'Zx [cm3]'])
    rts = float(df.loc[section, 'rts [cm6]'])
    j = float(df.loc[section, 'j [cm4]'])
    c = 1
    h0 = float(df.loc[section, 'ho [mm]']) / 10  # Convert to cm
    Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
    E = float(df_mat.loc[option_mat, "E"])

    Mni = []
    Mnr = []
    Lni = []
    Lri_values = []

    if Lb < Lp:
        Case = "F2.1 - Plastic Yielding"
        Mp = Fy * Z_Major 
        Mn = Mp / 100000
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100
    elif Lp <= Lb < Lr:
        Case = "F2.2 - Lateral-Torsional Buckling"
        Mp = Fy * Z_Major
        Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb - Lp) / (Lr - Lp))))
        Mn = Mn / 100000
        Mp = Mp / 100000
        Mn = min(Mp, Mn)
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100
    else:
        Case = "F2.3 - Lateral-Torsional Buckling"
        Term_1 = (Cb * mt.pi ** 2 * E) / (((Lb) / rts) ** 2)
        Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * (((Lb) / rts) ** 2)
        Term12 = Term_1 * mt.sqrt(1 + Term_2)
        Mn = Term12 * S_Major
        Mn = Mn / 100000
        Mp = Fy * Z_Major 
        Mp = Mp / 100000
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100

    Mn = np.floor(Mn * 100) / 100
    Mn_F2C = 0.7 * Fy * S_Major / 100000
    Mn_F2C = np.floor(Mn_F2C * 100) / 100

    Mni.append(Mp)
    Lni.append(np.floor(0 * 100) / 100)

    Mni.append(Mp)
    Lni.append(np.floor((Lp / 100) * 100) / 100)

    Mni.append(Mn_F2C)
    Lni.append(np.floor((Lr / 100) * 100) / 100)

    Lro = Lr
    Lr = Lr / 100
    Lr = np.ceil(Lr * 100) / 100
    Lr += 0.01
    Lrii = Lr
    Lriii = Lrii + 11

    i = Lrii
    while i < Lriii:
        Lbi = i * 100
        rounded_i = np.floor(i * 100) / 100
        Lri_values.append(rounded_i)
        
        Term_1 = (Cb * mt.pi ** 2 * E) / ((Lbi / rts) ** 2)
        Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * ((Lbi / rts) ** 2)
        fcr = Term_1 * mt.sqrt(1 + Term_2)
        Mnc = fcr * S_Major
        Mnc = Mnc / 100000
        Mnc = np.floor(Mnc * 100) / 100
        Mnr.append(Mnc)
        
        i += 0.5

    Mni.append(Mnr)
    Lni.append(Lri_values)

    Lb = Lb / 100
    Lp = Lp / 100
    Lr = Lro / 100

    Lb = np.floor(Lb * 100) / 100
    Lp = np.floor(Lp * 100) / 100
    Lr = np.floor(Lr * 100) / 100

    return Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case

def classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis):
    """Classify section based on element slenderness"""
    if lamf < lamf_limp:
        flange = "Compact Flange"
    elif lamf_limp <= lamf < lamf_limr:
        flange = "Non-Compact Flange"
    else:
        flange = "Slender Flange"
    
    if lamw < lamw_limp:
        web = "Compact Web"
    elif lamw_limp <= lamw < lamw_limr:
        web = "Non-Compact Web"
    else:
        web = "Slender Web"
    
    if bending_axis == "Major axis bending":
        if flange == "Compact Flange" and web == "Compact Web":
            return "F2: Doubly Symmetric Compact I-Shaped Members"
        elif flange == "Non-Compact Flange" and web == "Compact Web":
            return "F3: Non-Compact Flange, Compact Web"
        elif flange == "Slender Flange" and web == "Compact Web":
            return "F4: Slender Flange, Compact Web"
        else:
            return "F5: Other I-Shaped Members"
    elif bending_axis == "Minor axis bending":
        if flange == "Compact Flange":
            return "F6: Minor Axis Bending (Compact Flange)"
        elif flange == "Non-Compact Flange":
            return "F6: Minor Axis Bending (Non-Compact Flange)"
        elif flange == "Slender Flange":
            return "F6: Minor Axis Bending (Slender Flange)"
    
    return "Classification not determined"

# ==================== BEAM-COLUMN ANALYSIS FUNCTIONS ====================
def calculate_Fe(E, KL, r):
    """Calculate elastic buckling stress Fe"""
    Fe = (mt.pi**2 * E) / ((KL/r)**2)
    return Fe

def calculate_Fcr(Fy, Fe):
    """Calculate critical buckling stress Fcr per AISC 360 E3"""
    if Fy/Fe <= 2.25:
        # Inelastic buckling
        Fcr = Fy * (0.658**(Fy/Fe))
    else:
        # Elastic buckling
        Fcr = 0.877 * Fe
    return Fcr

def calculate_Pn(df, df_mat, section, option_mat, KLx, KLy, KLz=None):
    """
    Calculate nominal compressive strength Pn
    KLx, KLy: Effective lengths about x and y axes (m)
    KLz: Effective length for torsional buckling (m), if None uses min(KLx, KLy)
    """
    try:
        # Get material properties
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        E = float(df_mat.loc[option_mat, "E"])
        G = E / (2 * (1 + 0.3))  # Shear modulus (assuming Poisson's ratio = 0.3)
        
        # Get section properties
        Ag = float(df.loc[section, 'A [cm2]'])  # Gross area
        rx = float(df.loc[section, 'rx [cm]'])
        ry = float(df.loc[section, 'ry [cm]'])
        
        # Convert KL from m to cm
        KLx = KLx * 100
        KLy = KLy * 100
        
        # Calculate slenderness ratios
        lambda_x = KLx / rx
        lambda_y = KLy / ry
        
        # Governing slenderness ratio for flexural buckling
        lambda_max = max(lambda_x, lambda_y)
        
        # Calculate elastic buckling stress
        Fe = (mt.pi**2 * E) / (lambda_max**2)
        
        # Calculate critical buckling stress
        Fcr = calculate_Fcr(Fy, Fe)
        
        # Calculate nominal compressive strength
        Pn = Fcr * Ag / 1000  # Convert to tons
        
        # Check for local buckling (if needed)
        lamf, lamw, lamw_lim, lamf_lim, Class_flange, Class_web = compression_classify(df, df_mat, section, option_mat)
        
        # Apply reduction for slender elements if necessary
        Q = 1.0  # Reduction factor for local buckling
        if "Slender" in Class_flange or "Slender" in Class_web:
            # Simplified approach - should be refined based on actual slender element calculations
            Q = 0.9  # Placeholder - implement detailed Q calculation if needed
            Pn = Q * Pn
        
        return {
            'Pn': Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_max': lambda_max,
            'Q': Q,
            'Classification': f"{Class_flange}, {Class_web}"
        }
        
    except Exception as e:
        st.error(f"Error in compression calculation: {e}")
        return None

def calculate_Cm(M1, M2, case="no_transverse"):
    """
    Calculate moment modification factor Cm
    M1: Smaller end moment (absolute value)
    M2: Larger end moment (absolute value)
    case: "no_transverse" for no transverse loads, "transverse" for transverse loads
    """
    if case == "transverse":
        return 1.0
    else:
        # For members without transverse loads
        if M2 == 0:
            return 1.0
        ratio = M1 / M2  # M1/M2 is positive for double curvature, negative for single
        Cm = 0.6 - 0.4 * ratio
        return max(0.4, Cm)

def calculate_B1(Pr, Pe1, Cm, alpha=1.0):
    """
    Calculate amplification factor B1 for member stability
    Pr: Required axial strength
    Pe1: Elastic buckling strength
    Cm: Moment modification factor
    alpha: 1.0 for LRFD
    """
    if Pe1 <= 0:
        return 1.0
    
    B1 = Cm / (1 - alpha * Pr / Pe1)
    return max(1.0, B1)

def beam_column_interaction_H1(Pr, Pc, Mrx, Mry, Mcx, Mcy):
    """
    Check H1-1 interaction equations for doubly symmetric members
    Returns interaction ratio and pass/fail status
    """
    # H1-1a: For Pr/Pc >= 0.2
    if Pr/Pc >= 0.2:
        ratio_a = Pr/Pc + (8/9) * (Mrx/Mcx + Mry/Mcy)
        check_a = ratio_a <= 1.0
        return ratio_a, check_a, "H1-1a"
    
    # H1-1b: For Pr/Pc < 0.2
    else:
        ratio_b = Pr/(2*Pc) + (Mrx/Mcx + Mry/Mcy)
        check_b = ratio_b <= 1.0
        return ratio_b, check_b, "H1-1b"

def analyze_beam_column(df, df_mat, section, option_mat, Pu, Mux, Muy, KLx, KLy, Lbx, Cm_x=1.0, Cm_y=1.0):
    """
    Complete beam-column analysis
    Pu: Ultimate axial load (tons)
    Mux, Muy: Ultimate moments about x and y axes (t-m)
    KLx, KLy: Effective lengths (m)
    Lbx: Unbraced length for lateral-torsional buckling (m)
    Cm_x, Cm_y: Moment modification factors
    """
    try:
        results = {}
        
        # 1. Calculate compression capacity
        comp_results = calculate_Pn(df, df_mat, section, option_mat, KLx, KLy)
        if comp_results is None:
            return None
        
        Pn = comp_results['Pn']
        phi_c = 0.9  # Resistance factor for compression
        Pc = phi_c * Pn
        
        # 2. Calculate flexural capacity about x-axis
        Mnx, _, Lpx, Lrx, Mpx, _, _, Case_x = F2(df, df_mat, section, option_mat, Lbx)
        phi_b = 0.9  # Resistance factor for flexure
        Mcx = phi_b * Mnx
        
        # 3. Calculate flexural capacity about y-axis (usually full plastic moment)
        Zy = float(df.loc[section, 'Zy [cm3]'])
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        Mny = Fy * Zy / 100000  # Convert to t-m
        Mcy = phi_b * Mny
        
        # 4. Calculate elastic buckling loads for stability analysis
        E = float(df_mat.loc[option_mat, "E"])
        Ix = float(df.loc[section, 'Ix [cm4]'])
        Iy = float(df.loc[section, 'Iy [cm4]'])
        
        # Elastic buckling about x-axis
        Pe1x = (mt.pi**2 * E * Ix) / ((KLx * 100)**2) / 1000  # tons
        
        # Elastic buckling about y-axis  
        Pe1y = (mt.pi**2 * E * Iy) / ((KLy * 100)**2) / 1000  # tons
        
        # 5. Calculate amplification factors
        B1x = calculate_B1(Pu, Pe1x, Cm_x) if Mux > 0 else 1.0
        B1y = calculate_B1(Pu, Pe1y, Cm_y) if Muy > 0 else 1.0
        
        # 6. Calculate required strengths (assuming B2 = 1.0 for braced frame)
        B2 = 1.0  # Modify if analyzing unbraced frame
        Mr_x = B1x * Mux + B2 * 0  # No lateral translation moments for braced
        Mr_y = B1y * Muy + B2 * 0
        
        # 7. Check interaction equations
        interaction_ratio, passes, equation = beam_column_interaction_H1(
            Pu, Pc, Mr_x, Mr_y, Mcx, Mcy
        )
        
        # 8. Calculate individual ratios
        axial_ratio = Pu / Pc
        moment_ratio_x = Mr_x / Mcx if Mcx > 0 else 0
        moment_ratio_y = Mr_y / Mcy if Mcy > 0 else 0
        
        # Compile results
        results = {
            # Capacities
            'Pn': Pn,
            'Pc': Pc,
            'Mnx': Mnx,
            'Mcx': Mcx,
            'Mny': Mny,
            'Mcy': Mcy,
            
            # Demands
            'Pu': Pu,
            'Mux': Mux,
            'Muy': Muy,
            'Mr_x': Mr_x,
            'Mr_y': Mr_y,
            
            # Amplification factors
            'B1x': B1x,
            'B1y': B1y,
            'Cm_x': Cm_x,
            'Cm_y': Cm_y,
            
            # Elastic buckling
            'Pe1x': Pe1x,
            'Pe1y': Pe1y,
            
            # Ratios
            'axial_ratio': axial_ratio,
            'moment_ratio_x': moment_ratio_x,
            'moment_ratio_y': moment_ratio_y,
            'interaction_ratio': interaction_ratio,
            
            # Status
            'passes': passes,
            'equation_used': equation,
            'unity_check': interaction_ratio,
            
            # Additional info
            'lambda_x': comp_results['lambda_x'],
            'lambda_y': comp_results['lambda_y'],
            'Fcr': comp_results['Fcr'],
            'Fe': comp_results['Fe']
        }
        
        return results
        
    except Exception as e:
        st.error(f"Error in beam-column analysis: {e}")
        return None

def get_effective_length_factor(condition):
    """Get K factor based on end conditions"""
    K_factors = {
        "Fixed-Fixed": 0.5,
        "Fixed-Pinned": 0.7,
        "Fixed-Guided": 1.0,
        "Pinned-Pinned": 1.0,
        "Pinned-Guided": 2.0,
        "Guided-Guided": 1.0
    }
    return K_factors.get(condition, 1.0)

def create_interaction_diagram(df, df_mat, section, option_mat, Lbx=6.0, n_points=50):
    """Create P-M interaction diagram for beam-column"""
    try:
        # Get capacities
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        Ag = float(df.loc[section, 'A [cm2]'])
        Zx = float(df.loc[section, 'Zx [cm3]'])
        
        # Calculate key points
        Py = Fy * Ag / 1000  # Yield strength in compression (tons)
        Mp = Fy * Zx / 100000  # Plastic moment (t-m)
        
        # Get Pn for typical KL/r
        comp_results = calculate_Pn(df, df_mat, section, option_mat, 3.0, 3.0)  # Assume 3m effective length
        Pn = comp_results['Pn'] if comp_results else Py * 0.7
        
        # Generate points for interaction curve
        P_values = []
        M_values = []
        
        for i in range(n_points + 1):
            p_ratio = i / n_points
            P = Pn * p_ratio
            
            # Calculate corresponding moment capacity
            if p_ratio >= 0.2:
                # H1-1a equation rearranged
                M_ratio = (9/8) * (1 - p_ratio)
            else:
                # H1-1b equation rearranged
                M_ratio = 1 - p_ratio/2
            
            M = Mp * M_ratio
            P_values.append(P)
            M_values.append(M)
        
        # Apply resistance factors
        phi_c = 0.9
        phi_b = 0.9
        P_design = [phi_c * p for p in P_values]
        M_design = [phi_b * m for m in M_values]
        
        return P_design, M_design, phi_c * Pn, phi_b * Mp
        
    except Exception as e:
        st.error(f"Error creating interaction diagram: {e}")
        return None, None, None, None

def plot_interaction_diagram(P_design, M_design, Pc_max, Mc_max, Pu=None, Mu=None):
    """Plot P-M interaction diagram"""
    fig = go.Figure()
    
    # Add interaction curve
    fig.add_trace(go.Scatter(
        x=M_design,
        y=P_design,
        mode='lines',
        name='Interaction Curve',
        line=dict(color='blue', width=3),
        fill='tozeroy',
        fillcolor='rgba(0,100,200,0.2)'
    ))
    
    # Add design point if provided
    if Pu is not None and Mu is not None:
        fig.add_trace(go.Scatter(
            x=[Mu],
            y=[Pu],
            mode='markers',
            name='Design Point',
            marker=dict(color='red', size=12, symbol='star')
        ))
        
        # Add safety check annotation
        inside = False
        for i in range(len(M_design)-1):
            if M_design[i] <= Mu <= M_design[i+1]:
                if Pu <= P_design[i] + (P_design[i+1]-P_design[i])*(Mu-M_design[i])/(M_design[i+1]-M_design[i]):
                    inside = True
                    break
        
        status_text = "✅ Safe" if inside else "❌ Unsafe"
        fig.add_annotation(
            x=Mu, y=Pu,
            text=status_text,
            showarrow=True,
            arrowhead=2,
            bgcolor="white",
            bordercolor="black"
        )
    
    # Add capacity points
    fig.add_trace(go.Scatter(
        x=[0, Mc_max],
        y=[Pc_max, 0],
        mode='markers',
        name='Capacity Points',
        marker=dict(color='green', size=10, symbol='diamond')
    ))
    
    fig.update_layout(
        title="P-M Interaction Diagram",
        xaxis_title="Moment, M (t·m)",
        yaxis_title="Axial Force, P (tons)",
        height=600,
        hovermode='closest',
        showlegend=True
    )
    
    fig.update_xaxes(range=[0, max(M_design)*1.1])
    fig.update_yaxes(range=[0, max(P_design)*1.1])
    
    return fig

def create_3d_interaction_surface(df, df_mat, section, option_mat, n_points=20):
    """Create 3D P-Mx-My interaction surface"""
    try:
        # Get material and section properties
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        Ag = float(df.loc[section, 'A [cm2]'])
        Zx = float(df.loc[section, 'Zx [cm3]'])
        Zy = float(df.loc[section, 'Zy [cm3]'])
        
        # Key capacities
        Py = Fy * Ag / 1000  # tons
        Mpx = Fy * Zx / 100000  # t-m
        Mpy = Fy * Zy / 100000  # t-m
        
        # Assume typical compression capacity
        Pn = Py * 0.7  # Simplified
        phi = 0.9
        
        # Create mesh grid
        p_ratios = np.linspace(0, 1, n_points)
        theta = np.linspace(0, 2*np.pi, n_points*2)
        
        P_surf = []
        Mx_surf = []
        My_surf = []
        
        for p_ratio in p_ratios:
            P = phi * Pn * p_ratio
            
            for t in theta:
                if p_ratio >= 0.2:
                    m_total = (9/8) * (1 - p_ratio)
                else:
                    m_total = 1 - p_ratio/2
                
                Mx = phi * Mpx * m_total * np.cos(t)
                My = phi * Mpy * m_total * np.sin(t)
                
                P_surf.append(P)
                Mx_surf.append(Mx)
                My_surf.append(My)
        
        return P_surf, Mx_surf, My_surf
        
    except Exception as e:
        st.error(f"Error creating 3D surface: {e}")
        return None, None, None

# ==================== PLOTTING FUNCTIONS ====================
def create_multi_section_comparison_plot(df, df_mat, selected_sections, option_mat, section_lb_values, use_global_lb=False, global_lb=6.0, show_lp_lr_sections=None):
    """Create multi-section comparison plot"""
    try:
        fig = go.Figure()
        colors = px.colors.qualitative.Set3
        legend_info = []
        
        if show_lp_lr_sections is None:
            show_lp_lr_sections = selected_sections
        
        for i, section in enumerate(selected_sections):
            try:
                if section not in df.index:
                    continue
                
                Lr_max = df.loc[section, 'Lr [cm]'] / 100
                Lr_max = max(15, Lr_max + 5)
                
                lb_range = np.linspace(0.1, Lr_max, 100)
                mn_values = []
                
                for lb in lb_range:
                    try:
                        Mn, _, Lp, Lr, Mp, _, _, _ = F2(df, df_mat, section, option_mat, lb)
                        mn_values.append(Mn if Mn is not None else 0)
                    except:
                        mn_values.append(0)
                
                color = colors[i % len(colors)]
                fig.add_trace(go.Scatter(
                    x=lb_range,
                    y=mn_values,
                    mode='lines',
                    name=f'{section} - Capacity Curve',
                    line=dict(color=color, width=2),
                    hovertemplate=f'<b>{section}</b><br>' +
                                'Lb: %{x:.2f} m<br>' +  
                                'Mn: %{y:.2f} t⋅m<extra></extra>'
                ))
                
                current_lb = global_lb if use_global_lb else section_lb_values.get(section, 6.0)
                current_mn, _, current_lp, current_lr, current_mp, _, _, current_case = F2(df, df_mat, section, option_mat, current_lb)
                
                fig.add_trace(go.Scatter(
                    x=[current_lb],
                    y=[current_mn],
                    mode='markers',
                    name=f'{section} - Current Point',
                    marker=dict(
                        color=color,
                        size=12,
                        symbol='diamond',
                        line=dict(color='black', width=1)
                    ),
                    hovertemplate=f'<b>{section} - Current Design</b><br>' +
                                f'Lb: {current_lb:.2f} m<br>' +
                                f'Mn: {current_mn:.2f} t⋅m<br>' +
                                f'Mp: {current_mp:.2f} t⋅m<br>' +
                                f'Lp: {current_lp:.2f} m<br>' +
                                f'Lr: {current_lr:.2f} m<br>' +
                                f'Case: {current_case}<extra></extra>'
                ))
                
                if section in show_lp_lr_sections:
                    fig.add_vline(
                        x=current_lp,
                        line=dict(color=color, dash="dot", width=1.5),
                        annotation=dict(
                            text=f"Lp-{section}<br>{current_lp:.1f}m",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=1,
                            arrowcolor=color,
                            bgcolor="rgba(255,255,255,0.9)",
                            bordercolor=color,
                            font=dict(size=10),
                            xanchor="left" if i % 2 == 0 else "right"
                        )
                    )
                    
                    fig.add_vline(
                        x=current_lr,
                        line=dict(color=color, dash="dashdot", width=1.5),
                        annotation=dict(
                            text=f"Lr-{section}<br>{current_lr:.1f}m",
                            showarrow=True,
                            arrowhead=2,
                            arrowsize=1,
                            arrowwidth=1,
                            arrowcolor=color,
                            bgcolor="rgba(255,255,255,0.9)",
                            bordercolor=color,
                            font=dict(size=10),
                            xanchor="right" if i % 2 == 0 else "left"
                        )
                    )
                
                legend_info.append({
                    'section': section,
                    'current_lb': current_lb,
                    'current_mn': current_mn,
                    'mp': current_mp,
                    'lp': current_lp,
                    'lr': current_lr,
                    'efficiency': (0.9 * current_mn) / safe_get_weight(df, section) if safe_get_weight(df, section) > 0 else 0
                })
                
            except Exception as e:
                st.warning(f"⚠️ Error processing section {section}: {e}")
                continue
        
        fig.update_layout(
            title="🔧 Multi-Section Moment Capacity Comparison",
            xaxis_title="Unbraced Length, Lb (m)",
            yaxis_title="Moment Capacity, Mn (t⋅m)",
            height=600,
            hovermode='closest',
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.01
            ),
            showlegend=True
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig, legend_info
        
    except Exception as e:
        st.error(f"Error creating multi-section comparison plot: {e}")
        return None, []

def create_multi_section_efficiency_plot(df, df_mat, selected_sections, option_mat, section_lb_values, use_global_lb=False, global_lb=6.0):
    """Create multi-section efficiency plot"""
    try:
        sections_data = []
        
        for section in selected_sections:
            try:
                if section not in df.index:
                    continue
                
                current_lb = global_lb if use_global_lb else section_lb_values.get(section, 6.0)
                Mn, _, Lp, Lr, Mp, _, _, Case = F2(df, df_mat, section, option_mat, current_lb)
                
                Fib = 0.9
                FibMn = Fib * Mn
                weight = safe_get_weight(df, section)
                efficiency = FibMn / weight if weight > 0 else 0
                capacity_ratio = Mn / Mp if Mp > 0 else 0
                
                sections_data.append({
                    'Section': section,
                    'φMn': FibMn,
                    'Weight': weight,
                    'Efficiency': efficiency,
                    'Capacity_Ratio': capacity_ratio,
                    'Lb': current_lb,
                    'Case': Case
                })
                
            except Exception as e:
                continue
        
        if not sections_data:
            return None
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Design Moment Capacity', 'Unit Weight', 
                          'Efficiency Ratio', 'Capacity Utilization'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        sections = [d['Section'] for d in sections_data]
        colors = px.colors.qualitative.Set3[:len(sections)]
        
        fig.add_trace(
            go.Bar(
                x=sections,
                y=[d['φMn'] for d in sections_data],
                name='φMn',
                marker_color=colors,
                text=[f'{d["φMn"]:.2f}' for d in sections_data],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=sections,
                y=[d['Weight'] for d in sections_data],
                name='Weight',
                marker_color=colors,
                text=[f'{d["Weight"]:.1f}' for d in sections_data],
                textposition='auto'
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=sections,
                y=[d['Efficiency'] for d in sections_data],
                name='Efficiency',
                marker_color=colors,
                text=[f'{d["Efficiency"]:.3f}' for d in sections_data],
                textposition='auto'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=sections,
                y=[d['Capacity_Ratio'] for d in sections_data],
                name='Mn/Mp Ratio',
                marker_color=colors,
                text=[f'{d["Capacity_Ratio"]:.2f}' for d in sections_data],
                textposition='auto'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=700,
            showlegend=False,
            title_text="📊 Multi-Section Performance Dashboard"
        )
        
        fig.update_yaxes(title_text="φMn (t⋅m)", row=1, col=1)
        fig.update_yaxes(title_text="Weight (kg/m)", row=1, col=2)
        fig.update_yaxes(title_text="Efficiency", row=2, col=1)
        fig.update_yaxes(title_text="Capacity Ratio", row=2, col=2)
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating efficiency plot: {e}")
        return None

# ==================== LOAD DATA ====================
df = pd.DataFrame()
df_mat = pd.DataFrame()
df_chf = pd.DataFrame()
section_list = []
section_list_mat = []

try:
    if check_url(file_path) and check_url(file_path_mat):
        df, df_mat, df_chf, success = load_data()
        if success and not df.empty and not df_mat.empty:
            section_list = list(df.index)
            section_list_mat = list(df_mat.index)
            st.success("✅ Files loaded successfully!")
        else:
            st.error("❌ Failed to load data files or files are empty.")
    else:
        st.error("❌ One or both files do not exist at the given URLs. Please check the URLs.")
except Exception as e:
    st.error(f"❌ Unexpected error during data loading: {e}")

# ==================== MAIN APPLICATION ====================
st.markdown('<h1 class="main-header">🏗️ Structural Steel Design Analysis</h1>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("## 🔧 Configuration Panel")
    
    option = section_list[0] if section_list else ""
    option_mat = section_list_mat[0] if section_list_mat else ""
    bending_axis = "Major axis bending"

    ChapterF_Strength = st.checkbox("🔍 Enable Chapter F Strength Analysis")
    if ChapterF_Strength:
        if section_list:
            option = st.selectbox("🔩 Choose Steel Section:", section_list, index=0 if option in section_list else 0)
            st.session_state.option = option
        if section_list_mat:
            option_mat = st.selectbox("⚙️ Choose Steel Grade:", section_list_mat, index=0 if option_mat in section_list_mat else 0)
            st.session_state.option_mat = option_mat
        bending_axis = st.selectbox("📐 Select Bending Axis:", ["Major axis bending", "Minor axis bending"], index=0)

    st.divider()
    
    st.markdown("### 📊 Input Method")
    col1, col2 = st.columns(2)
    if col1.button("🎚️ Slider", use_container_width=True):
        st.session_state.input_mode = "slider"
    if col2.button("🔢 Number", use_container_width=True):
        st.session_state.input_mode = "number"

    Mu = 100
    Vu = 100
    ChapterF_Design = st.checkbox("📋 Enable Chapter F Design Analysis")
    if ChapterF_Design:
        Mu = st.number_input("⚡ Ultimate Bending Moment (kN·m):", value=100.0)
        Vu = st.number_input("⚡ Ultimate Shear Force (kN):", value=100.0)

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Steel Catalogue", "🔧 Chapter F Analysis", "📋 Section Selection", "📈 Comparative Analysis", "🏗️ Beam-Column"])

# ==================== TAB 1: STEEL CATALOGUE ====================
with tab1:
    st.markdown('<h2 class="sub-header">Steel Section Database</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if option and not df.empty and option in df.index:
            st.markdown("### 📋 Section Properties")
            section_data = df.loc[option].to_frame().reset_index()
            section_data.columns = ['Property', 'Value']
            st.dataframe(section_data, use_container_width=True, height=400)
        else:
            st.warning("⚠️ No section selected or database is empty.")

    with col2:
        st.markdown("### 🏗️ Section Visualization")
        if option and option in df.index:
            try:
                bf = float(df.loc[option, 'bf [mm]'])
                d = float(df.loc[option, 'd [mm]'])
                tw = float(df.loc[option, 'tw [mm]'])
                tf = float(df.loc[option, 'tf [mm]'])

                fig, ax = plt.subplots(figsize=(6, 6))
                fig.patch.set_facecolor('white')
                ax.set_facecolor('white')

                flange_top = patches.Rectangle((-bf/2, d/2 - tf), bf, tf, 
                                             linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)
                flange_bottom = patches.Rectangle((-bf/2, -d/2), bf, tf, 
                                                linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)
                web = patches.Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf, 
                                      linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)

                ax.add_patch(flange_top)
                ax.add_patch(flange_bottom)
                ax.add_patch(web)

                ax.axhline(y=0, color='red', linewidth=2, linestyle='--', alpha=0.8, label='Centroid')
                ax.axvline(x=0, color='red', linewidth=2, linestyle='--', alpha=0.8)

                ax.set_xlim([-bf/2 - 20, bf/2 + 20])
                ax.set_ylim([-d/2 - 20, d/2 + 20])
                ax.set_aspect('equal')
                ax.set_title(f"H-Section: {option}", fontsize=14, fontweight='bold')
                ax.set_xlabel("Width [mm]", fontsize=12)
                ax.set_ylabel("Height [mm]", fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend()

                st.pyplot(fig)
            except Exception as e:
                st.error(f"Error creating visualization: {e}")
        else:
            st.warning("⚠️ Please select a valid section!")

    with col3:
        st.markdown("### 🔍 Classification Results")
        if option and option_mat and not df.empty and not df_mat.empty:
            try:
                lamf, lamw, lamf_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression = compression_classify(df, df_mat, option, option_mat)
                lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural = Flexural_classify(df, df_mat, option, option_mat)

                classification_data = {
                    "Element": ["Flange (Compression)", "Web (Compression)", "Flange (Flexural)", "Web (Flexural)"],
                    "Classification": [Classify_flange_Compression, Classify_Web_Compression, 
                                     Classify_flange_Flexural, Classify_Web_Flexural],
                    "λ": [f"{lamf:.2f}", f"{lamw:.2f}", f"{lamf:.2f}", f"{lamw:.2f}"]
                }
                
                classification_df = pd.DataFrame(classification_data)
                
                def color_classification(val):
                    if "Compact" in val:
                        return 'background-color: #d4edda'
                    elif "Non-Compact" in val:
                        return 'background-color: #fff3cd'
                    else:
                        return 'background-color: #f8d7da'

                styled_df = classification_df.style.applymap(color_classification, subset=['Classification'])
                st.dataframe(styled_df, use_container_width=True)

                result = classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis)
                st.markdown(f"**🎯 Design Code Section:** {result}")

            except Exception as e:
                st.error(f"❌ Error in classification: {e}")

# ==================== TAB 2: CHAPTER F ANALYSIS ====================
with tab2:
    st.markdown('<h2 class="sub-header">Chapter F: Flexural Design Analysis</h2>', unsafe_allow_html=True)
    
    if option and option_mat and not df.empty and not df_mat.empty:
        try:
            lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural = Flexural_classify(df, df_mat, option, option_mat)
            result = classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis)
            
            st.markdown(f"**📋 Analysis Method:** {result}")
            
            Lr_max = df.loc[option, 'Lr [cm]']/100
            Lr_max = mt.ceil(Lr_max)

            col_input1, col_input2 = st.columns(2)
            with col_input1:
                if st.session_state.input_mode == "slider":
                    Lb = st.slider("📏 Unbraced Length (Lb) [m]", 0.0, float(Lr_max+10), 6.0, 0.5)
                else:
                    Lb = st.number_input("📏 Unbraced Length (Lb) [m]", value=6.0, step=0.5)
            
            with col_input2:
                st.metric("Current Lb", f"{Lb} m")

            if "F2:" in result:
                col_result, col_plot = st.columns([1, 2])
                
                with col_result:
                    Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, option, option_mat, Lb)
                    
                    Fib = 0.9
                    FibMn = Fib * Mn
                    FibMp = Fib * Mp

                    st.markdown("### 📊 Analysis Results")
                    results_data = {
                        "Parameter": ["Mp (Plastic Moment)", "Mn (Nominal Moment)", "φMn (Design Moment)", 
                                    "Lp (Limiting Length)", "Lr (Limiting Length)", "Case"],
                        "Value": [f"{Mp:.2f} t⋅m", f"{Mn:.2f} t⋅m", f"{FibMn:.2f} t⋅m", 
                                f"{Lp:.2f} m", f"{Lr:.2f} m", Case],
                        "Status": ["Plastic Capacity", "Nominal Capacity", "Design Capacity",
                                 "Compact Limit", "LTB Limit", "Governing"]
                    }
                    
                    results_df = pd.DataFrame(results_data)
                    st.dataframe(results_df, use_container_width=True)
                    
                    if Mn >= Mp * 0.9:
                        st.success("✅ Close to plastic capacity")
                    elif Mn >= Mp * 0.7:
                        st.warning("⚠️ Moderate capacity reduction")
                    else:
                        st.error("❌ Significant capacity reduction")

                with col_plot:
                    try:
                        Mni_flat = Mni[:3] + (Mni[3] if len(Mni) > 3 else [])
                        Lni_flat = Lni[:3] + (Lni[3] if len(Lni) > 3 else [])

                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=Mni_flat,
                            mode='lines+markers',
                            name='Nominal Moment Capacity',
                            line=dict(color='blue', width=3),
                            marker=dict(size=6)
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=[Lb], y=[Mn],
                            mode='markers',
                            name=f'Current Design Point (Lb={Lb}m)',
                            marker=dict(color='red', size=12, symbol='diamond')
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=[FibMn] * len(Lni_flat),
                            mode='lines',
                            name='φMn (Design Capacity)',
                            line=dict(color='green', width=2, dash='dash')
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=[Mp] * len(Lni_flat),
                            mode='lines',
                            name='Mp (Plastic Capacity)',
                            line=dict(color='orange', width=2, dash='dot')
                        ))
                        
                        fig.add_vline(x=Lp, line=dict(color="purple", dash="dash"), 
                                    annotation_text="Lp", annotation_position="top")
                        fig.add_vline(x=Lr, line=dict(color="brown", dash="dash"), 
                                    annotation_text="Lr", annotation_position="top")
                        
                        fig.update_layout(
                            title=f"Moment Capacity vs Unbraced Length - {option}",
                            xaxis_title="Unbraced Length, Lb (m)",
                            yaxis_title="Moment Capacity (t⋅m)",
                            height=500,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    except Exception as e:
                        st.error(f"Error in plotting: {e}")

        except Exception as e:
            st.error(f"❌ Error in analysis: {e}")
    else:
        st.warning("⚠️ Please select section and material in the sidebar.")

# ==================== TAB 3: SECTION SELECTION ====================
with tab3:
    st.markdown('<h2 class="sub-header">Steel Section Selection Tool</h2>', unsafe_allow_html=True)
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        zx_min = st.number_input("🔍 Min Zx [cm³]:", min_value=0, value=0, step=100)
    
    with col_filter2:
        depth_min = st.number_input("📏 Min Depth [mm]:", min_value=0, value=0, step=50)
    
    with col_filter3:
        weight_max = st.number_input("⚖️ Max Weight [kg/m]:", min_value=0, value=1000, step=10)

    if not df.empty:
        try:
            filtered_data = df.copy()
            filtered_data = filtered_data[filtered_data["Zx [cm3]"] >= zx_min]
            if depth_min > 0:
                filtered_data = filtered_data[filtered_data["d [mm]"] >= depth_min]
            if weight_max < 1000:
                weight_col = None
                for col in ['Unit Weight [kg/m]', 'w [kg/m]', 'Weight [kg/m]']:
                    if col in filtered_data.columns:
                        weight_col = col
                        break
                
                if weight_col:
                    filtered_data = filtered_data[filtered_data[weight_col] <= weight_max]

            filtered_data_display = filtered_data.reset_index()
            
            st.markdown(f"**📋 Filtered Results: {len(filtered_data_display)} sections**")

            gb = GridOptionsBuilder.from_dataframe(filtered_data_display)
            gb.configure_selection("multiple", use_checkbox=True, groupSelectsChildren=False)
            gb.configure_grid_options(enableCellTextSelection=True)
            gb.configure_column("Section", headerCheckboxSelection=True)
            grid_options = gb.build()

            try:
                grid_response = AgGrid(
                    filtered_data_display,
                    gridOptions=grid_options,
                    height=400,
                    width="100%",
                    theme="streamlit",
                    allow_unsafe_jscode=True,
                    update_mode='SELECTION_CHANGED'
                )
                
                selected_rows = grid_response.get("selected_rows", [])
                
                if selected_rows is not None and len(selected_rows) > 0:
                    df_selected = pd.DataFrame(selected_rows)
                    
                    if 'Section' in df_selected.columns:
                        st.session_state.selected_sections = df_selected.to_dict('records')
                        st.success(f"✅ Selected {len(selected_rows)} sections for analysis")
                        
                        with st.expander("📋 Selected Sections Summary", expanded=True):
                            summary_cols = ['Section', 'Zx [cm3]', 'Zy [cm3]', 'd [mm]', 'bf [mm]', 
                                          'tf [mm]', 'tw [mm]', 'Unit Weight [kg/m]', 'Sx [cm3]', 
                                          'Sy [cm3]', 'Ix [cm4]', 'Iy [cm4]']
                            available_cols = [col for col in summary_cols if col in df_selected.columns]
                            
                            if available_cols:
                                st.dataframe(df_selected[available_cols], use_container_width=True)
                                
                                st.markdown("### 📏 Individual Unbraced Length Settings")
                                
                                if 'section_lb_values' not in st.session_state:
                                    st.session_state.section_lb_values = {}
                                
                                for idx, row in df_selected.iterrows():
                                    section_name = row['Section']
                                    col_lb1, col_lb2 = st.columns([2, 1])
                                    
                                    with col_lb1:
                                        lb_value = st.number_input(
                                            f"📏 Lb for {section_name} [m]:", 
                                            min_value=0.0, 
                                            value=st.session_state.section_lb_values.get(section_name, 6.0),
                                            step=0.5,
                                            key=f"lb_{section_name}"
                                        )
                                        st.session_state.section_lb_values[section_name] = lb_value
                                    
                                    with col_lb2:
                                        st.metric(f"Current Lb", f"{lb_value} m")
                            else:
                                st.warning("⚠️ Summary data not available")
                    else:
                        st.error("❌ Selected data does not contain 'Section' column")
                else:
                    st.info("ℹ️ Please select sections for comparative analysis")
                    
            except Exception as e:
                st.error(f"Error displaying grid: {e}")
        except Exception as e:
            st.error(f"Error in filtering data: {e}")
    else:
        st.error("❌ No data available")

# ==================== TAB 4: COMPARATIVE ANALYSIS ====================
with tab4:
    st.markdown('<h2 class="sub-header">Comparative Analysis Dashboard</h2>', unsafe_allow_html=True)

    has_selected_sections = 'selected_sections' in st.session_state and st.session_state.selected_sections
    if has_selected_sections:
        df_selected = pd.DataFrame(st.session_state.selected_sections)
        df = standardize_column_names(df)

        col_input1, col_input2, col_input3 = st.columns(3)
        with col_input1:
            use_global_lb = st.checkbox("🌐 Use Global Lb for all sections", value=False)
            if use_global_lb:
                if st.session_state.input_mode == "slider":
                    global_lb = st.slider("📏 Global Unbraced Length [m]", 0.0, 20.0, 6.0, 0.5)
                else:
                    global_lb = st.number_input("📏 Global Unbraced Length [m]", value=6.0, step=0.5)
        with col_input2:
            analysis_type = st.selectbox("🔍 Analysis Type",
                ["Moment Capacity", "Weight Comparison", "Efficiency Ratio",
                "Detailed Comparison", "Multi-Section Moment Curve", "Multi-Section Dashboard"])
        with col_input3:
            show_details = st.checkbox("📊 Show Detailed Results", value=True)

        if 'Section' in df_selected.columns and len(df_selected) > 0:
            section_names = df_selected['Section'].unique()

            comparison_results = []
            plot_data = {'sections': [], 'Mp': [], 'Mn': [], 'phi_Mn': [], 'weight': [], 
                        'efficiency': [], 'lb_used': []}
            
            for section in section_names:
                try:
                    if section not in df.index:
                        st.warning(f"⚠️ Section {section} not found in database")
                        continue
                    
                    if use_global_lb:
                        lb_to_use = global_lb
                    else:
                        lb_to_use = st.session_state.section_lb_values.get(section, 6.0)
                    
                    Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, section, option_mat, lb_to_use)
                    
                    Fib = 0.9
                    FibMn = Fib * Mn
                    
                    weight = safe_get_weight(df, section)
                    efficiency = FibMn / weight if weight > 0 else 0
                    
                    comparison_results.append({
                        'Section': section,
                        'Lb Used (m)': lb_to_use,
                        'Mp (t⋅m)': Mp if Mp is not None else 0,
                        'Mn (t⋅m)': Mn if Mn is not None else 0,
                        'φMn (t⋅m)': FibMn if FibMn is not None else 0,
                        'Weight (kg/m)': weight,
                        'Efficiency': efficiency,
                        'Lp (m)': Lp if Lp is not None else 0,
                        'Lr (m)': Lr if Lr is not None else 0,
                        'Case': Case if Case is not None else 'Unknown',
                        'Capacity Ratio': (Mn/Mp if Mp is not None and Mp > 0 and Mn is not None else 0)
                    })
                    
                    plot_data['sections'].append(section)
                    plot_data['Mp'].append(Mp if Mp is not None else 0)
                    plot_data['Mn'].append(Mn if Mn is not None else 0)
                    plot_data['phi_Mn'].append(FibMn if FibMn is not None else 0)
                    plot_data['weight'].append(weight)
                    plot_data['efficiency'].append(efficiency)
                    plot_data['lb_used'].append(lb_to_use)
                    
                except Exception as e:
                    st.error(f"❌ Error analyzing section {section}: {e}")
                    continue

            if analysis_type == "Multi-Section Moment Curve":
                st.markdown("#### 🔧 Multi-Section Moment Capacity vs Unbraced Length")
                col_curve1, col_curve2 = st.columns([2, 1])
                with col_curve1:
                    st.markdown("##### 📊 Graph Controls")
                    show_lp_lr_sections = st.multiselect(
                        "🔍 Select sections to show Lp/Lr lines:",
                        options=list(section_names),
                        default=list(section_names),
                        help="Select sections to show critical length lines in graph"
                    )
                with col_curve2:
                    st.markdown("##### ℹ️ Legend")
                    st.write("- **Solid**: Mn vs Lb")
                    st.write("- **Diamond**: Current design point")
                    st.write("- **Dot**: Lp")
                    st.write("- **Dash-dot**: Lr")
                    if show_lp_lr_sections:
                        st.success(f"✅ Showing Lp/Lr for {len(show_lp_lr_sections)} section(s)")
                    else:
                        st.warning("⚠️ No Lp/Lr lines selected")

                fig, legend_info = create_multi_section_comparison_plot(
                    df, df_mat, section_names, option_mat,
                    st.session_state.section_lb_values, use_global_lb,
                    global_lb if use_global_lb else None,
                    show_lp_lr_sections=show_lp_lr_sections
                )
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)

            elif analysis_type == "Multi-Section Dashboard":
                st.markdown("#### 📊 Multi-Section Performance Dashboard")
                
                fig = create_multi_section_efficiency_plot(
                    df, df_mat, section_names, option_mat,
                    st.session_state.section_lb_values, use_global_lb,
                    global_lb if use_global_lb else None
                )
                
                if fig is not None:
                    st.plotly_chart(fig, use_container_width=True)

            elif analysis_type == "Moment Capacity":
                try:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=plot_data['sections'],
                        y=plot_data['phi_Mn'],
                        name='φMn',
                        marker_color='lightblue',
                        text=[f'{v:.2f}' for v in plot_data['phi_Mn']],
                        textposition='auto'
                    ))
                    fig.update_layout(
                        title="Design Moment Capacity Comparison",
                        xaxis_title="Steel Sections",
                        yaxis_title="φMn (t⋅m)",
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating moment capacity chart: {e}")

        else:
            st.error("❌ Selected data does not contain 'Section' column or no sections available")
    else:
        st.info("ℹ️ Please select sections in the 'Section Selection' tab first")

# ==================== TAB 5: BEAM-COLUMN ANALYSIS ====================
with tab5:
    st.markdown('<h2 class="sub-header">Beam-Column Interaction Analysis (Combined Loading)</h2>', unsafe_allow_html=True)
    
    if not df.empty and not df_mat.empty and option and option_mat:
        
        col_input, col_results = st.columns([1, 2])
        
        with col_input:
            st.markdown("### 📝 Design Parameters")
            
            st.info(f"**Selected Section:** {option}")
            st.info(f"**Material Grade:** {option_mat}")
            
            load_case = st.selectbox(
                "Load Case Type",
                ["Custom Input", "Gravity Only", "Gravity + Wind", "Gravity + Seismic"],
                help="Select predefined load case or custom input"
            )
            
            st.markdown("#### 🔧 Applied Loads")
            
            if load_case == "Custom Input":
                Pu = st.number_input("**Axial Load, Pu** (tons)", 
                                    min_value=0.0, value=50.0, step=5.0,
                                    help="Ultimate axial compression load")
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    Mux = st.number_input("**Mux** (t·m)", 
                                        min_value=0.0, value=30.0, step=5.0,
                                        help="Ultimate moment about major axis")
                with col_m2:
                    Muy = st.number_input("**Muy** (t·m)", 
                                        min_value=0.0, value=5.0, step=1.0,
                                        help="Ultimate moment about minor axis")
            else:
                st.warning("🚧 Predefined load cases coming soon")
                Pu = 50.0
                Mux = 30.0
                Muy = 5.0
            
            st.markdown("#### 📏 Effective Lengths")
            
            end_condition_x = st.selectbox(
                "End Condition (Major Axis)",
                ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned", "Fixed-Guided"],
                index=0
            )
            
            end_condition_y = st.selectbox(
                "End Condition (Minor Axis)",
                ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned", "Fixed-Guided"],
                index=0
            )
            
            Kx = get_effective_length_factor(end_condition_x)
            Ky = get_effective_length_factor(end_condition_y)
            
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                Lx = st.number_input("**Lx** (m)", min_value=0.1, value=3.0, step=0.5,
                                   help="Unbraced length about X-axis")
                st.caption(f"K = {Kx:.2f}")
                KLx = Kx * Lx
                st.metric("KLx", f"{KLx:.2f} m")
                
            with col_l2:
                Ly = st.number_input("**Ly** (m)", min_value=0.1, value=3.0, step=0.5,
                                   help="Unbraced length about Y-axis")
                st.caption(f"K = {Ky:.2f}")
                KLy = Ky * Ly
                st.metric("KLy", f"{KLy:.2f} m")
            
            Lbx = st.number_input("**Lateral Unbraced Length, Lb** (m)", 
                                min_value=0.1, value=3.0, step=0.5,
                                help="Unbraced length for lateral-torsional buckling")
            
            with st.expander("⚙️ Advanced Options", expanded=False):
                st.markdown("#### Moment Modification Factors")
                col_cm1, col_cm2 = st.columns(2)
                with col_cm1:
                    Cm_x = st.number_input("Cm,x", min_value=0.4, max_value=1.0, 
                                         value=0.85, step=0.05,
                                         help="Moment modification factor for X-axis")
                with col_cm2:
                    Cm_y = st.number_input("Cm,y", min_value=0.4, max_value=1.0, 
                                         value=0.85, step=0.05,
                                         help="Moment modification factor for Y-axis")
                
                frame_type = st.radio("Frame Type", 
                                     ["Braced Frame (B2=1.0)", "Unbraced Frame"],
                                     help="Select frame bracing condition")
                
                analysis_method = st.selectbox("Analysis Method",
                                              ["AISC 360-16 (H1)", "Simplified", "Advanced"],
                                              help="Select analysis method")
            
            st.markdown("---")
            analyze_btn = st.button("🔍 **Analyze Beam-Column**", 
                                   type="primary", 
                                   use_container_width=True)
        
        with col_results:
            if analyze_btn:
                with st.spinner("Analyzing beam-column interaction..."):
                    try:
                        results = analyze_beam_column(
                            df, df_mat, option, option_mat,
                            Pu, Mux, Muy, KLx, KLy, Lbx, Cm_x, Cm_y
                        )
                        
                        if results:
                            if results['passes']:
                                st.markdown("""
                                <div class="success-card">
                                    <h3>✅ Design PASSES</h3>
                                    <h4>Unity Check: {:.3f} < 1.0</h4>
                                    <p>Safety Margin: {:.1f}%</p>
                                </div>
                                """.format(results['unity_check'], 
                                         (1-results['unity_check'])*100), 
                                unsafe_allow_html=True)
                            else:
                                st.markdown("""
                                <div class="warning-card">
                                    <h3>❌ Design FAILS</h3>
                                    <h4>Unity Check: {:.3f} > 1.0</h4>
                                    <p>Overstressed by: {:.1f}%</p>
                                </div>
                                """.format(results['unity_check'],
                                         (results['unity_check']-1)*100), 
                                unsafe_allow_html=True)
                            
                            st.markdown("### 📊 Load Utilization Ratios")
                            col_r1, col_r2, col_r3 = st.columns(3)
                            
                            with col_r1:
                                axial_color = "normal" if results['axial_ratio'] < 0.95 else "inverse"
                                st.metric("**Axial**", 
                                        f"{results['axial_ratio']:.3f}",
                                        delta=f"{results['Pu']:.1f}/{results['Pc']:.1f} tons",
                                        delta_color=axial_color)
                                st.progress(min(results['axial_ratio'], 1.0))
                            
                            with col_r2:
                                mx_color = "normal" if results['moment_ratio_x'] < 0.95 else "inverse"
                                st.metric("**Moment X**", 
                                        f"{results['moment_ratio_x']:.3f}",
                                        delta=f"{results['Mr_x']:.1f}/{results['Mcx']:.1f} t·m",
                                        delta_color=mx_color)
                                st.progress(min(results['moment_ratio_x'], 1.0))
                            
                            with col_r3:
                                my_color = "normal" if results['moment_ratio_y'] < 0.95 else "inverse"
                                st.metric("**Moment Y**", 
                                        f"{results['moment_ratio_y']:.3f}",
                                        delta=f"{results['Mr_y']:.1f}/{results['Mcy']:.1f} t·m",
                                        delta_color=my_color)
                                st.progress(min(results['moment_ratio_y'], 1.0))
                            
                            st.markdown("### 📈 P-M Interaction Diagram")
                            
                            P_design, M_design, Pc_max, Mc_max = create_interaction_diagram(
                                df, df_mat, option, option_mat, Lbx
                            )
                            
                            if P_design and M_design:
                                fig = plot_interaction_diagram(
                                    P_design, M_design, Pc_max, Mc_max, Pu, Mux
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with st.expander("📋 Detailed Analysis Results", expanded=True):
                                st.markdown("#### Member Capacities")
                                capacity_data = {
                                    "Property": ["Pn", "φPn", "Mnx", "φMnx", "Mny", "φMny"],
                                    "Value": [
                                        f"{results['Pn']:.2f} tons",
                                        f"{results['Pc']:.2f} tons",
                                        f"{results['Mnx']:.2f} t·m",
                                        f"{results['Mcx']:.2f} t·m",
                                        f"{results['Mny']:.2f} t·m",
                                        f"{results['Mcy']:.2f} t·m"
                                    ],
                                    "Description": [
                                        "Nominal compression capacity",
                                        "Design compression capacity",
                                        "Nominal moment capacity (X)",
                                        "Design moment capacity (X)",
                                        "Nominal moment capacity (Y)",
                                        "Design moment capacity (Y)"
                                    ]
                                }
                                capacity_df = pd.DataFrame(capacity_data)
                                st.dataframe(capacity_df, use_container_width=True, hide_index=True)
                                
                                st.markdown("#### Stability Parameters")
                                stability_data = {
                                    "Parameter": ["λx", "λy", "Fe", "Fcr", "B1x", "B1y"],
                                    "Value": [
                                        f"{results['lambda_x']:.1f}",
                                        f"{results['lambda_y']:.1f}",
                                        f"{results['Fe']:.1f} ksc",
                                        f"{results['Fcr']:.1f} ksc",
                                        f"{results['B1x']:.3f}",
                                        f"{results['B1y']:.3f}"
                                    ]
                                }
                                stability_df = pd.DataFrame(stability_data)
                                st.dataframe(stability_df, use_container_width=True, hide_index=True)
                                
                                st.markdown("#### Interaction Equation Check")
                                st.info(f"**Equation Used:** {results['equation_used']}")
                                
                                if results['equation_used'] == "H1-1a":
                                    eq_text = f"""
Pr/Pc + (8/9)(Mrx/Mcx + Mry/Mcy) ≤ 1.0

{results['axial_ratio']:.3f} + (8/9)({results['moment_ratio_x']:.3f} + {results['moment_ratio_y']:.3f}) = {results['unity_check']:.3f}
                                    """
                                else:
                                    eq_text = f"""
Pr/(2Pc) + (Mrx/Mcx + Mry/Mcy) ≤ 1.0

{results['axial_ratio']:.3f}/2 + ({results['moment_ratio_x']:.3f} + {results['moment_ratio_y']:.3f}) = {results['unity_check']:.3f}
                                    """
                                st.code(eq_text, language='text')
                        
                    except Exception as e:
                        st.error(f"❌ Analysis Error: {str(e)}")
                        st.exception(e)
            else:
                st.info("""
                ### 📖 How to Use Beam-Column Analysis
                
                1. **Select Section and Material** in the sidebar
                2. **Input Applied Loads** (Pu, Mux, Muy)
                3. **Specify Effective Lengths** based on end conditions
                4. **Adjust Advanced Options** if needed
                5. **Click Analyze** to perform interaction check
                
                The analysis follows **AISC 360-16 Chapter H** provisions for combined loading.
                """)
                
                example_P = np.linspace(0, 100, 50)
                example_M = 50 * np.sqrt(1 - (example_P/100)**2)
                
                fig_example = go.Figure()
                fig_example.add_trace(go.Scatter(
                    x=example_M, y=example_P,
                    mode='lines',
                    fill='tozeroy',
                    name='Interaction Curve'
                ))
                fig_example.update_layout(
                    title="Typical P-M Interaction Diagram",
                    xaxis_title="Moment, M (t·m)",
                    yaxis_title="Axial Force, P (tons)",
                    height=400
                )
                st.plotly_chart(fig_example, use_container_width=True)
    
    else:
        st.warning("⚠️ Please select a section and material grade in the sidebar configuration panel first.")
