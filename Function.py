# ==================== ENHANCED STEEL DESIGN ANALYSIS APPLICATION ====================
# Version: 5.0 - Based on working v3.1 with enhanced F2 calculations
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
    page_title="Steel Design Analysis | AISC 360",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    /* Clean, modern design with better readability */
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

# ==================== CORRECT F2 FUNCTION FROM ORIGINAL ====================
def F2(df, df_mat, option, option_mat, Lb):
    """F2 Analysis for doubly symmetric compact I-shaped members - Corrected Version"""
    try:
        Cb = 1
        section = option
        Lb = Lb * 100  # Convert Lb from m to cm
        
        # Get section properties
        Lp = float(df.loc[section, "Lp [cm]"])
        Lr = float(df.loc[section, "Lr [cm]"])
        S_Major = float(df.loc[section, "Sx [cm3]"])
        Z_Major = float(df.loc[section, 'Zx [cm3]'])
        
        # Handle rts variations
        if 'rts [cm6]' in df.columns:
            rts = float(df.loc[section, 'rts [cm6]'])
        elif 'rts [cm]' in df.columns:
            rts = float(df.loc[section, 'rts [cm]'])
        else:
            ry = float(df.loc[section, 'ry [cm]'])
            rts = ry * 1.1  # Approximation
        
        j = float(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 1.0
        c = 1
        h0 = float(df.loc[section, 'ho [mm]']) / 10 if 'ho [mm]' in df.columns else float(df.loc[section, 'd [mm]']) / 10
        
        # Material properties
        Fy = float(df_mat.loc[option_mat, "Yield Point (ksc)"])
        E = float(df_mat.loc[option_mat, "E"])
        
        # Initialize arrays for plotting
        Mni = []
        Mnr = []
        Lni = []
        Lri_values = []
        
        # Calculate Mn based on Lb
        if Lb < Lp:
            Case = "F2.1 - Plastic Yielding"
            Mp = Fy * Z_Major 
            Mn = Mp / 100000
            Mn = np.floor(Mn * 100) / 100
            Mp = np.floor(Mp * 100) / 100
        elif Lp <= Lb < Lr:
            Case = "F2.2 - Inelastic LTB"
            Mp = Fy * Z_Major
            Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb - Lp) / (Lr - Lp))))
            Mn = Mn / 100000
            Mp = Mp / 100000
            Mn = min(Mp, Mn)
            Mn = np.floor(Mn * 100) / 100
            Mp = np.floor(Mp * 100) / 100
        else:
            Case = "F2.3 - Elastic LTB"
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
        
        # Build arrays for plotting
        Mni.append(Mp)
        Lni.append(0)
        
        Mni.append(Mp)
        Lni.append(np.floor((Lp / 100) * 100) / 100)
        
        Mni.append(Mn_F2C)
        Lni.append(np.floor((Lr / 100) * 100) / 100)
        
        # Elastic region calculations
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
        
        # Convert back to meters
        Lb = Lb / 100
        Lp = Lp / 100
        Lr = Lro / 100
        
        Lb = np.floor(Lb * 100) / 100
        Lp = np.floor(Lp * 100) / 100
        Lr = np.floor(Lr * 100) / 100
        
        return Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case
        
    except Exception as e:
        st.error(f"Error in F2 calculation: {str(e)}")
        return 0, 0, 0, 0, 0, [], [], "Error"

def calculate_required_properties(Mu, phi=0.9):
    """Calculate required section properties based on design moment"""
    Mu_tm = Mu / 9.81
    required_zx = {}
    steel_grades = {
        'SS400': 2400,
        'SM490': 3300,
        'SM520': 3600,
        'SM570': 4600
    }
    for grade, Fy in steel_grades.items():
        Zx_req = (Mu_tm * 100000) / (phi * Fy)
        required_zx[grade] = Zx_req
    return required_zx

def calculate_required_ix(w, L, delta_limit, E=2.04e6):
    """Calculate required Ix based on deflection limit"""
    w_kg = w * 1000 / 9.81
    L_cm = L * 100
    delta_max = L_cm / delta_limit
    Ix_req = (5 * w_kg * L_cm**4) / (384 * E * delta_max)
    return Ix_req

def calculate_service_load_capacity(df, df_mat, section, material, L, Lb):
    """Calculate service load capacity in kg/m"""
    try:
        Mn, _, _, _, _, _, _, _ = F2(df, df_mat, section, material, Lb)
        phi_Mn = 0.9 * Mn  # t·m
        phi_Mn_kg_cm = phi_Mn * 100000
        L_cm = L * 100
        w = (8 * phi_Mn_kg_cm) / (L_cm**2)  # kg/cm
        w_per_m = w * 100  # kg/m
        return w_per_m
    except:
        return 0

def compression_analysis_advanced(df, df_mat, section, material, KLx, KLy, Kz=None, Lz=None):
    """Advanced compression member analysis including flexural-torsional buckling"""
    try:
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        G = E / (2 * (1 + 0.3))
        
        Ag = float(df.loc[section, 'A [cm2]'])
        rx = float(df.loc[section, 'rx [cm]'])
        ry = float(df.loc[section, 'ry [cm]'])
        
        lambda_x = (KLx * 100) / rx
        lambda_y = (KLy * 100) / ry
        lambda_max = max(lambda_x, lambda_y)
        
        # 4.71√(E/Fy) for transition
        lambda_limit = 4.71 * mt.sqrt(E / Fy)
        
        Fe = (mt.pi**2 * E) / (lambda_max**2)
        
        if lambda_max <= lambda_limit:
            Fcr = Fy * (0.658**(Fy/Fe))
        else:
            Fcr = 0.877 * Fe
        
        Pn = Fcr * Ag / 1000
        phi_Pn = 0.9 * Pn
        
        return {
            'Pn': Pn,
            'phi_Pn': phi_Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_max': lambda_max,
            'lambda_limit': lambda_limit,
            'buckling_mode': 'Flexural'
        }
    except Exception as e:
        st.error(f"Error in compression analysis: {e}")
        return None

def visualize_column_2d_enhanced(df, section):
    """Enhanced 2D visualization showing both principal planes"""
    try:
        fig, axes = plt.subplots(1, 3, figsize=(15, 6))
        
        # Get dimensions
        d = float(df.loc[section, 'd [mm]'])
        bf = float(df.loc[section, 'bf [mm]'])
        tw = float(df.loc[section, 'tw [mm]'])
        tf = float(df.loc[section, 'tf [mm]'])
        
        # Strong axis view
        ax1 = axes[0]
        ax1.set_title('Strong Axis (X-X)', fontsize=14, fontweight='bold')
        column_height = 3000
        
        ax1.add_patch(Rectangle((-bf/2, 0), bf, column_height,
                                linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd'))
        
        y = np.linspace(0, column_height, 100)
        x = (bf/4) * np.sin(np.pi * y / column_height)
        ax1.plot(x, y, 'r--', lw=2, alpha=0.7, label='Buckled shape')
        
        ax1.arrow(0, column_height + 200, 0, -150, head_width=bf/3,
                 head_length=50, fc='red', ec='red')
        ax1.text(0, column_height + 300, 'P', ha='center', fontsize=14, fontweight='bold')
        
        ax1.set_xlim([-bf, bf])
        ax1.set_ylim([-100, column_height + 400])
        ax1.set_xlabel('Width (mm)')
        ax1.set_ylabel('Height (mm)')
        ax1.legend()
        
        # Weak axis view
        ax2 = axes[1]
        ax2.set_title('Weak Axis (Y-Y)', fontsize=14, fontweight='bold')
        
        ax2.add_patch(Rectangle((-d/2, 0), d, column_height,
                                linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd'))
        
        x2 = (d/4) * np.sin(np.pi * y / column_height)
        ax2.plot(x2, y, 'r--', lw=2, alpha=0.7, label='Buckled shape')
        
        ax2.arrow(0, column_height + 200, 0, -150, head_width=d/3,
                 head_length=50, fc='red', ec='red')
        ax2.text(0, column_height + 300, 'P', ha='center', fontsize=14, fontweight='bold')
        
        ax2.set_xlim([-d, d])
        ax2.set_ylim([-100, column_height + 400])
        ax2.set_xlabel('Depth (mm)')
        ax2.legend()
        
        # Cross-section
        ax3 = axes[2]
        ax3.set_title(f'Cross-Section: {section}', fontsize=14, fontweight='bold')
        
        # Draw H-section
        ax3.add_patch(Rectangle((-bf/2, d/2 - tf), bf, tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#bbdefb'))
        ax3.add_patch(Rectangle((-bf/2, -d/2), bf, tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#bbdefb'))
        ax3.add_patch(Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#90caf9'))
        
        ax3.axhline(y=0, color='red', linewidth=1, linestyle='--', alpha=0.7)
        ax3.axvline(x=0, color='red', linewidth=1, linestyle='--', alpha=0.7)
        ax3.text(bf/2 + 10, 0, 'X', fontsize=12, color='red', fontweight='bold')
        ax3.text(0, d/2 + 10, 'Y', fontsize=12, color='red', fontweight='bold')
        
        ax3.set_xlim([-bf*1.2, bf*1.2])
        ax3.set_ylim([-d*1.2, d*1.2])
        ax3.set_aspect('equal')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlabel('Width (mm)')
        ax3.set_ylabel('Height (mm)')
        
        plt.tight_layout()
        return fig
    except Exception as e:
        st.error(f"Error in visualization: {e}")
        return None

# ==================== LOAD DATA ====================
df, df_mat, success = load_data()

if not success:
    st.error("❌ Failed to load data. Please check your internet connection.")
    st.stop()

# ==================== MAIN HEADER ====================
st.markdown('<h1 class="main-header">🏗️ AISC Steel Design Analysis System v5.0</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84;">Enhanced with Correct F2 Calculations</p>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### ⚙️ Design Configuration")
    
    material_list = list(df_mat.index)
    selected_material = st.selectbox(
        "Steel Grade:",
        material_list,
        index=0,
        help="Select steel material grade"
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
        ✅ **{quick_section}**
        - Weight: {weight:.1f} kg/m
        - Zx: {df.loc[quick_section, 'Zx [cm3]']:.0f} cm³
        """)

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Section Properties",
    "🔍 Section Selection",
    "📈 Flexural Design (Mn-Lb)",
    "🏢 Column Design"
])

# ==================== TAB 1: SECTION PROPERTIES ====================
with tab1:
    st.markdown('<h2 class="section-header">Complete Section Properties Table</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section:
        section = st.session_state.selected_section
        st.info(f"**Showing properties for: {section}**")
        
        # Get all properties
        section_data = df.loc[section]
        
        # Create comprehensive table
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
        
        # Full table
        with st.expander("📋 View All Properties"):
            st.dataframe(properties_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section from the sidebar")

# ==================== TAB 2: SECTION SELECTION ====================
with tab2:
    st.markdown('<h2 class="section-header">Section Selection with Filters</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Moment Design")
        Mu = st.number_input("Design Moment Mu (kN·m):", min_value=0.0, value=500.0, step=50.0)
        phi = 0.9
        
        if Mu > 0 and selected_material:
            required_zx = calculate_required_properties(Mu, phi)
            if selected_material in required_zx:
                st.success(f"Required Zx ≥ {required_zx[selected_material]:.0f} cm³")
    
    with col2:
        st.markdown("#### Service Load")
        L_span = st.number_input("Span Length (m):", min_value=1.0, value=6.0, step=0.5)
        Lb_service = st.number_input("Unbraced Length (m):", min_value=0.1, value=3.0, step=0.5)
    
    with col3:
        st.markdown("#### Filters")
        depth_max = st.number_input("Max Depth (mm):", min_value=0, value=0, help="0 = no limit")
        weight_max = st.number_input("Max Weight (kg/m):", min_value=0, value=0, help="0 = no limit")
    
    # Filter sections
    filtered_df = df.copy()
    
    if Mu > 0 and selected_material:
        zx_min = calculate_required_properties(Mu, phi)[selected_material]
        filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= zx_min]
    
    if depth_max > 0:
        filtered_df = filtered_df[filtered_df['d [mm]'] <= depth_max]
    
    if weight_max > 0:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df = filtered_df[filtered_df[weight_col] <= weight_max]
    
    # Calculate capacities
    st.markdown(f"### Found {len(filtered_df)} Suitable Sections")
    
    if len(filtered_df) > 0:
        # Calculate φMn and service load for each section
        results = []
        for section in filtered_df.index[:20]:  # Limit to 20 for performance
            try:
                Mn, _, _, _, _, _, _, _ = F2(df, df_mat, section, selected_material, Lb_service)
                weight = filtered_df.loc[section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in filtered_df.columns else filtered_df.loc[section, 'w [kg/m]']
                service_w = calculate_service_load_capacity(df, df_mat, section, selected_material, L_span, Lb_service)
                
                results.append({
                    'Section': section,
                    'Weight (kg/m)': weight,
                    'Zx (cm³)': filtered_df.loc[section, 'Zx [cm3]'],
                    'Ix (cm⁴)': filtered_df.loc[section, 'Ix [cm4]'],
                    'φMn (t·m)': 0.9 * Mn,
                    'Service w (kg/m)': service_w
                })
            except:
                continue
        
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('Weight (kg/m)')
            
            # Configure grid for multi-selection
            gb = GridOptionsBuilder.from_dataframe(results_df)
            gb.configure_selection('multiple', use_checkbox=True)
            gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
            grid_options = gb.build()
            
            grid_response = AgGrid(
                results_df.round(2),
                gridOptions=grid_options,
                height=400,
                theme='streamlit',
                update_mode=GridUpdateMode.SELECTION_CHANGED
            )
            
            selected_rows = grid_response['selected_rows']
            if selected_rows is not None and len(selected_rows) > 0:
                st.session_state.selected_sections = [row['Section'] for row in selected_rows]
                st.success(f"✅ Selected {len(selected_rows)} sections for comparison")

# ==================== TAB 3: FLEXURAL DESIGN WITH CORRECT F2 ====================
with tab3:
    st.markdown('<h2 class="section-header">Flexural Design - Correct Mn vs Lb Curves</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Parameters")
            Lb_current = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
            Cb = st.number_input("Cb Factor:", 1.0, 2.3, 1.0, 0.1)
            
            show_phi = st.checkbox("Show φMn curve", value=True)
            show_mn = st.checkbox("Show Mn curve", value=True)
            
            # Calculate using F2 function
            Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, section, selected_material, Lb_current)
            
            st.markdown("### Current Point")
            st.metric("Mn", f"{Mn:.2f} t·m")
            st.metric("φMn", f"{0.9*Mn:.2f} t·m")
            st.metric("Case", Case)
            
            # Classification
            if Mn >= Mp * 0.9:
                st.success("✅ Close to plastic capacity")
            elif Mn >= Mp * 0.7:
                st.warning("⚠️ Moderate reduction")
            else:
                st.error("❌ Significant reduction")
            
            # Critical lengths
            st.markdown("### Critical Lengths")
            st.write(f"**Lp = {Lp:.2f} m**")
            st.caption("Plastic limit")
            st.write(f"**Lr = {Lr:.2f} m**")
            st.caption("Inelastic limit")
        
        with col2:
            # Create plot using F2 arrays
            if Mni and Lni:
                try:
                    # Flatten arrays for plotting
                    Mni_flat = []
                    Lni_flat = []
                    
                    for i in range(len(Mni)):
                        if isinstance(Mni[i], list):
                            Mni_flat.extend(Mni[i])
                            Lni_flat.extend(Lni[i])
                        else:
                            Mni_flat.append(Mni[i])
                            Lni_flat.append(Lni[i])
                    
                    fig = go.Figure()
                    
                    # Mn curve
                    if show_mn:
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=Mni_flat,
                            mode='lines+markers',
                            name='Mn',
                            line=dict(color='#1976d2', width=3),
                            marker=dict(size=6)
                        ))
                    
                    # φMn curve
                    if show_phi:
                        phi_Mni = [0.9 * m for m in Mni_flat]
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=phi_Mni,
                            mode='lines',
                            name='φMn (0.9×Mn)',
                            line=dict(color='#4caf50', width=2, dash='dash')
                        ))
                    
                    # Current point
                    fig.add_trace(go.Scatter(
                        x=[Lb_current], y=[Mn],
                        mode='markers',
                        name=f'Current (Lb={Lb_current}m)',
                        marker=dict(color='#f44336', size=12, symbol='diamond')
                    ))
                    
                    # Mp line
                    fig.add_hline(y=Mp, line_dash="dot", line_color='#ff9800', line_width=2,
                                annotation_text=f"Mp = {Mp:.2f} t·m", annotation_font_size=14)
                    
                    # Lp and Lr lines
                    fig.add_vline(x=Lp, line_dash="dash", line_color='#9c27b0', line_width=2,
                                annotation_text=f"Lp = {Lp:.2f} m", annotation_font_size=14)
                    fig.add_vline(x=Lr, line_dash="dash", line_color='#e91e63', line_width=2,
                                annotation_text=f"Lr = {Lr:.2f} m", annotation_font_size=14)
                    
                    # Zones with large labels
                    fig.add_vrect(x0=0, x1=Lp, fillcolor='#4caf50', opacity=0.15,
                                annotation_text="<b>YIELDING</b>", annotation_position="top",
                                annotation_font_size=16)
                    fig.add_vrect(x0=Lp, x1=Lr, fillcolor='#ff9800', opacity=0.15,
                                annotation_text="<b>INELASTIC LTB</b>", annotation_position="top",
                                annotation_font_size=16)
                    
                    max_x = max(Lni_flat) if Lni_flat else Lr + 10
                    fig.add_vrect(x0=Lr, x1=max_x, fillcolor='#f44336', opacity=0.15,
                                annotation_text="<b>ELASTIC LTB</b>", annotation_position="top",
                                annotation_font_size=16)
                    
                    fig.update_layout(
                        title=f"Moment Capacity vs Unbraced Length - {section}",
                        xaxis_title="Unbraced Length, Lb (m)",
                        yaxis_title="Moment Capacity (t·m)",
                        height=600,
                        hovermode='x unified',
                        showlegend=True,
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error in plotting: {str(e)}")
            
            # Summary table
            st.markdown("### Summary")
            summary_df = pd.DataFrame({
                'Parameter': ['Mp', 'Mn at current Lb', 'φMn', 'Lp', 'Lr', 'Current Lb'],
                'Value': [f"{Mp:.2f} t·m", f"{Mn:.2f} t·m", f"{0.9*Mn:.2f} t·m", 
                         f"{Lp:.2f} m", f"{Lr:.2f} m", f"{Lb_current:.2f} m"],
                'Status': ['Plastic Capacity', Case, 'Design Capacity', 
                          'Yielding → Inelastic', 'Inelastic → Elastic', 'Design Point']
            })
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section from the sidebar")

# ==================== TAB 4: COLUMN DESIGN ====================
with tab4:
    st.markdown('<h2 class="section-header">Column Design with Enhanced Visualization</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.markdown("### Design Parameters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Effective Length Factors")
            Kx = st.selectbox("Kx:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            Ky = st.selectbox("Ky:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            st.info("""
            **K Factors:**
            - 0.5: Fixed-Fixed
            - 0.7: Fixed-Pinned
            - 1.0: Pinned-Pinned
            - 2.0: Fixed-Free
            """)
        
        with col2:
            st.markdown("#### Unbraced Lengths")
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, step=0.1)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, step=0.1)
            
            # Calculate and display KL/r
            rx = float(df.loc[section, 'rx [cm]'])
            ry = float(df.loc[section, 'ry [cm]'])
            KLr_x = (Kx * Lx * 100) / rx
            KLr_y = (Ky * Ly * 100) / ry
            
            col_klr1, col_klr2 = st.columns(2)
            with col_klr1:
                if KLr_x <= 200:
                    st.success(f"KL/rx = {KLr_x:.1f} ✓")
                else:
                    st.error(f"KL/rx = {KLr_x:.1f} > 200 ⚠️")
            
            with col_klr2:
                if KLr_y <= 200:
                    st.success(f"KL/ry = {KLr_y:.1f} ✓")
                else:
                    st.error(f"KL/ry = {KLr_y:.1f} > 200 ⚠️")
        
        with col3:
            st.markdown("#### Applied Load")
            Pu = st.number_input("Pu (tons):", min_value=0.0, value=100.0, step=10.0)
            
            # Plane selection for display
            display_plane = st.selectbox("Display:", ["Both Planes", "Strong Axis", "Weak Axis"])
        
        # Calculate compression capacity
        comp_results = compression_analysis_advanced(df, df_mat, section, selected_material, Kx*Lx, Ky*Ly)
        
        if comp_results:
            st.markdown("### Analysis Results")
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("φPn", f"{comp_results['phi_Pn']:.2f} tons",
                         delta=f"Pn = {comp_results['Pn']:.2f} tons")
            
            with col_r2:
                ratio = Pu / comp_results['phi_Pn'] if comp_results['phi_Pn'] > 0 else 999
                st.metric("Utilization", f"{ratio:.3f}",
                         delta="OK" if ratio <= 1.0 else "NG")
            
            with col_r3:
                if comp_results['lambda_max'] <= comp_results['lambda_limit']:
                    st.metric("Buckling", "🟡 Inelastic",
                             delta=f"λ = {comp_results['lambda_max']:.1f}")
                else:
                    st.metric("Buckling", "🔵 Elastic",
                             delta=f"λ = {comp_results['lambda_max']:.1f}")
            
            if ratio <= 1.0:
                st.success(f"✅ Design PASSES - Factor of Safety: {1/ratio:.2f}")
            else:
                st.error(f"❌ Design FAILS - Overstressed by {(ratio-1)*100:.1f}%")
        
        # Column visualization
        st.markdown("### Column Visualization - Both Principal Planes")
        fig_vis = visualize_column_2d_enhanced(df, section)
        if fig_vis:
            st.pyplot(fig_vis)
        
        # Capacity curve
        st.markdown("### Column Capacity Curve")
        
        col_curve1, col_curve2 = st.columns([1, 3])
        
        with col_curve1:
            curve_axis = st.radio("Select Axis:", ["Strong (X-X)", "Weak (Y-Y)"])
            show_regions = st.checkbox("Show regions", value=True)
            show_demand = st.checkbox("Show demand", value=True)
        
        with col_curve2:
            # Generate capacity curve
            KLr_range = np.linspace(1, 250, 500)
            Pn_values = []
            
            Fy = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
            E = float(df_mat.loc[selected_material, "E"])
            Ag = float(df.loc[section, 'A [cm2]'])
            
            lambda_limit = 4.71 * mt.sqrt(E / Fy)
            
            for klr in KLr_range:
                Fe = (mt.pi**2 * E) / (klr**2)
                
                if klr <= lambda_limit:
                    # Inelastic: Fcr = 0.658^(Fy/Fe) * Fy
                    Fcr = Fy * (0.658**(Fy/Fe))
                else:
                    # Elastic: Fcr = 0.877 * Fe
                    Fcr = 0.877 * Fe
                
                Pn = 0.9 * Fcr * Ag / 1000
                Pn_values.append(Pn)
            
            fig_capacity = go.Figure()
            
            # Capacity curve
            fig_capacity.add_trace(go.Scatter(
                x=KLr_range, y=Pn_values,
                mode='lines',
                name='φPn',
                line=dict(color='#1976d2', width=3)
            ))
            
            # Current point
            if comp_results:
                current_klr = comp_results['lambda_x'] if "Strong" in curve_axis else comp_results['lambda_y']
                fig_capacity.add_trace(go.Scatter(
                    x=[current_klr], y=[comp_results['phi_Pn']],
                    mode='markers',
                    name='Current Design',
                    marker=dict(color='#f44336', size=12, symbol='star')
                ))
            
            # Transition line at 4.71√(E/Fy)
            fig_capacity.add_vline(x=lambda_limit, line_dash="dash", line_color='#ff9800', line_width=2,
                                  annotation_text=f"λ = {lambda_limit:.1f}", annotation_font_size=14)
            
            # Regions
            if show_regions:
                fig_capacity.add_vrect(x0=0, x1=lambda_limit, fillcolor='#ffc107', opacity=0.1,
                                      annotation_text="<b>INELASTIC</b><br>Fcr = 0.658^(Fy/Fe)·Fy",
                                      annotation_position="top left", annotation_font_size=14)
                fig_capacity.add_vrect(x0=lambda_limit, x1=250, fillcolor='#2196f3', opacity=0.1,
                                      annotation_text="<b>ELASTIC</b><br>Fcr = 0.877·Fe",
                                      annotation_position="top right", annotation_font_size=14)
            
            # KL/r = 200 limit
            fig_capacity.add_vline(x=200, line_dash="dot", line_color='#f44336', line_width=2,
                                  annotation_text="KL/r = 200 (Limit)", annotation_font_size=12)
            
            # Demand line
            if show_demand and Pu > 0:
                fig_capacity.add_hline(y=Pu, line_dash="dash", line_color='#4caf50', line_width=2,
                                      annotation_text=f"Pu = {Pu:.1f} tons", annotation_font_size=14)
            
            fig_capacity.update_layout(
                title=f"Column Capacity - {curve_axis}",
                xaxis_title="Slenderness Ratio (KL/r)",
                yaxis_title="Design Capacity φPn (tons)",
                height=500,
                template='plotly_white'
            )
            
            st.plotly_chart(fig_capacity, use_container_width=True)
        
        # Summary table
        if comp_results:
            st.markdown("### Design Summary")
            summary_col = pd.DataFrame({
                'Parameter': ['λx', 'λy', 'λ limit', 'Fe', 'Fcr', 'Pn', 'φPn', 'Pu', 'Utilization'],
                'Value': [f"{comp_results['lambda_x']:.1f}", f"{comp_results['lambda_y']:.1f}",
                         f"{comp_results['lambda_limit']:.1f}", f"{comp_results['Fe']:.1f} ksc",
                         f"{comp_results['Fcr']:.1f} ksc", f"{comp_results['Pn']:.2f} tons",
                         f"{comp_results['phi_Pn']:.2f} tons", f"{Pu:.2f} tons",
                         f"{Pu/comp_results['phi_Pn']:.3f}" if comp_results['phi_Pn'] > 0 else "N/A"],
                'Unit/Note': ['KLx/rx', 'KLy/ry', '4.71√(E/Fy)', 'Elastic buckling',
                             'Critical stress', 'Nominal', 'Design', 'Applied', 'Pu/φPn']
            })
            st.dataframe(summary_col, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section from the sidebar")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><b>AISC Steel Design Analysis v5.0</b></p>
    <p>Enhanced with Correct F2 Function | Service Loads in kg/m</p>
    <p>Based on AISC 360-16 Specification</p>
</div>
""", unsafe_allow_html=True)
