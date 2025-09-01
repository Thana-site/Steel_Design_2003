# ==================== ENHANCED STEEL DESIGN ANALYSIS APPLICATION ====================
# Version: 5.1 - Corrected and Optimized
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

# ==================== CORRECTED F2 FUNCTION ====================
def F2(df, df_mat, section, material, Lb):
    """F2 Analysis for doubly symmetric compact I-shaped members - CORRECTED VERSION"""
    try:
        Cb = 1.0
        Lb_cm = Lb * 100  # Convert Lb from m to cm
        
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
        c = 1.0
        h0 = float(df.loc[section, 'ho [mm]']) / 10 if 'ho [mm]' in df.columns else float(df.loc[section, 'd [mm]']) / 10
        
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        
        # Calculate Mn based on Lb
        if Lb_cm < Lp:
            Case = "F2.1 - Plastic Yielding"
            Mp = Fy * Z_Major 
            Mn = Mp
        elif Lp <= Lb_cm < Lr:
            Case = "F2.2 - Inelastic LTB"
            Mp = Fy * Z_Major
            Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb_cm - Lp) / (Lr - Lp))))
            Mp = Mp / 100000  # Convert to t·m
            Mn = min(Mp * 100000, Mn) / 100000  # Convert to t·m and ensure Mn ≤ Mp
        else:
            Case = "F2.3 - Elastic LTB"
            Mp = Fy * Z_Major / 100000  # t·m
            Term_1 = (Cb * mt.pi ** 2 * E) / (((Lb_cm) / rts) ** 2)
            Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * (((Lb_cm) / rts) ** 2)
            Term12 = Term_1 * mt.sqrt(1 + Term_2)
            Mn = Term12 * S_Major / 100000  # Convert to t·m
        
        # Convert all to t·m
        if Case != "F2.3 - Elastic LTB":
            Mp = Mp / 100000 if isinstance(Mp, (int, float)) and Mp > 1000 else Mp
            Mn = Mn / 100000 if isinstance(Mn, (int, float)) and Mn > 1000 else Mn
        
        # Convert lengths back to meters
        Lp_m = Lp / 100
        Lr_m = Lr / 100
        
        return Mn, Lb, Lp_m, Lr_m, Mp, Case
        
    except Exception as e:
        st.error(f"Error in F2 calculation: {str(e)}")
        return 0, 0, 0, 0, 0, "Error"

def generate_moment_capacity_curve(df, df_mat, section, material, Lb_max=20.0):
    """Generate moment capacity curve for plotting"""
    try:
        Lb_range = np.linspace(0.1, Lb_max, 200)
        Mn_values = []
        
        for lb in Lb_range:
            Mn, _, _, _, _, _ = F2(df, df_mat, section, material, lb)
            Mn_values.append(Mn)
        
        return Lb_range, Mn_values
    except Exception as e:
        st.error(f"Error generating curve: {str(e)}")
        return [], []

def calculate_required_properties(Mu, selected_material, Fy_value, phi=0.9):
    """Calculate required section properties based on design moment"""
    Mu_tm = Mu  # Already in t·m (ton-meter)
    Zx_req = (Mu_tm * 100000) / (phi * Fy_value)  # cm³
    return Zx_req

def calculate_required_ix(w, L, delta_limit, E=2.04e6):
    """Calculate required Ix based on deflection limit"""
    w_kg_cm = w / 100  # Convert kg/m to kg/cm
    L_cm = L * 100  # Convert m to cm
    delta_max = L_cm / delta_limit
    Ix_req = (5 * w_kg_cm * L_cm**4) / (384 * E * delta_max)
    return Ix_req

def calculate_service_load_capacity(df, df_mat, section, material, L, Lb):
    """Calculate service load capacity in kg/m"""
    try:
        Mn, _, _, _, _, _ = F2(df, df_mat, section, material, Lb)
        phi_Mn = 0.9 * Mn  # t·m
        phi_Mn_kg_cm = phi_Mn * 100000
        L_cm = L * 100
        w = (8 * phi_Mn_kg_cm) / (L_cm**2)  # kg/cm
        w_per_m = w * 100  # kg/m
        return w_per_m
    except:
        return 0

def compression_analysis_advanced(df, df_mat, section, material, KLx, KLy):
    """Advanced compression member analysis"""
    try:
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        
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

def visualize_column_2d_simple(df, section):
    """Simplified 2D column visualization"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
        
        # Get dimensions
        d = float(df.loc[section, 'd [mm]'])
        bf = float(df.loc[section, 'bf [mm]'])
        tw = float(df.loc[section, 'tw [mm]'])
        tf = float(df.loc[section, 'tf [mm]'])
        
        # Strong axis buckling (edge view)
        ax1.set_title('Strong Axis Buckling\n(Edge View)', fontweight='bold')
        
        # Draw section edge view
        ax1.add_patch(Rectangle((-tf/2, 0), tf, tf, facecolor='lightblue', edgecolor='blue'))
        ax1.add_patch(Rectangle((-tw/2, tf), tw, d-2*tf, facecolor='lightgreen', edgecolor='blue'))
        ax1.add_patch(Rectangle((-tf/2, d-tf), tf, tf, facecolor='lightblue', edgecolor='blue'))
        
        # Buckling curve
        y = np.linspace(0, d, 100)
        x_buckled = 30 * np.sin(np.pi * y / d)
        ax1.plot(x_buckled, y, 'r-', linewidth=3, label='Buckled Shape')
        
        ax1.set_xlim([-60, 60])
        ax1.set_ylim([-20, d+20])
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Weak axis buckling (front view)
        ax2.set_title('Weak Axis Buckling\n(Front View)', fontweight='bold')
        
        # Draw section front view
        ax2.add_patch(Rectangle((-bf/2, 0), bf, tf, facecolor='lightcoral', edgecolor='red'))
        ax2.add_patch(Rectangle((-bf/2, d-tf), bf, tf, facecolor='lightcoral', edgecolor='red'))
        ax2.plot([0, 0], [tf, d-tf], 'k-', linewidth=2, alpha=0.5, label='Web')
        
        # Buckling curve
        x_buckled_weak = 20 * np.sin(np.pi * y / d)
        ax2.plot(x_buckled_weak, y, 'r-', linewidth=3, label='Buckled Shape')
        
        ax2.set_xlim([-bf*0.7, bf*0.7])
        ax2.set_ylim([-20, d+20])
        ax2.set_aspect('equal')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        fig.suptitle(f'Column Buckling Analysis - {section}', fontsize=14, fontweight='bold')
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
st.markdown('<h1 class="main-header">🏗️ AISC Steel Design Analysis System v5.1</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84;">Corrected and Optimized Analysis with AISC 360-16</p>', unsafe_allow_html=True)

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
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Section Properties",
    "🔍 Section Selection", 
    "📈 Flexural Design",
    "🏢 Column Design",
    "🏗️ Beam-Column",
    "📊 Comparison"
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
        Mu = st.number_input("Design Moment Mu (t·m):", min_value=0.0, value=50.0, step=5.0,
                            help="Enter design moment in t·m (ton-meter)")
        phi = 0.9
        
        if Mu > 0 and selected_material:
            Fy_value = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
            Zx_req = calculate_required_properties(Mu, selected_material, Fy_value, phi)
            st.success(f"Required Zx ≥ {Zx_req:.0f} cm³")
    
    with col2:
        st.markdown("#### Deflection Control")
        L_span = st.number_input("Span Length (m):", min_value=1.0, value=6.0, step=0.5,
                                help="Enter span length in meters")
        w_load = st.number_input("Service Load w (kg/m):", min_value=0.0, value=100.0, step=10.0,
                               help="Enter distributed load in kg/m")
        deflection_limit = st.selectbox("Deflection Limit:", 
                                       ["L/200", "L/250", "L/300", "L/360", "L/400"],
                                       index=2, help="Select deflection limit ratio")
        
        # Calculate required Ix
        if w_load > 0 and L_span > 0:
            limit_value = float(deflection_limit.split('/')[1])
            Ix_req = calculate_required_ix(w_load, L_span, limit_value)
            st.success(f"Required Ix ≥ {Ix_req:.0f} cm⁴")
    
    with col3:
        st.markdown("#### Additional Filters")
        depth_max = st.number_input("Max Depth (mm):", min_value=0, value=0, help="0 = no limit")
        weight_max = st.number_input("Max Weight (kg/m):", min_value=0, value=200, step=10,
                                    help="0 = no limit")
        
        # Preference
        optimization = st.selectbox("Optimize for:",
                                   ["Minimum Weight", "Minimum Depth", "Maximum Efficiency"],
                                   index=0)
    
    # Filter sections
    filtered_df = df.copy()
    
    if Mu > 0 and selected_material:
        Fy_value = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
        zx_min = calculate_required_properties(Mu, selected_material, Fy_value, phi)
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
    
    # Display filtered sections
    st.markdown(f"### Found {len(filtered_df)} Suitable Sections")
    
    if len(filtered_df) > 0:
        # Reset index to make Section a column
        filtered_df_display = filtered_df.reset_index()
        
        # Select important columns to display
        display_cols = ['Section', 'd [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 
                       'A [cm2]', weight_col, 'Ix [cm4]', 'Iy [cm4]', 
                       'Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]', 
                       'rx [cm]', 'ry [cm]']
        
        # Only include columns that exist in the dataframe
        available_cols = [col for col in display_cols if col in filtered_df_display.columns]
        
        # Configure AgGrid for multi-selection
        gb = GridOptionsBuilder.from_dataframe(filtered_df_display[available_cols])
        gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=False, groupSelectsFiltered=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_column("Section", headerCheckboxSelection=True)
        gb.configure_default_column(resizable=True, filterable=True, sortable=True)
        grid_options = gb.build()
        
        # Display grid
        st.markdown("#### 📋 Section Properties Database (Select sections using checkboxes)")
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
            st.success(f"✅ Selected {len(selected_sections)} sections for analysis")

# ==================== TAB 3: FLEXURAL DESIGN (CORRECTED) ====================
with tab3:
    st.markdown('<h2 class="section-header">Flexural Design - Corrected Mn vs Lb Curves</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Parameters")
            Lb_current = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
            
            # Calculate using corrected F2 function
            Mn, Lb_calc, Lp, Lr, Mp, Case = F2(df, df_mat, section, selected_material, Lb_current)
            
            st.markdown("### Current Analysis")
            st.metric("Mn", f"{Mn:.2f} t·m")
            st.metric("φMn", f"{0.9*Mn:.2f} t·m")
            st.info(f"**Case:** {Case}")
            
            # Classification
            if Mn >= Mp * 0.95:
                st.success("✅ Plastic capacity achieved")
            elif Mn >= Mp * 0.8:
                st.warning("⚠️ Good capacity")
            else:
                st.error("❌ Significant reduction")
            
            # Critical lengths
            st.markdown("### Critical Lengths")
            st.write(f"**Lp = {Lp:.2f} m**")
            st.caption("Compact limit")
            st.write(f"**Lr = {Lr:.2f} m**")
            st.caption("Noncompact limit")
            st.write(f"**Mp = {Mp:.2f} t·m**")
            st.caption("Plastic moment")
        
        with col2:
            st.markdown("### Moment Capacity Curve")
            
            # Generate corrected moment capacity curve
            try:
                Lb_range, Mn_values = generate_moment_capacity_curve(df, df_mat, section, selected_material, 20.0)
                
                if Lb_range and Mn_values:
                    fig = go.Figure()
                    
                    # Mn curve
                    fig.add_trace(go.Scatter(
                        x=Lb_range, y=Mn_values,
                        mode='lines',
                        name='Mn',
                        line=dict(color='#1976d2', width=3),
                        hovertemplate='Lb: %{x:.2f}m<br>Mn: %{y:.2f} t·m<extra></extra>'
                    ))
                    
                    # φMn curve
                    phi_Mn_values = [0.9 * m for m in Mn_values]
                    fig.add_trace(go.Scatter(
                        x=Lb_range, y=phi_Mn_values,
                        mode='lines',
                        name='φMn (0.9×Mn)',
                        line=dict(color='#4caf50', width=2, dash='dash'),
                        hovertemplate='Lb: %{x:.2f}m<br>φMn: %{y:.2f} t·m<extra></extra>'
                    ))
                    
                    # Current point
                    fig.add_trace(go.Scatter(
                        x=[Lb_current], y=[Mn],
                        mode='markers',
                        name=f'Current Point (Lb={Lb_current:.1f}m)',
                        marker=dict(color='#f44336', size=12, symbol='diamond'),
                        hovertemplate=f'Current Point<br>Lb: {Lb_current:.2f}m<br>Mn: {Mn:.2f} t·m<extra></extra>'
                    ))
                    
                    # Mp line (plastic moment)
                    fig.add_hline(y=Mp, line_dash="dot", line_color='#ff9800', line_width=2,
                                annotation_text=f"Mp = {Mp:.2f} t·m", annotation_font_size=12)
                    
                    # Critical length lines
                    fig.add_vline(x=Lp, line_dash="dash", line_color='#9c27b0', line_width=2,
                                annotation_text=f"Lp = {Lp:.2f}m", annotation_font_size=12)
                    fig.add_vline(x=Lr, line_dash="dash", line_color='#e91e63', line_width=2,
                                annotation_text=f"Lr = {Lr:.2f}m", annotation_font_size=12)
                    
                    # Behavior regions
                    fig.add_vrect(x0=0, x1=Lp, fillcolor='#4caf50', opacity=0.1,
                                annotation_text="<b>YIELDING</b><br>Mn = Mp", 
                                annotation_position="top", annotation_font_size=14)
                    fig.add_vrect(x0=Lp, x1=Lr, fillcolor='#ff9800', opacity=0.1,
                                annotation_text="<b>INELASTIC LTB</b><br>Linear transition", 
                                annotation_position="top", annotation_font_size=14)
                    fig.add_vrect(x0=Lr, x1=20, fillcolor='#f44336', opacity=0.1,
                                annotation_text="<b>ELASTIC LTB</b><br>Mn ∝ 1/Lb²", 
                                annotation_position="top", annotation_font_size=14)
                    
                    fig.update_layout(
                        title=f"Flexural Capacity - {section} ({selected_material})",
                        xaxis_title="Unbraced Length, Lb (m)",
                        yaxis_title="Moment Capacity (t·m)",
                        height=500,
                        hovermode='x unified',
                        template='plotly_white',
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("Error generating moment capacity curve")
                    
            except Exception as e:
                st.error(f"Error in curve generation: {str(e)}")
            
            # Summary table
            st.markdown("### Design Summary")
            summary_data = {
                'Parameter': ['Mp (Plastic Moment)', 'Mn (Current)', 'φMn (Design)', 
                             'Lp (Compact)', 'Lr (Noncompact)', 'Current Lb', 'Efficiency'],
                'Value': [f"{Mp:.2f} t·m", f"{Mn:.2f} t·m", f"{0.9*Mn:.2f} t·m", 
                         f"{Lp:.2f} m", f"{Lr:.2f} m", f"{Lb_current:.2f} m", f"{(Mn/Mp)*100:.1f}%"],
                'Note': ['Maximum possible', Case, 'With safety factor', 
                        'Yielding limit', 'Inelastic limit', 'Design value', 'Mn/Mp ratio']
            }
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar")

# ==================== TAB 4: COLUMN DESIGN (SIMPLIFIED) ====================
with tab4:
    st.markdown('<h2 class="section-header">Column Design Analysis</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.info(f"**Analyzing:** {section} | **Material:** {selected_material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Design Parameters")
            
            # Effective length factors
            Kx = st.selectbox("Kx:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            Ky = st.selectbox("Ky:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            
            # Unbraced lengths
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, step=0.1)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, step=0.1)
            
            # Applied load
            Pu = st.number_input("Pu (tons):", min_value=0.0, value=100.0, step=10.0)
            
            # Calculate and display KL/r
            rx = float(df.loc[section, 'rx [cm]'])
            ry = float(df.loc[section, 'ry [cm]'])
            KLr_x = (Kx * Lx * 100) / rx
            KLr_y = (Ky * Ly * 100) / ry
            
            st.markdown("### Slenderness Ratios")
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
        
        # Calculate compression capacity
        comp_results = compression_analysis_advanced(df, df_mat, section, selected_material, Kx*Lx, Ky*Ly)
        
        if comp_results:
            with col1:
                st.markdown("### Results")
                st.metric("φPn", f"{comp_results['phi_Pn']:.2f} tons",
                         delta=f"Pn = {comp_results['Pn']:.2f} tons")
                
                ratio = Pu / comp_results['phi_Pn'] if comp_results['phi_Pn'] > 0 else 999
                st.metric("Utilization", f"{ratio:.3f}",
                         delta="OK" if ratio <= 1.0 else "NG")
                
                if ratio <= 1.0:
                    st.success(f"✅ Design PASSES")
                else:
                    st.error(f"❌ Design FAILS")
            
            with col2:
                st.markdown("### Column Capacity Curve")
                
                # Generate capacity curve
                KLr_range = np.linspace(1, 250, 200)
                Pn_values = []
                
                Fy = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
                E = float(df_mat.loc[selected_material, "E"])
                Ag = float(df.loc[section, 'A [cm2]'])
                
                lambda_limit = 4.71 * mt.sqrt(E / Fy)
                
                for klr in KLr_range:
                    Fe = (mt.pi**2 * E) / (klr**2)
                    
                    if klr <= lambda_limit:
                        Fcr = Fy * (0.658**(Fy/Fe))
                    else:
                        Fcr = 0.877 * Fe
                    
                    Pn = 0.9 * Fcr * Ag / 1000
                    Pn_values.append(Pn)
                
                fig = go.Figure()
                
                # Capacity curve
                fig.add_trace(go.Scatter(
                    x=KLr_range, y=Pn_values,
                    mode='lines',
                    name='φPn',
                    line=dict(color='#1976d2', width=3)
                ))
                
                # Current point
                current_klr = max(comp_results['lambda_x'], comp_results['lambda_y'])
                fig.add_trace(go.Scatter(
                    x=[current_klr], y=[comp_results['phi_Pn']],
                    mode='markers',
                    name='Current Design',
                    marker=dict(color='#f44336', size=12, symbol='star')
                ))
                
                # Transition line
                fig.add_vline(x=lambda_limit, line_dash="dash", line_color='#ff9800', line_width=2,
                            annotation_text=f"λ = {lambda_limit:.1f}")
                
                # KL/r = 200 limit
                fig.add_vline(x=200, line_dash="dot", line_color='#f44336', line_width=2,
                            annotation_text="KL/r = 200")
                
                # Demand line
                if Pu > 0:
                    fig.add_hline(y=Pu, line_dash="dash", line_color='#4caf50', line_width=2,
                                annotation_text=f"Pu = {Pu:.1f} tons")
                
                fig.update_layout(
                    title="Column Capacity Curve",
                    xaxis_title="Slenderness Ratio (KL/r)",
                    yaxis_title="Design Capacity φPn (tons)",
                    height=400,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Optional simplified visualization
                if st.checkbox("Show column buckling visualization"):
                    fig_vis = visualize_column_2d_simple(df, section)
                    if fig_vis:
                        st.pyplot(fig_vis)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar")

# ==================== TAB 5: BEAM-COLUMN ====================
with tab5:
    st.markdown('<h2 class="section-header">Beam-Column Interaction Design</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and selected_material:
        section = st.session_state.selected_section
        
        st.info(f"**Analyzing:** {section} | **Material:** {selected_material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Combined Loading")
            
            # Loads
            Pu_bc = st.slider("Axial Load Pu (tons):", 
                             min_value=0.0, max_value=200.0, value=50.0, step=1.0)
            Mux = st.slider("Moment Mux (t·m):", 
                           min_value=0.0, max_value=100.0, value=30.0, step=1.0)
            Muy = st.slider("Moment Muy (t·m):", 
                           min_value=0.0, max_value=50.0, value=5.0, step=0.5)
            
            # Effective lengths
            KLx_bc = st.slider("KLx (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            KLy_bc = st.slider("KLy (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            Lb_bc = st.slider("Lb for LTB (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
        
        # Analysis
        comp_results = compression_analysis_advanced(df, df_mat, section, selected_material, KLx_bc, KLy_bc)
        Mnx, _, _, _, _, _ = F2(df, df_mat, section, selected_material, Lb_bc)
        
        # Minor axis capacity (simplified)
        Zy = float(df.loc[section, 'Zy [cm3]'])
        Fy = float(df_mat.loc[selected_material, "Yield Point (ksc)"])
        Mny = Fy * Zy / 100000  # t·m
        
        if comp_results:
            Pc = comp_results['phi_Pn']
            Mcx = 0.9 * Mnx
            Mcy = 0.9 * Mny
            
            # Interaction check
            if Pc > 0 and Mcx > 0 and Mcy > 0:
                if Pu_bc/Pc >= 0.2:
                    interaction = Pu_bc/Pc + (8/9)*(Mux/Mcx + Muy/Mcy)
                    equation = "H1-1a"
                else:
                    interaction = Pu_bc/(2*Pc) + (Mux/Mcx + Muy/Mcy)
                    equation = "H1-1b"
                
                with col1:
                    st.markdown("### Results")
                    st.metric("P/φPn", f"{Pu_bc/Pc:.3f}")
                    st.metric("Mx/φMnx", f"{Mux/Mcx:.3f}")
                    st.metric("My/φMny", f"{Muy/Mcy:.3f}")
                    st.metric("Unity Check", f"{interaction:.3f}", 
                             delta=f"Equation {equation}")
                    
                    if interaction <= 1.0:
                        st.success(f"✅ DESIGN PASSES")
                    else:
                        st.error(f"❌ DESIGN FAILS")
                
                with col2:
                    st.markdown("### P-M Interaction Diagram")
                    
                    # Generate interaction curve
                    P_ratios = np.linspace(0, 1, 50)
                    M_ratios = []
                    
                    for p_ratio in P_ratios:
                        if p_ratio >= 0.2:
                            m_ratio = (9/8) * (1 - p_ratio)
                        else:
                            m_ratio = 1 - p_ratio/2
                        M_ratios.append(max(0, m_ratio))
                    
                    fig = go.Figure()
                    
                    # Interaction curve
                    fig.add_trace(go.Scatter(
                        x=M_ratios, y=P_ratios,
                        mode='lines',
                        name='Interaction Curve',
                        line=dict(color='#2196f3', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(33, 150, 243, 0.2)'
                    ))
                    
                    # Design point
                    M_combined = Mux/Mcx + Muy/Mcy
                    P_ratio = Pu_bc/Pc
                    
                    fig.add_trace(go.Scatter(
                        x=[M_combined], y=[P_ratio],
                        mode='markers',
                        name='Design Point',
                        marker=dict(color='#f44336', size=15, symbol='star')
                    ))
                    
                    fig.update_layout(
                        title="P-M Interaction Diagram",
                        xaxis_title="Combined Moment Ratio (ΣM/ΣMc)",
                        yaxis_title="Axial Force Ratio (P/Pc)",
                        height=400,
                        template='plotly_white',
                        xaxis=dict(range=[0, 1.2]),
                        yaxis=dict(range=[0, 1.2])
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar")

# ==================== TAB 6: COMPARISON ====================
with tab6:
    st.markdown('<h2 class="section-header">Multi-Section Comparison Tool</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_sections:
        st.info(f"Comparing {len(st.session_state.selected_sections)} sections")
        
        # Comparison parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            comparison_type = st.selectbox("Comparison Type:",
                ["Moment Capacity", "Compression Capacity", "Weight Efficiency"])
        
        with col2:
            Lb_comp = st.slider("Unbraced Length (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        with col3:
            KL_comp = st.slider("Effective Length (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        # Generate comparison data
        comparison_data = []
        
        for section_name in st.session_state.selected_sections:
            if section_name not in df.index:
                continue
            
            try:
                weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
                weight = df.loc[section_name, weight_col]
                
                # Flexural analysis
                Mn, _, _, _, _, _ = F2(df, df_mat, section_name, selected_material, Lb_comp)
                
                # Compression analysis
                comp_results = compression_analysis_advanced(df, df_mat, section_name, selected_material, 
                                                            KL_comp, KL_comp)
                
                if comp_results:
                    comparison_data.append({
                        'Section': section_name,
                        'Weight (kg/m)': weight,
                        'φMn (t·m)': 0.9 * Mn,
                        'φPn (tons)': comp_results['phi_Pn'],
                        'Moment Efficiency': (0.9 * Mn) / weight,
                        'Compression Efficiency': comp_results['phi_Pn'] / weight
                    })
            except:
                continue
        
        if comparison_data:
            df_comparison = pd.DataFrame(comparison_data)
            
            # Display comparison chart
            if comparison_type == "Moment Capacity":
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['φMn (t·m)'],
                    text=[f'{v:.1f}' for v in df_comparison['φMn (t·m)']],
                    textposition='auto',
                    marker_color='#2196f3'
                ))
                fig.update_layout(title=f"Moment Capacity at Lb = {Lb_comp:.1f} m",
                                 yaxis_title="φMn (t·m)", template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
                
            elif comparison_type == "Compression Capacity":
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['φPn (tons)'],
                    text=[f'{v:.1f}' for v in df_comparison['φPn (tons)']],
                    textposition='auto',
                    marker_color='#4caf50'
                ))
                fig.update_layout(title=f"Compression Capacity at KL = {KL_comp:.1f} m",
                                 yaxis_title="φPn (tons)", template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
                
            else:  # Weight Efficiency
                fig = make_subplots(rows=1, cols=2,
                                   subplot_titles=('Moment Efficiency', 'Compression Efficiency'))
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Moment Efficiency'],
                    marker_color='#ff9800'
                ), row=1, col=1)
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Compression Efficiency'],
                    marker_color='#9c27b0'
                ), row=1, col=2)
                
                fig.update_layout(title="Efficiency Comparison (Capacity/Weight)",
                                 height=400, template='plotly_white', showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Comparison table
            st.markdown("### Detailed Comparison")
            st.dataframe(df_comparison.round(2), use_container_width=True, hide_index=True)
            
            # Recommendations
            st.markdown("### 🏆 Recommendations")
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                best_moment = df_comparison.loc[df_comparison['φMn (t·m)'].idxmax()]
                st.info(f"""
                **Highest Moment:**
                {best_moment["Section"]}
                φMn: {best_moment["φMn (t·m)"]:.2f} t·m
                """)
            
            with col_r2:
                best_compression = df_comparison.loc[df_comparison['φPn (tons)'].idxmax()]
                st.info(f"""
                **Highest Compression:**
                {best_compression["Section"]}
                φPn: {best_compression["φPn (tons)"]:.1f} tons
                """)
            
            with col_r3:
                lightest = df_comparison.loc[df_comparison['Weight (kg/m)'].idxmin()]
                st.info(f"""
                **Lightest Section:**
                {lightest["Section"]}
                Weight: {lightest["Weight (kg/m)"]:.1f} kg/m
                """)
    else:
        st.warning("⚠️ Please select sections from the 'Section Selection' tab first")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><b>AISC Steel Design Analysis v5.1 - Corrected Version</b></p>
    <p>✅ Fixed F2 Function | ✅ Corrected Moment Curves | ✅ Simplified Visualizations</p>
    <p>© 2024 - Educational Tool for Structural Engineers</p>
</div>
""", unsafe_allow_html=True)
