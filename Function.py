# ==================== IMPROVED STEEL DESIGN ANALYSIS APPLICATION ====================
# Version: 3.1 - Real-time Interactive with Multi-Selection
# GitHub: Thana-site/Steel_Design_2003

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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

# ==================== SIMPLIFIED CUSTOM CSS ====================
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
    
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
    
    /* Better contrast for dark mode compatibility */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a237e;
        margin-bottom: 1rem;
    }
    
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #283593;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
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

def calculate_required_properties(Mu, phi=0.9):
    """Calculate required section properties based on design moment"""
    # Mu in kN·m, convert to t·m
    Mu_tm = Mu / 9.81
    
    # Calculate required Zx for different steel grades
    required_zx = {}
    steel_grades = {
        'SS400': 2400,  # kg/cm²
        'SM490': 3300,
        'SM520': 3600,
        'SM570': 4600
    }
    
    for grade, Fy in steel_grades.items():
        Zx_req = (Mu_tm * 100000) / (phi * Fy)  # cm³
        required_zx[grade] = Zx_req
    
    return required_zx

def calculate_required_ix(w, L, delta_limit, E=2.04e6):
    """
    Calculate required Ix based on deflection limit
    w: uniform load (kN/m)
    L: span length (m)
    delta_limit: deflection limit (L/300, L/400, etc.)
    E: modulus of elasticity (kg/cm²)
    """
    # Convert units
    w_kg = w * 1000 / 9.81  # kg/m to kg/cm
    L_cm = L * 100  # m to cm
    
    # For simply supported beam: δ = 5wL⁴/(384EI)
    delta_max = L_cm / delta_limit
    Ix_req = (5 * w_kg * L_cm**4) / (384 * E * delta_max)
    
    return Ix_req

def visualize_column_with_load(P, section_name, buckling_mode="Flexural"):
    """Create visualization of column with axial load and buckling mode"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Column elevation view
    ax1.set_title(f'Column: {section_name}\nP = {P:.1f} tons | Mode: {buckling_mode}', 
                 fontsize=12, fontweight='bold')
    
    # Draw column
    column_width = 0.3
    column_height = 3.0
    
    # Column shape - show buckling shape
    if buckling_mode == "Flexural":
        # Draw buckled shape
        y = np.linspace(0, column_height, 100)
        x = 0.1 * np.sin(np.pi * y / column_height)
        ax1.plot(x, y, 'b--', lw=2, alpha=0.5, label='Buckled shape')
    elif buckling_mode == "Flexural-Torsional":
        # Show rotation
        for i in range(5):
            y_pos = i * column_height / 4
            ax1.plot([-column_width/2, column_width/2], [y_pos, y_pos], 'r-', lw=1, alpha=0.5)
            # Add rotation arrow
            if i > 0:
                circle = patches.FancyArrowPatch((-column_width/3, y_pos), 
                                                (column_width/3, y_pos),
                                                connectionstyle="arc3,rad=.3",
                                                arrowstyle='->',
                                                color='red', alpha=0.5)
                ax1.add_patch(circle)
    
    # Column shape
    column = patches.Rectangle((-column_width/2, 0), column_width, column_height,
                              linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd', alpha=0.7)
    ax1.add_patch(column)
    
    # Load arrow
    arrow_props = dict(arrowstyle='->', lw=3, color='red')
    ax1.annotate('', xy=(0, column_height), xytext=(0, column_height + 0.5),
                arrowprops=arrow_props)
    ax1.text(0, column_height + 0.7, f'P = {P:.1f} t', ha='center', fontsize=14, 
            fontweight='bold', color='red')
    
    # Base support
    base_width = column_width * 1.5
    base = patches.Rectangle((-base_width/2, -0.1), base_width, 0.1,
                            linewidth=2, edgecolor='black', facecolor='gray')
    ax1.add_patch(base)
    
    # Ground hatching
    for i in range(5):
        x = -base_width/2 - 0.1 + i * (base_width + 0.2) / 4
        ax1.plot([x, x - 0.05], [-0.1, -0.2], 'k-', lw=1)
    
    ax1.set_xlim([-1, 1])
    ax1.set_ylim([-0.3, 4])
    ax1.set_aspect('equal')
    ax1.axis('off')
    if buckling_mode == "Flexural":
        ax1.legend(loc='upper right')
    
    # Stress distribution
    ax2.set_title('Stress Distribution', fontsize=12, fontweight='bold')
    ax2.barh([0], [1], height=3, color='#ff5252', alpha=0.7, label=f'σ = P/A')
    ax2.set_ylim([-0.5, 3.5])
    ax2.set_xlabel('Normalized Stress', fontsize=11)
    ax2.set_yticks([])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

def compression_analysis_advanced(df, df_mat, section, material, KLx, KLy, Kz=None, Lz=None):
    """
    Advanced compression member analysis including flexural-torsional buckling
    Kz: Effective length factor for torsional buckling
    Lz: Unbraced length for torsional buckling
    """
    try:
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        G = E / (2 * (1 + 0.3))  # Shear modulus (Poisson's ratio = 0.3)
        
        # Section properties
        Ag = float(df.loc[section, 'A [cm2]'])
        rx = float(df.loc[section, 'rx [cm]'])
        ry = float(df.loc[section, 'ry [cm]'])
        
        # Try to get additional properties for torsional buckling
        try:
            J = float(df.loc[section, 'j [cm4]']) if 'j [cm4]' in df.columns else 0
            Cw = float(df.loc[section, 'Cw [cm6]']) if 'Cw [cm6]' in df.columns else 0
            xo = float(df.loc[section, 'xo [cm]']) if 'xo [cm]' in df.columns else 0
            yo = float(df.loc[section, 'yo [cm]']) if 'yo [cm]' in df.columns else 0
            Ix = float(df.loc[section, 'Ix [cm4]'])
            Iy = float(df.loc[section, 'Iy [cm4]'])
        except:
            J = 0
            Cw = 0
            xo = 0
            yo = 0
            Ix = float(df.loc[section, 'Ix [cm4]'])
            Iy = float(df.loc[section, 'Iy [cm4]'])
        
        # Polar radius of gyration
        ro_squared = rx**2 + ry**2 + xo**2 + yo**2
        
        # Slenderness ratios for flexural buckling
        lambda_x = (KLx * 100) / rx
        lambda_y = (KLy * 100) / ry
        lambda_max_flexural = max(lambda_x, lambda_y)
        
        # Elastic flexural buckling stresses
        Fex = (mt.pi**2 * E) / (lambda_x**2)
        Fey = (mt.pi**2 * E) / (lambda_y**2)
        Fe_flexural = min(Fex, Fey)
        
        # Check for flexural-torsional buckling (for doubly symmetric sections)
        buckling_mode = "Flexural"
        Fe = Fe_flexural
        
        if J > 0 and Cw > 0 and Kz and Lz:
            # Torsional buckling stress
            KzLz = Kz * Lz * 100  # Convert to cm
            Fez = ((mt.pi**2 * E * Cw) / (KzLz**2) + G * J) / (Ag * ro_squared)
            
            # For doubly symmetric sections (xo = yo = 0)
            if xo == 0 and yo == 0:
                # Flexural-torsional buckling doesn't apply
                Fe = min(Fex, Fey, Fez)
                if Fez < Fe_flexural:
                    buckling_mode = "Torsional"
            else:
                # For singly symmetric sections
                # Solve cubic equation for flexural-torsional buckling
                H = 1 - (xo**2 + yo**2) / ro_squared
                
                # Simplified approach - take minimum
                Fe_ft = min(Fey, (Fex + Fez) / (2 * H) * 
                          (1 - mt.sqrt(1 - (4 * Fex * Fez * H) / ((Fex + Fez)**2))))
                
                Fe = min(Fe_flexural, Fe_ft)
                if Fe_ft < Fe_flexural:
                    buckling_mode = "Flexural-Torsional"
        
        # Critical slenderness
        lambda_c = mt.pi * mt.sqrt(E / Fy)
        
        # Effective slenderness for comparison
        lambda_eff = mt.pi * mt.sqrt(E / Fe)
        
        # Critical buckling stress (AISC 360 E3)
        if lambda_eff <= lambda_c:
            Fcr = Fy * (0.658**(Fy/Fe))
        else:
            Fcr = 0.877 * Fe
        
        # Check for local buckling (slender elements)
        Q = 1.0  # Reduction factor
        # Simplified check - you can expand this
        lamf = float(df.loc[section, '0.5bf/tf']) if '0.5bf/tf' in df.columns else 0
        lamw = float(df.loc[section, 'h/tw']) if 'h/tw' in df.columns else 0
        
        lamf_limit = 0.56 * mt.sqrt(E / Fy)
        lamw_limit = 1.49 * mt.sqrt(E / Fy)
        
        if lamf > lamf_limit or lamw > lamw_limit:
            Q = 0.9  # Simplified - should calculate actual Q
            Fcr = Q * Fcr
        
        # Nominal compressive strength
        Pn = Fcr * Ag / 1000  # tons
        phi_c = 0.9
        phi_Pn = phi_c * Pn
        
        return {
            'Pn': Pn,
            'phi_Pn': phi_Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'Fex': Fex,
            'Fey': Fey,
            'Fez': Fez if 'Fez' in locals() else None,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_max': lambda_max_flexural,
            'lambda_c': lambda_c,
            'lambda_eff': lambda_eff,
            'Ag': Ag,
            'Q': Q,
            'buckling_mode': buckling_mode,
            'local_buckling': "Yes" if Q < 1.0 else "No"
        }
    except Exception as e:
        st.error(f"Error in compression analysis: {e}")
        return None

def flexural_analysis(df, df_mat, section, material, Lb):
    """Simplified flexural analysis function"""
    try:
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        
        # Section properties
        Zx = float(df.loc[section, 'Zx [cm3]'])
        Sx = float(df.loc[section, 'Sx [cm3]'])
        
        # Simplified analysis (you can add full F2 analysis here)
        Mp = Fy * Zx / 100000  # t·m
        
        # Get Lp and Lr if available
        try:
            Lp = float(df.loc[section, "Lp [cm]"]) / 100  # m
            Lr = float(df.loc[section, "Lr [cm]"]) / 100  # m
        except:
            # Approximate if not available
            ry = float(df.loc[section, 'ry [cm]'])
            Lp = 1.76 * ry * mt.sqrt(E/Fy) / 100
            Lr = 1.95 * ry * mt.sqrt(E/(0.7*Fy)) / 100
        
        # Determine Mn based on Lb
        if Lb <= Lp:
            Mn = Mp
            case = "Plastic (Lb ≤ Lp)"
        elif Lb <= Lr:
            Mn = Mp - (Mp - 0.7*Fy*Sx/100000) * ((Lb - Lp)/(Lr - Lp))
            Mn = min(Mp, Mn)
            case = "Inelastic LTB (Lp < Lb ≤ Lr)"
        else:
            # Simplified elastic LTB
            Mn = 0.7 * Fy * Sx / 100000
            case = "Elastic LTB (Lb > Lr)"
        
        phi_b = 0.9
        phi_Mn = phi_b * Mn
        
        return {
            'Mp': Mp,
            'Mn': Mn,
            'phi_Mn': phi_Mn,
            'Lp': Lp,
            'Lr': Lr,
            'case': case
        }
    except Exception as e:
        st.error(f"Error in flexural analysis: {e}")
        return None

def create_multi_section_plot(df, df_mat, sections, material, Lb_values):
    """Create multi-section moment capacity plot"""
    fig = go.Figure()
    colors = ['#2196f3', '#4caf50', '#ff9800', '#f44336', '#9c27b0', '#00bcd4']
    
    for i, section in enumerate(sections):
        if section not in df.index:
            continue
        
        # Create Lb range
        Lb_range = np.linspace(0.1, 15, 100)
        Mn_values = []
        
        for lb in Lb_range:
            result = flexural_analysis(df, df_mat, section, material, lb)
            if result:
                Mn_values.append(result['Mn'])
            else:
                Mn_values.append(0)
        
        color = colors[i % len(colors)]
        
        # Add capacity curve
        fig.add_trace(go.Scatter(
            x=Lb_range, y=Mn_values,
            mode='lines',
            name=f'{section}',
            line=dict(color=color, width=2),
            hovertemplate='%{y:.2f} t·m @ Lb=%{x:.1f}m<extra></extra>'
        ))
        
        # Add current point
        current_lb = Lb_values.get(section, 3.0)
        current_result = flexural_analysis(df, df_mat, section, material, current_lb)
        if current_result:
            fig.add_trace(go.Scatter(
                x=[current_lb], y=[current_result['Mn']],
                mode='markers',
                name=f'{section} (current)',
                marker=dict(color=color, size=10, symbol='diamond'),
                showlegend=False,
                hovertemplate=f'{section}<br>Lb: {current_lb:.1f}m<br>Mn: {current_result["Mn"]:.2f} t·m<extra></extra>'
            ))
    
    fig.update_layout(
        title="Multi-Section Moment Capacity Comparison",
        xaxis_title="Unbraced Length, Lb (m)",
        yaxis_title="Nominal Moment, Mn (t·m)",
        height=500,
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

# ==================== LOAD DATA ====================
df, df_mat, success = load_data()

if not success:
    st.error("❌ Failed to load data. Please check your internet connection.")
    st.stop()

# ==================== MAIN HEADER ====================
st.markdown('<h1 style="text-align: center; color: #1a237e;">🏗️ Steel Design Analysis System</h1>', 
           unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84; font-size: 1.1rem;">AISC 360-16 Specification for Structural Steel Buildings</p>', 
           unsafe_allow_html=True)

# ==================== SIDEBAR CONFIGURATION ====================
with st.sidebar:
    st.markdown("### ⚙️ Design Configuration")
    
    # Material selection
    st.markdown("#### 📦 Material Properties")
    material_list = list(df_mat.index)
    selected_material = st.selectbox(
        "Steel Grade:",
        material_list,
        index=0,
        help="Select steel material grade"
    )
    st.session_state.selected_material = selected_material
    
    # Display material properties
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
    
    # Quick section selection
    st.markdown("#### 🔍 Quick Section Search")
    section_list = list(df.index)
    quick_section = st.selectbox(
        "Select Section:",
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
        - Ix: {df.loc[quick_section, 'Ix [cm4]']:.0f} cm⁴
        """)

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📚 Section Database",
    "🔍 Section Selection",
    "🏢 Flexural Design",
    "⚡ Compression Design",
    "🏗️ Beam-Column",
    "📊 Comparison"
])

# ==================== TAB 1: SECTION DATABASE ====================
with tab1:
    st.markdown('<h2 class="section-header">Section Database Explorer</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Section search
        search_section = st.text_input("🔍 Search section by name:", placeholder="e.g., H-200x200")
        
        if search_section:
            matching_sections = [s for s in section_list if search_section.upper() in s.upper()]
            if matching_sections:
                selected_display = st.selectbox("Select from matches:", matching_sections)
                st.session_state.selected_section = selected_display
            else:
                st.warning("No matching sections found")
        
        # Display section properties
        if st.session_state.selected_section:
            section = st.session_state.selected_section
            st.markdown(f"### Properties of {section}")
            
            # Key properties in a clean format
            props = {
                "Depth (d)": f"{df.loc[section, 'd [mm]']:.0f} mm",
                "Width (bf)": f"{df.loc[section, 'bf [mm]']:.0f} mm",
                "Web thickness (tw)": f"{df.loc[section, 'tw [mm]']:.1f} mm",
                "Flange thickness (tf)": f"{df.loc[section, 'tf [mm]']:.1f} mm",
                "Area (A)": f"{df.loc[section, 'A [cm2]']:.2f} cm²",
                "Weight": f"{df.loc[section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in df.columns else df.loc[section, 'w [kg/m]']:.1f} kg/m",
                "Ix": f"{df.loc[section, 'Ix [cm4]']:.0f} cm⁴",
                "Zx": f"{df.loc[section, 'Zx [cm3]']:.0f} cm³",
                "rx": f"{df.loc[section, 'rx [cm]']:.2f} cm",
                "ry": f"{df.loc[section, 'ry [cm]']:.2f} cm"
            }
            
            for prop, value in props.items():
                col_prop, col_val = st.columns([2, 1])
                with col_prop:
                    st.write(prop)
                with col_val:
                    st.write(f"**{value}**")
    
    with col2:
        # Section visualization
        if st.session_state.selected_section:
            section = st.session_state.selected_section
            st.markdown(f"### Cross-Section: {section}")
            
            # Create figure
            fig, ax = plt.subplots(figsize=(8, 8))
            
            # Get dimensions
            bf = float(df.loc[section, 'bf [mm]'])
            d = float(df.loc[section, 'd [mm]'])
            tw = float(df.loc[section, 'tw [mm]'])
            tf = float(df.loc[section, 'tf [mm]'])
            
            # Draw H-section
            # Top flange
            top_flange = patches.Rectangle((-bf/2, d/2 - tf), bf, tf,
                                          linewidth=2, edgecolor='#1a237e', 
                                          facecolor='#bbdefb', alpha=0.8)
            # Bottom flange
            bottom_flange = patches.Rectangle((-bf/2, -d/2), bf, tf,
                                             linewidth=2, edgecolor='#1a237e',
                                             facecolor='#bbdefb', alpha=0.8)
            # Web
            web = patches.Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf,
                                   linewidth=2, edgecolor='#1a237e',
                                   facecolor='#90caf9', alpha=0.8)
            
            ax.add_patch(top_flange)
            ax.add_patch(bottom_flange)
            ax.add_patch(web)
            
            # Add dimensions
            ax.annotate('', xy=(bf/2, d/2), xytext=(-bf/2, d/2),
                       arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
            ax.text(0, d/2 + 10, f'{bf:.0f} mm', ha='center', color='red', fontsize=10)
            
            ax.annotate('', xy=(bf/2 + 20, d/2), xytext=(bf/2 + 20, -d/2),
                       arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
            ax.text(bf/2 + 40, 0, f'{d:.0f} mm', ha='center', rotation=90, color='red', fontsize=10)
            
            # Axes
            ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
            ax.axvline(x=0, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
            
            ax.set_xlim([-bf, bf])
            ax.set_ylim([-d, d])
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            ax.set_xlabel('Width (mm)')
            ax.set_ylabel('Height (mm)')
            
            st.pyplot(fig)

# ==================== TAB 2: SECTION SELECTION WITH MULTI-SELECT ====================
with tab2:
    st.markdown('<h2 class="section-header">Intelligent Section Selection Tool</h2>', unsafe_allow_html=True)
    
    # Design requirements input
    st.markdown("### 📐 Design Requirements")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Moment Design")
        Mu = st.number_input("Design Moment Mu (kN·m):", min_value=0.0, value=500.0, step=50.0)
        phi = st.selectbox("Resistance Factor φ:", [0.9, 0.85, 0.75], index=0)
        
        # Calculate required Zx
        if Mu > 0:
            required_zx = calculate_required_properties(Mu, phi)
            st.markdown("**Required Zx (cm³):**")
            for grade, zx in required_zx.items():
                if grade == selected_material:
                    st.success(f"{grade}: **{zx:.0f} cm³** ✓")
                else:
                    st.info(f"{grade}: {zx:.0f} cm³")
    
    with col2:
        st.markdown("#### Deflection Control")
        L_span = st.number_input("Span Length L (m):", min_value=1.0, value=6.0, step=0.5)
        w_load = st.number_input("Service Load w (kN/m):", min_value=0.0, value=10.0, step=1.0)
        deflection_limit = st.selectbox("Deflection Limit:", 
                                       ["L/200", "L/250", "L/300", "L/360", "L/400"],
                                       index=2)
        
        # Calculate required Ix
        if w_load > 0 and L_span > 0:
            limit_value = float(deflection_limit.split('/')[1])
            Ix_req = calculate_required_ix(w_load, L_span, limit_value)
            st.success(f"**Required Ix: {Ix_req:.0f} cm⁴**")
    
    with col3:
        st.markdown("#### Additional Filters")
        depth_max = st.number_input("Max Depth (mm):", min_value=0, value=0, step=50,
                                   help="Enter 0 for no limit")
        weight_max = st.number_input("Max Weight (kg/m):", min_value=0, value=200, step=10,
                                    help="Enter 0 for no limit")
        
        # Preference
        optimization = st.selectbox("Optimize for:",
                                   ["Minimum Weight", "Minimum Depth", "Maximum Efficiency"],
                                   index=0)
    
    st.markdown("---")
    
    # Apply filters automatically
    filtered_df = df.copy()
    
    # Filter by required Zx
    if Mu > 0 and selected_material in calculate_required_properties(Mu, phi):
        zx_min = calculate_required_properties(Mu, phi)[selected_material]
        filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= zx_min]
    
    # Filter by required Ix
    if w_load > 0 and L_span > 0:
        limit_value = float(deflection_limit.split('/')[1])
        Ix_req = calculate_required_ix(w_load, L_span, limit_value)
        filtered_df = filtered_df[filtered_df['Ix [cm4]'] >= Ix_req]
    
    # Filter by depth
    if depth_max > 0:
        filtered_df = filtered_df[filtered_df['d [mm]'] <= depth_max]
    
    # Filter by weight
    if weight_max > 0:
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df = filtered_df[filtered_df[weight_col] <= weight_max]
    
    # Sort by optimization criteria
    if optimization == "Minimum Weight":
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df = filtered_df.sort_values(weight_col)
    elif optimization == "Minimum Depth":
        filtered_df = filtered_df.sort_values('d [mm]')
    else:  # Maximum Efficiency
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
        filtered_df['efficiency'] = filtered_df['Zx [cm3]'] / filtered_df[weight_col]
        filtered_df = filtered_df.sort_values('efficiency', ascending=False)
    
    # Display results with AgGrid for multi-selection
    st.markdown(f"### ✅ Found {len(filtered_df)} Suitable Sections")
    
    if len(filtered_df) > 0:
        # Reset index to make Section a column
        filtered_df_display = filtered_df.reset_index()
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(filtered_df_display)
        gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=False, groupSelectsFiltered=True)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        gb.configure_column("Section", headerCheckboxSelection=True)
        
        # Format columns
        weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df_display.columns else 'w [kg/m]'
        display_cols = ['Section', 'd [mm]', 'bf [mm]', weight_col, 'A [cm2]', 
                       'Ix [cm4]', 'Zx [cm3]', 'Sx [cm3]', 'rx [cm]', 'ry [cm]']
        available_cols = [col for col in display_cols if col in filtered_df_display.columns]
        
        grid_options = gb.build()
        
        # Display grid
        grid_response = AgGrid(
            filtered_df_display[available_cols],
            gridOptions=grid_options,
            height=400,
            width='100%',
            theme='streamlit',
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            allow_unsafe_jscode=True,
            enable_enterprise_modules=False
        )
        
        # Handle selected rows
        selected_rows = grid_response['selected_rows']
        
        if selected_rows is not None and len(selected_rows) > 0:
            selected_df = pd.DataFrame(selected_rows)
            st.session_state.selected_sections = selected_df['Section'].tolist()
            
            st.success(f"✅ Selected {len(selected_rows)} sections for analysis")
            
            # Show selected sections with individual Lb values
            with st.expander("📋 Selected Sections Configuration", expanded=True):
                st.markdown("#### Configure Unbraced Length for Each Section")
                
                use_global_lb = st.checkbox("Use same Lb for all sections", value=False)
                
                if use_global_lb:
                    global_lb = st.slider("Global Unbraced Length (m):", 0.0, 20.0, 3.0, 0.5)
                    for section_name in st.session_state.selected_sections:
                        st.session_state.section_lb_values[section_name] = global_lb
                else:
                    col_sec1, col_sec2 = st.columns(2)
                    for i, section_name in enumerate(st.session_state.selected_sections):
                        with col_sec1 if i % 2 == 0 else col_sec2:
                            lb_value = st.number_input(
                                f"Lb for {section_name} (m):", 
                                min_value=0.0, 
                                value=st.session_state.section_lb_values.get(section_name, 3.0),
                                step=0.5,
                                key=f"lb_{section_name}"
                            )
                            st.session_state.section_lb_values[section_name] = lb_value
                
                # Display summary table
                if st.session_state.selected_sections:
                    summary_data = []
                    for section_name in st.session_state.selected_sections:
                        weight = df.loc[section_name, weight_col] if section_name in df.index else 0
                        summary_data.append({
                            'Section': section_name,
                            'Weight': f"{weight:.1f} kg/m",
                            'Zx': f"{df.loc[section_name, 'Zx [cm3]']:.0f} cm³",
                            'Ix': f"{df.loc[section_name, 'Ix [cm4]']:.0f} cm⁴",
                            'Lb': f"{st.session_state.section_lb_values.get(section_name, 3.0):.1f} m"
                        })
                    
                    st.markdown("#### Summary of Selected Sections")
                    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    else:
        st.warning("No sections meet the specified criteria. Try adjusting your requirements.")

# ==================== TAB 3: FLEXURAL DESIGN ====================
with tab3:
    st.markdown('<h2 class="section-header">Flexural Member Design (Chapter F)</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and st.session_state.selected_material:
        section = st.session_state.selected_section
        material = st.session_state.selected_material
        
        st.info(f"**Analyzing:** {section} | **Material:** {material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Design Parameters")
            
            # Interactive unbraced length input
            Lb = st.slider("Unbraced Length Lb (m):", 
                          min_value=0.1, max_value=20.0, value=3.0, step=0.1)
            
            # Moment modification factor
            Cb = st.number_input("Moment Factor Cb:", 
                               min_value=1.0, value=1.0, max_value=3.0, step=0.1,
                               help="1.0 for uniform moment, up to 2.3 for single curvature")
            
            # Load case
            load_case = st.selectbox("Load Case:",
                                    ["Uniform Load", "Point Load at Center", "End Moments"])
        
        # Real-time analysis
        results = flexural_analysis(df, df_mat, section, material, Lb)
        
        if results:
            st.markdown("### 📊 Analysis Results")
            
            # Display results in metrics
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("φMn", f"{results['phi_Mn']:.2f} t·m", 
                        delta=f"Mn = {results['Mn']:.2f} t·m")
            
            with col_r2:
                st.metric("Mp", f"{results['Mp']:.2f} t·m",
                        delta=f"Plastic Capacity")
            
            with col_r3:
                utilization = (results['Mn'] / results['Mp']) * 100
                st.metric("Utilization", f"{utilization:.1f}%",
                        delta=results['case'])
            
            # Classification
            if utilization >= 90:
                st.markdown('<div class="success-box">✅ <b>Compact Section - Full Plastic Capacity</b></div>', 
                          unsafe_allow_html=True)
            elif utilization >= 70:
                st.markdown('<div class="warning-box">⚠️ <b>Lateral-Torsional Buckling Controls</b></div>', 
                          unsafe_allow_html=True)
            else:
                st.markdown('<div class="error-box">❌ <b>Significant Capacity Reduction - Consider Reducing Lb</b></div>', 
                          unsafe_allow_html=True)
            
            # Critical lengths
            st.markdown("### Critical Lengths")
            col_l1, col_l2, col_l3 = st.columns(3)
            
            with col_l1:
                st.write(f"**Lp = {results['Lp']:.2f} m**")
                st.caption("Compact limit")
            
            with col_l2:
                st.write(f"**Lr = {results['Lr']:.2f} m**")
                st.caption("Inelastic limit")
            
            with col_l3:
                st.write(f"**Lb = {Lb:.2f} m**")
                st.caption("Actual unbraced")
        
        with col2:
            st.markdown("### Moment Capacity Diagram")
            
            # Create Mn vs Lb plot
            Lb_range = np.linspace(0, 15, 100)
            Mn_values = []
            
            for lb in Lb_range:
                result = flexural_analysis(df, df_mat, section, material, lb)
                if result:
                    Mn_values.append(result['Mn'])
                else:
                    Mn_values.append(0)
            
            if results:
                fig = go.Figure()
                
                # Main curve
                fig.add_trace(go.Scatter(
                    x=Lb_range, y=Mn_values,
                    mode='lines',
                    name='Mn',
                    line=dict(color='#1976d2', width=3),
                    hovertemplate='Lb: %{x:.1f} m<br>Mn: %{y:.2f} t·m<extra></extra>'
                ))
                
                # Current point
                fig.add_trace(go.Scatter(
                    x=[Lb], y=[results['Mn']],
                    mode='markers',
                    name='Current Design',
                    marker=dict(color='#f44336', size=12, symbol='star'),
                    hovertemplate=f'Lb: {Lb:.1f} m<br>Mn: {results["Mn"]:.2f} t·m<extra></extra>'
                ))
                
                # Add Lp and Lr lines
                fig.add_vline(x=results['Lp'], line_dash="dash", line_color="#4caf50",
                            annotation_text=f"Lp = {results['Lp']:.1f} m")
                fig.add_vline(x=results['Lr'], line_dash="dash", line_color="#ff9800",
                            annotation_text=f"Lr = {results['Lr']:.1f} m")
                
                # Add Mp line
                fig.add_hline(y=results['Mp'], line_dash="dot", line_color="#9c27b0",
                            annotation_text=f"Mp = {results['Mp']:.1f} t·m")
                
                # Add zones
                fig.add_vrect(x0=0, x1=results['Lp'],
                            fillcolor="#4caf50", opacity=0.1,
                            annotation_text="Plastic", annotation_position="top left")
                fig.add_vrect(x0=results['Lp'], x1=results['Lr'],
                            fillcolor="#ff9800", opacity=0.1,
                            annotation_text="Inelastic LTB", annotation_position="top left")
                fig.add_vrect(x0=results['Lr'], x1=15,
                            fillcolor="#f44336", opacity=0.1,
                            annotation_text="Elastic LTB", annotation_position="top left")
                
                fig.update_layout(
                    title=f"Moment Capacity vs Unbraced Length - {section}",
                    xaxis_title="Unbraced Length, Lb (m)",
                    yaxis_title="Nominal Moment, Mn (t·m)",
                    height=500,
                    hovermode='closest',
                    showlegend=True,
                    template='plotly_white'
                )
                
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar or Section Selection tab.")

# ==================== TAB 4: COMPRESSION DESIGN WITH TORSIONAL BUCKLING ====================
with tab4:
    st.markdown('<h2 class="section-header">Compression Member Design (Chapter E) - Including Flexural-Torsional Buckling</h2>', 
               unsafe_allow_html=True)
    
    if st.session_state.selected_section and st.session_state.selected_material:
        section = st.session_state.selected_section
        material = st.session_state.selected_material
        
        st.info(f"**Analyzing:** {section} | **Material:** {material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Design Parameters")
            
            # Interactive effective length factors
            st.markdown("#### Effective Length Factors")
            col_k1, col_k2 = st.columns(2)
            
            with col_k1:
                end_condition_x = st.selectbox("X-axis End Condition:",
                    ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned", "Fixed-Free"],
                    index=0)
                K_factors = {"Pinned-Pinned": 1.0, "Fixed-Fixed": 0.5, 
                           "Fixed-Pinned": 0.7, "Fixed-Free": 2.0}
                Kx = K_factors[end_condition_x]
                st.caption(f"Kx = {Kx}")
            
            with col_k2:
                end_condition_y = st.selectbox("Y-axis End Condition:",
                    ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned", "Fixed-Free"],
                    index=0)
                Ky = K_factors[end_condition_y]
                st.caption(f"Ky = {Ky}")
            
            # Torsional buckling parameters
            st.markdown("#### Torsional Buckling")
            consider_torsional = st.checkbox("Consider Flexural-Torsional Buckling", value=True)
            
            if consider_torsional:
                end_condition_z = st.selectbox("Torsional End Condition:",
                    ["Pinned-Pinned", "Fixed-Fixed", "Fixed-Pinned"],
                    index=0)
                Kz = K_factors.get(end_condition_z, 1.0)
                st.caption(f"Kz = {Kz}")
            else:
                Kz = None
            
            # Interactive unbraced lengths
            st.markdown("#### Unbraced Lengths")
            Lx = st.slider("Lx (m):", min_value=0.1, max_value=20.0, value=3.0, step=0.1)
            Ly = st.slider("Ly (m):", min_value=0.1, max_value=20.0, value=3.0, step=0.1)
            
            if consider_torsional:
                Lz = st.slider("Lz for torsion (m):", min_value=0.1, max_value=20.0, value=3.0, step=0.1)
            else:
                Lz = None
            
            # Calculate effective lengths
            KLx = Kx * Lx
            KLy = Ky * Ly
            
            col_kl1, col_kl2 = st.columns(2)
            with col_kl1:
                st.metric("KLx", f"{KLx:.2f} m")
            with col_kl2:
                st.metric("KLy", f"{KLy:.2f} m")
            
            # Applied load
            Pu = st.slider("Applied Axial Load Pu (tons):", 
                          min_value=0.0, max_value=500.0, value=100.0, step=5.0)
        
        # Real-time analysis
        results = compression_analysis_advanced(df, df_mat, section, material, KLx, KLy, Kz, Lz)
        
        if results:
            st.markdown("### 📊 Analysis Results")
            
            # Capacity check
            capacity_ratio = Pu / results['phi_Pn']
            
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("φPn", f"{results['phi_Pn']:.2f} tons",
                        delta=f"Pn = {results['Pn']:.2f} tons")
            
            with col_r2:
                st.metric("Demand/Capacity", f"{capacity_ratio:.3f}",
                        delta=f"Pu = {Pu:.2f} tons")
            
            with col_r3:
                safety_margin = (1 - capacity_ratio) * 100
                st.metric("Safety Margin", f"{safety_margin:.1f}%",
                        delta="SAFE" if capacity_ratio < 1.0 else "UNSAFE")
            
            # Pass/Fail indication
            if capacity_ratio <= 1.0:
                st.markdown(f'<div class="success-box">✅ <b>DESIGN PASSES</b> - Ratio: {capacity_ratio:.3f} ≤ 1.0</div>', 
                          unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="error-box">❌ <b>DESIGN FAILS</b> - Ratio: {capacity_ratio:.3f} > 1.0</div>', 
                          unsafe_allow_html=True)
            
            # Buckling mode indication
            st.markdown("### Buckling Analysis")
            col_b1, col_b2, col_b3 = st.columns(3)
            
            with col_b1:
                st.write(f"**Governing Mode:**")
                st.info(f"{results['buckling_mode']}")
            
            with col_b2:
                st.write(f"**Local Buckling:**")
                st.info(f"{results['local_buckling']}")
            
            with col_b3:
                st.write(f"**Q Factor:**")
                st.info(f"{results['Q']:.2f}")
            
            # Slenderness parameters
            st.markdown("### Slenderness & Critical Stresses")
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            
            with col_s1:
                st.write(f"**λx = {results['lambda_x']:.1f}**")
                st.caption(f"Fex = {results['Fex']:.0f} ksc")
            
            with col_s2:
                st.write(f"**λy = {results['lambda_y']:.1f}**")
                st.caption(f"Fey = {results['Fey']:.0f} ksc")
            
            with col_s3:
                st.write(f"**λeff = {results['lambda_eff']:.1f}**")
                st.caption(f"Fe = {results['Fe']:.0f} ksc")
            
            with col_s4:
                if results['Fez']:
                    st.write(f"**Torsional**")
                    st.caption(f"Fez = {results['Fez']:.0f} ksc")
                else:
                    st.write(f"**λc = {results['lambda_c']:.1f}**")
                    st.caption(f"Fcr = {results['Fcr']:.0f} ksc")
        
        with col2:
            st.markdown("### Column Visualization & Capacity Curves")
            
            # Visualization of column with load
            if st.session_state.selected_section and results:
                fig = visualize_column_with_load(Pu, section, results['buckling_mode'])
                st.pyplot(fig)
                
                # Create capacity curve
                st.markdown("### Compression Capacity vs Slenderness")
                
                # Generate curve data
                KL_r_range = np.linspace(10, 200, 100)
                Pn_flexural = []
                Pn_torsional = []
                
                for klr in KL_r_range:
                    Fe_temp = (mt.pi**2 * 2.04e6) / (klr**2)
                    Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
                    
                    if klr <= mt.pi * mt.sqrt(2.04e6 / Fy):
                        Fcr_temp = Fy * (0.658**(Fy/Fe_temp))
                    else:
                        Fcr_temp = 0.877 * Fe_temp
                    
                    Ag = float(df.loc[section, 'A [cm2]'])
                    Pn_temp = 0.9 * Fcr_temp * Ag / 1000
                    Pn_flexural.append(Pn_temp)
                
                # Plot
                fig2 = go.Figure()
                
                fig2.add_trace(go.Scatter(
                    x=KL_r_range, y=Pn_flexural,
                    mode='lines',
                    name='φPn (Flexural)',
                    line=dict(color='#2196f3', width=3),
                    hovertemplate='KL/r: %{x:.0f}<br>φPn: %{y:.1f} tons<extra></extra>'
                ))
                
                # Add current point
                fig2.add_trace(go.Scatter(
                    x=[results['lambda_max']], y=[results['phi_Pn']],
                    mode='markers',
                    name=f'Current ({results["buckling_mode"]})',
                    marker=dict(color='#f44336', size=12, symbol='star'),
                    hovertemplate=f'KL/r: {results["lambda_max"]:.1f}<br>φPn: {results["phi_Pn"]:.1f} tons<br>Mode: {results["buckling_mode"]}<extra></extra>'
                ))
                
                # Add demand line
                fig2.add_hline(y=Pu, line_dash="dash", line_color="#ff5722",
                             annotation_text=f"Pu = {Pu:.1f} tons")
                
                fig2.update_layout(
                    title=f"Compression Capacity - {section}",
                    xaxis_title="Slenderness Ratio (KL/r)",
                    yaxis_title="Design Capacity φPn (tons)",
                    height=400,
                    template='plotly_white',
                    hovermode='closest'
                )
                
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar or Section Selection tab.")

# ==================== TAB 5: BEAM-COLUMN ====================
with tab5:
    st.markdown('<h2 class="section-header">Beam-Column Interaction Design (Chapter H)</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and st.session_state.selected_material:
        section = st.session_state.selected_section
        material = st.session_state.selected_material
        
        st.info(f"**Analyzing:** {section} | **Material:** {material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Combined Loading")
            
            # Interactive loads
            Pu_bc = st.slider("Axial Load Pu (tons):", 
                             min_value=0.0, max_value=200.0, value=50.0, step=1.0)
            
            st.markdown("#### Applied Moments")
            Mux = st.slider("Moment Mux (t·m):", 
                           min_value=0.0, max_value=100.0, value=30.0, step=1.0,
                           help="Moment about strong axis")
            Muy = st.slider("Moment Muy (t·m):", 
                           min_value=0.0, max_value=50.0, value=5.0, step=0.5,
                           help="Moment about weak axis")
            
            # Effective lengths
            st.markdown("#### Effective Lengths")
            KLx_bc = st.slider("KLx (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            KLy_bc = st.slider("KLy (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
            Lb_bc = st.slider("Lb for LTB (m):", min_value=0.1, max_value=10.0, value=3.0, step=0.1)
        
        # Real-time analysis
        comp_results = compression_analysis_advanced(df, df_mat, section, material, KLx_bc, KLy_bc)
        flex_results = flexural_analysis(df, df_mat, section, material, Lb_bc)
        
        if comp_results and flex_results:
            # Calculate interaction ratios
            Pc = comp_results['phi_Pn']
            Mcx = flex_results['phi_Mn']
            
            # Simplified My calculation
            Zy = float(df.loc[section, 'Zy [cm3]'])
            Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
            Mcy = 0.9 * Fy * Zy / 100000  # t·m
            
            # Interaction check (H1-1)
            if Pu_bc/Pc >= 0.2:
                # H1-1a
                interaction = Pu_bc/Pc + (8/9)*(Mux/Mcx + Muy/Mcy)
                equation = "H1-1a"
            else:
                # H1-1b
                interaction = Pu_bc/(2*Pc) + (Mux/Mcx + Muy/Mcy)
                equation = "H1-1b"
            
            st.markdown("### 📊 Interaction Results")
            
            # Display results
            col_r1, col_r2, col_r3 = st.columns(3)
            
            with col_r1:
                st.metric("P/φPn", f"{Pu_bc/Pc:.3f}",
                        delta=f"{Pu_bc:.1f}/{Pc:.1f} tons")
            
            with col_r2:
                st.metric("Mx/φMnx", f"{Mux/Mcx:.3f}",
                        delta=f"{Mux:.1f}/{Mcx:.1f} t·m")
            
            with col_r3:
                st.metric("My/φMny", f"{Muy/Mcy:.3f}",
                        delta=f"{Muy:.1f}/{Mcy:.1f} t·m")
            
            # Unity check
            st.markdown("### Unity Check")
            st.metric("Interaction Ratio", f"{interaction:.3f}",
                    delta=f"Equation {equation}")
            
            if interaction <= 1.0:
                st.markdown(f'<div class="success-box">✅ <b>DESIGN PASSES</b> - Unity Check: {interaction:.3f} ≤ 1.0<br>Safety Margin: {(1-interaction)*100:.1f}%</div>', 
                          unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="error-box">❌ <b>DESIGN FAILS</b> - Unity Check: {interaction:.3f} > 1.0<br>Overstressed by: {(interaction-1)*100:.1f}%</div>', 
                          unsafe_allow_html=True)
        
        with col2:
            st.markdown("### P-M Interaction Diagram")
            
            if comp_results and flex_results:
                # Generate interaction curve
                P_ratios = np.linspace(0, 1, 50)
                M_ratios = []
                
                for p_ratio in P_ratios:
                    if p_ratio >= 0.2:
                        m_ratio = (9/8) * (1 - p_ratio)
                    else:
                        m_ratio = 1 - p_ratio/2
                    M_ratios.append(m_ratio)
                
                # Create plot
                fig = go.Figure()
                
                # Interaction curve
                fig.add_trace(go.Scatter(
                    x=M_ratios, y=P_ratios,
                    mode='lines',
                    name='Interaction Curve',
                    line=dict(color='#2196f3', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(33, 150, 243, 0.2)',
                    hovertemplate='M/Mc: %{x:.2f}<br>P/Pc: %{y:.2f}<extra></extra>'
                ))
                
                # Add design point
                M_combined = Mux/Mcx + Muy/Mcy
                P_ratio = Pu_bc/Pc
                
                fig.add_trace(go.Scatter(
                    x=[M_combined], y=[P_ratio],
                    mode='markers',
                    name='Design Point',
                    marker=dict(color='#f44336', size=15, symbol='star'),
                    hovertemplate=f'Design Point<br>P/Pc: {P_ratio:.3f}<br>ΣM/Mc: {M_combined:.3f}<br>Unity: {interaction:.3f}<extra></extra>'
                ))
                
                # Add safety indication
                if interaction <= 1.0:
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
                
                fig.update_layout(
                    title="P-M Interaction Diagram (Real-time)",
                    xaxis_title="Combined Moment Ratio (Mx/Mcx + My/Mcy)",
                    yaxis_title="Axial Force Ratio (P/Pc)",
                    height=500,
                    template='plotly_white',
                    hovermode='closest',
                    xaxis=dict(range=[0, 1.2]),
                    yaxis=dict(range=[0, 1.2])
                )
                
                # Add grid
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
                
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Please select a section and material from the sidebar or Section Selection tab.")

# ==================== TAB 6: COMPARISON ====================
with tab6:
    st.markdown('<h2 class="section-header">Multi-Section Comparison Tool</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_sections:
        st.info(f"Comparing {len(st.session_state.selected_sections)} sections")
        
        # Comparison parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            comparison_type = st.selectbox("Comparison Type:",
                ["Moment Capacity", "Compression Capacity", "Weight Efficiency", "Cost Analysis"])
        
        with col2:
            Lb_comp = st.slider("Unbraced Length for Flexure (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        with col3:
            KL_comp = st.slider("Effective Length for Compression (m):", 
                               min_value=0.1, max_value=20.0, value=3.0, step=0.1)
        
        # Real-time comparison
        comparison_data = []
        
        for section_name in st.session_state.selected_sections:
            if section_name not in df.index:
                continue
                
            # Get weight
            weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
            weight = df.loc[section_name, weight_col]
            
            # Flexural analysis
            flex_results = flexural_analysis(df, df_mat, section_name, st.session_state.selected_material, Lb_comp)
            
            # Compression analysis
            comp_results = compression_analysis_advanced(df, df_mat, section_name, st.session_state.selected_material, 
                                                        KL_comp, KL_comp)
            
            if flex_results and comp_results:
                comparison_data.append({
                    'Section': section_name,
                    'Weight (kg/m)': weight,
                    'φMn (t·m)': flex_results['phi_Mn'],
                    'φPn (tons)': comp_results['phi_Pn'],
                    'Moment Efficiency': flex_results['phi_Mn'] / weight,
                    'Compression Efficiency': comp_results['phi_Pn'] / weight,
                    'Buckling Mode': comp_results['buckling_mode']
                })
        
        if comparison_data:
            df_comparison = pd.DataFrame(comparison_data)
            
            # Display comparison chart based on type
            if comparison_type == "Moment Capacity":
                # Multi-section moment curves
                if st.session_state.section_lb_values:
                    st.markdown("### Multi-Section Moment Capacity Curves")
                    fig = create_multi_section_plot(df, df_mat, st.session_state.selected_sections, 
                                                   st.session_state.selected_material, 
                                                   st.session_state.section_lb_values)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Bar chart comparison at specific Lb
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['φMn (t·m)'],
                    text=[f'{v:.2f}' for v in df_comparison['φMn (t·m)']],
                    textposition='auto',
                    marker_color='#2196f3'
                ))
                fig_bar.update_layout(
                    title=f"Moment Capacity Comparison at Lb = {Lb_comp:.1f} m",
                    yaxis_title="φMn (t·m)",
                    template='plotly_white'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
            elif comparison_type == "Compression Capacity":
                fig = go.Figure()
                
                # Group by buckling mode
                colors = {'Flexural': '#2196f3', 'Torsional': '#ff9800', 'Flexural-Torsional': '#f44336'}
                
                for mode in df_comparison['Buckling Mode'].unique():
                    df_mode = df_comparison[df_comparison['Buckling Mode'] == mode]
                    fig.add_trace(go.Bar(
                        x=df_mode['Section'],
                        y=df_mode['φPn (tons)'],
                        name=mode,
                        text=[f'{v:.1f}' for v in df_mode['φPn (tons)']],
                        textposition='auto',
                        marker_color=colors.get(mode, '#9e9e9e')
                    ))
                
                fig.update_layout(
                    title=f"Compression Capacity Comparison at KL = {KL_comp:.1f} m",
                    yaxis_title="φPn (tons)",
                    barmode='group',
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
            elif comparison_type == "Weight Efficiency":
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Moment Efficiency'],
                    name='Moment Efficiency (t·m/kg/m)',
                    marker_color='#2196f3'
                ))
                
                fig.add_trace(go.Bar(
                    x=df_comparison['Section'],
                    y=df_comparison['Compression Efficiency'],
                    name='Compression Efficiency (tons/kg/m)',
                    marker_color='#4caf50'
                ))
                
                fig.update_layout(
                    title="Weight Efficiency Comparison",
                    yaxis_title="Efficiency (Capacity/Weight)",
                    barmode='group',
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Display comparison table
            st.markdown("### 📊 Detailed Comparison Table")
            
            # Format the dataframe for display
            df_display = df_comparison.copy()
            df_display['Weight (kg/m)'] = df_display['Weight (kg/m)'].round(1)
            df_display['φMn (t·m)'] = df_display['φMn (t·m)'].round(2)
            df_display['φPn (tons)'] = df_display['φPn (tons)'].round(1)
            df_display['Moment Efficiency'] = df_display['Moment Efficiency'].round(3)
            df_display['Compression Efficiency'] = df_display['Compression Efficiency'].round(3)
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            # Best section recommendation
            st.markdown("### 🏆 Recommendations")
            
            col_rec1, col_rec2, col_rec3 = st.columns(3)
            
            with col_rec1:
                best_moment = df_comparison.loc[df_comparison['φMn (t·m)'].idxmax()]
                st.markdown(f'''<div class="info-box">
                <b>Highest Moment Capacity:</b><br>
                {best_moment["Section"]}<br>
                φMn: {best_moment["φMn (t·m)"]:.2f} t·m
                </div>''', unsafe_allow_html=True)
            
            with col_rec2:
                best_compression = df_comparison.loc[df_comparison['φPn (tons)'].idxmax()]
                st.markdown(f'''<div class="info-box">
                <b>Highest Compression Capacity:</b><br>
                {best_compression["Section"]}<br>
                φPn: {best_compression["φPn (tons)"]:.1f} tons
                </div>''', unsafe_allow_html=True)
            
            with col_rec3:
                best_efficiency = df_comparison.loc[df_comparison['Moment Efficiency'].idxmax()]
                st.markdown(f'''<div class="info-box">
                <b>Most Efficient (Flexure):</b><br>
                {best_efficiency["Section"]}<br>
                Efficiency: {best_efficiency["Moment Efficiency"]:.3f}
                </div>''', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Please select sections from the 'Section Selection' tab first.")
        st.markdown("""
        ### 📖 How to Use Comparison Tool:
        1. Go to **Section Selection** tab
        2. Input your design requirements
        3. Select multiple sections from the table using checkboxes
        4. Configure individual Lb values if needed
        5. Return here to compare selected sections
        
        This tool provides:
        - Real-time interactive comparison
        - Multiple analysis types
        - Automatic best section recommendations
        - Detailed performance metrics
        """)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><b>Steel Design Analysis System v3.1</b></p>
    <p>Real-time Interactive Analysis | Multi-Section Selection | Flexural-Torsional Buckling</p>
    <p>Based on AISC 360-16 Specification | Developed with Streamlit</p>
    <p>© 2024 - Educational Tool for Structural Engineers</p>
</div>
""", unsafe_allow_html=True)
