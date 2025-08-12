# ==================== IMPROVED STEEL DESIGN ANALYSIS APPLICATION ====================
# Version: 3.0 - Simplified UI/UX with Enhanced Functionality
# GitHub: Thana-site/Steel_Design_2003

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import math as mt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid, GridOptionsBuilder
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
    
    /* Improved button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: 600;
        border-radius: 25px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
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
if 'filtered_sections' not in st.session_state:
    st.session_state.filtered_sections = []

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

def visualize_column_with_load(P, section_name):
    """Create visualization of column with axial load"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Column elevation view
    ax1.set_title(f'Column: {section_name}\nAxial Load P = {P:.1f} tons', fontsize=12, fontweight='bold')
    
    # Draw column
    column_width = 0.3
    column_height = 3.0
    
    # Column shape
    column = patches.Rectangle((-column_width/2, 0), column_width, column_height,
                              linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd')
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

def compression_analysis(df, df_mat, section, material, KLx, KLy):
    """Perform compression member analysis"""
    try:
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        
        # Section properties
        Ag = float(df.loc[section, 'A [cm2]'])
        rx = float(df.loc[section, 'rx [cm]'])
        ry = float(df.loc[section, 'ry [cm]'])
        
        # Slenderness ratios
        lambda_x = (KLx * 100) / rx
        lambda_y = (KLy * 100) / ry
        lambda_max = max(lambda_x, lambda_y)
        
        # Critical slenderness
        lambda_c = mt.pi * mt.sqrt(E / Fy)
        
        # Elastic buckling stress
        Fe = (mt.pi**2 * E) / (lambda_max**2)
        
        # Critical buckling stress (AISC 360 E3)
        if lambda_max <= lambda_c:
            Fcr = Fy * (0.658**(Fy/Fe))
        else:
            Fcr = 0.877 * Fe
        
        # Nominal compressive strength
        Pn = Fcr * Ag / 1000  # tons
        phi_c = 0.9
        phi_Pn = phi_c * Pn
        
        return {
            'Pn': Pn,
            'phi_Pn': phi_Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_max': lambda_max,
            'lambda_c': lambda_c,
            'Ag': Ag
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

# ==================== LOAD DATA ====================
df, df_mat, success = load_data()

if not success:
    st.error("❌ Failed to load data. Please check your internet connection.")
    st.stop()

# ==================== MAIN HEADER ====================
st.markdown('<h1 style="text-align: center; color: #1a237e;">🏗️ Steel Design Analysis System</h1>', 
           unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #5e6c84; font-size: 1.1rem;">AISC 360 Specification for Structural Steel Buildings</p>', 
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

# ==================== TAB 2: SECTION SELECTION ====================
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
    
    # Filter and display results
    if st.button("🔍 Find Suitable Sections", type="primary"):
        with st.spinner("Analyzing sections..."):
            # Apply filters
            filtered_df = df.copy()
            
            # Filter by required Zx
            if Mu > 0 and selected_material in required_zx:
                zx_min = required_zx[selected_material]
                filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= zx_min]
            
            # Filter by required Ix
            if w_load > 0 and L_span > 0:
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
            
            # Display results
            st.markdown(f"### ✅ Found {len(filtered_df)} Suitable Sections")
            
            if len(filtered_df) > 0:
                # Show top 5 recommendations
                st.markdown("#### 🏆 Top 5 Recommendations")
                
                for i, (idx, row) in enumerate(filtered_df.head(5).iterrows(), 1):
                    weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in df.columns else 'w [kg/m]'
                    
                    col_rank, col_section, col_props, col_select = st.columns([0.5, 2, 3, 1])
                    
                    with col_rank:
                        if i == 1:
                            st.markdown(f"**🥇 #{i}**")
                        elif i == 2:
                            st.markdown(f"**🥈 #{i}**")
                        elif i == 3:
                            st.markdown(f"**🥉 #{i}**")
                        else:
                            st.markdown(f"**#{i}**")
                    
                    with col_section:
                        st.markdown(f"**{idx}**")
                    
                    with col_props:
                        st.write(f"Weight: {row[weight_col]:.1f} kg/m | "
                                f"Zx: {row['Zx [cm3]']:.0f} cm³ | "
                                f"Ix: {row['Ix [cm4]']:.0f} cm⁴ | "
                                f"d: {row['d [mm]']:.0f} mm")
                    
                    with col_select:
                        if st.button(f"Select", key=f"select_{idx}"):
                            st.session_state.selected_section = idx
                            st.success(f"Selected {idx}")
                
                # Show all results in expandable section
                with st.expander("📋 View All Results"):
                    display_cols = ['d [mm]', 'bf [mm]', weight_col, 'A [cm2]', 
                                  'Ix [cm4]', 'Zx [cm3]', 'Sx [cm3]', 'rx [cm]', 'ry [cm]']
                    available_cols = [col for col in display_cols if col in filtered_df.columns]
                    st.dataframe(filtered_df[available_cols].round(2), use_container_width=True)
                
                st.session_state.filtered_sections = filtered_df.index.tolist()
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
            
            # Unbraced length input
            Lb = st.number_input("Unbraced Length Lb (m):", 
                               min_value=0.1, value=3.0, max_value=20.0, step=0.5)
            
            # Moment modification factor
            Cb = st.number_input("Moment Factor Cb:", 
                               min_value=1.0, value=1.0, max_value=3.0, step=0.1,
                               help="1.0 for uniform moment, up to 2.3 for single curvature")
            
            # Load case
            load_case = st.selectbox("Load Case:",
                                    ["Uniform Load", "Point Load at Center", "End Moments"])
            
            # Perform analysis
            if st.button("Analyze Flexural Capacity", type="primary"):
                with st.spinner("Calculating..."):
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
            
            # Get key points
            result_current = flexural_analysis(df, df_mat, section, material, Lb)
            
            if result_current:
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
                    x=[Lb], y=[result_current['Mn']],
                    mode='markers',
                    name='Current Design',
                    marker=dict(color='#f44336', size=12, symbol='star'),
                    hovertemplate=f'Lb: {Lb:.1f} m<br>Mn: {result_current["Mn"]:.2f} t·m<extra></extra>'
                ))
                
                # Add Lp and Lr lines
                fig.add_vline(x=result_current['Lp'], line_dash="dash", line_color="#4caf50",
                            annotation_text=f"Lp = {result_current['Lp']:.1f} m")
                fig.add_vline(x=result_current['Lr'], line_dash="dash", line_color="#ff9800",
                            annotation_text=f"Lr = {result_current['Lr']:.1f} m")
                
                # Add Mp line
                fig.add_hline(y=result_current['Mp'], line_dash="dot", line_color="#9c27b0",
                            annotation_text=f"Mp = {result_current['Mp']:.1f} t·m")
                
                # Add zones
                fig.add_vrect(x0=0, x1=result_current['Lp'],
                            fillcolor="#4caf50", opacity=0.1,
                            annotation_text="Plastic", annotation_position="top left")
                fig.add_vrect(x0=result_current['Lp'], x1=result_current['Lr'],
                            fillcolor="#ff9800", opacity=0.1,
                            annotation_text="Inelastic LTB", annotation_position="top left")
                fig.add_vrect(x0=result_current['Lr'], x1=15,
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

# ==================== TAB 4: COMPRESSION DESIGN ====================
with tab4:
    st.markdown('<h2 class="section-header">Compression Member Design (Chapter E)</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and st.session_state.selected_material:
        section = st.session_state.selected_section
        material = st.session_state.selected_material
        
        st.info(f"**Analyzing:** {section} | **Material:** {material}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Design Parameters")
            
            # Effective length factors
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
            
            # Unbraced lengths
            st.markdown("#### Unbraced Lengths")
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, max_value=20.0, step=0.5)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, max_value=20.0, step=0.5)
            
            # Calculate effective lengths
            KLx = Kx * Lx
            KLy = Ky * Ly
            
            col_kl1, col_kl2 = st.columns(2)
            with col_kl1:
                st.metric("KLx", f"{KLx:.2f} m")
            with col_kl2:
                st.metric("KLy", f"{KLy:.2f} m")
            
            # Applied load
            Pu = st.number_input("Applied Axial Load Pu (tons):", 
                               min_value=0.0, value=100.0, step=10.0)
            
            # Analyze button
            if st.button("Analyze Compression Capacity", type="primary"):
                with st.spinner("Calculating..."):
                    results = compression_analysis(df, df_mat, section, material, KLx, KLy)
                    
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
                        
                        # Slenderness parameters
                        st.markdown("### Slenderness Parameters")
                        col_s1, col_s2, col_s3 = st.columns(3)
                        
                        with col_s1:
                            st.write(f"**λx = {results['lambda_x']:.1f}**")
                            st.caption("KLx/rx")
                        
                        with col_s2:
                            st.write(f"**λy = {results['lambda_y']:.1f}**")
                            st.caption("KLy/ry")
                        
                        with col_s3:
                            st.write(f"**λmax = {results['lambda_max']:.1f}**")
                            st.caption("Governing")
                        
                        # Critical stresses
                        st.markdown("### Critical Stresses")
                        col_cr1, col_cr2, col_cr3 = st.columns(3)
                        
                        with col_cr1:
                            st.write(f"**Fe = {results['Fe']:.0f} ksc**")
                            st.caption("Elastic buckling")
                        
                        with col_cr2:
                            st.write(f"**Fcr = {results['Fcr']:.0f} ksc**")
                            st.caption("Critical stress")
                        
                        with col_cr3:
                            st.write(f"**λc = {results['lambda_c']:.1f}**")
                            st.caption("Transition slenderness")
        
        with col2:
            st.markdown("### Column Visualization & Capacity Curve")
            
            # Visualization of column with load
            if st.session_state.selected_section:
                fig = visualize_column_with_load(Pu, section)
                st.pyplot(fig)
                
                # Create capacity curve
                st.markdown("### Compression Capacity vs Slenderness")
                
                # Generate curve data
                KL_r_range = np.linspace(10, 200, 100)
                Pn_values = []
                
                for klr in KL_r_range:
                    Fe_temp = (mt.pi**2 * 2.04e6) / (klr**2)
                    Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
                    
                    if klr <= mt.pi * mt.sqrt(2.04e6 / Fy):
                        Fcr_temp = Fy * (0.658**(Fy/Fe_temp))
                    else:
                        Fcr_temp = 0.877 * Fe_temp
                    
                    Ag = float(df.loc[section, 'A [cm2]'])
                    Pn_temp = 0.9 * Fcr_temp * Ag / 1000
                    Pn_values.append(Pn_temp)
                
                # Plot
                fig2 = go.Figure()
                
                fig2.add_trace(go.Scatter(
                    x=KL_r_range, y=Pn_values,
                    mode='lines',
                    name='φPn',
                    line=dict(color='#2196f3', width=3),
                    hovertemplate='KL/r: %{x:.0f}<br>φPn: %{y:.1f} tons<extra></extra>'
                ))
                
                # Add current point if analyzed
                if 'results' in locals() and results:
                    fig2.add_trace(go.Scatter(
                        x=[results['lambda_max']], y=[results['phi_Pn']],
                        mode='markers',
                        name='Current Design',
                        marker=dict(color='#f44336', size=12, symbol='star'),
                        hovertemplate=f'KL/r: {results["lambda_max"]:.1f}<br>φPn: {results["phi_Pn"]:.1f} tons<extra></extra>'
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
            
            # Axial load
            Pu_bc = st.number_input("Axial Load Pu (tons):", 
                                   min_value=0.0, value=50.0, step=5.0)
            
            # Moments
            st.markdown("#### Applied Moments")
            Mux = st.number_input("Moment Mux (t·m):", 
                                min_value=0.0, value=30.0, step=5.0,
                                help="Moment about strong axis")
            Muy = st.number_input("Moment Muy (t·m):", 
                                min_value=0.0, value=5.0, step=1.0,
                                help="Moment about weak axis")
            
            # Effective lengths
            st.markdown("#### Effective Lengths")
            KLx_bc = st.number_input("KLx (m):", min_value=0.1, value=3.0, step=0.5)
            KLy_bc = st.number_input("KLy (m):", min_value=0.1, value=3.0, step=0.5)
            Lb_bc = st.number_input("Lb for LTB (m):", min_value=0.1, value=3.0, step=0.5)
            
            # Analysis
            if st.button("Check Beam-Column Interaction", type="primary"):
                with st.spinner("Analyzing interaction..."):
                    # Get capacities
                    comp_results = compression_analysis(df, df_mat, section, material, KLx_bc, KLy_bc)
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
            
            # Add design point if analyzed
            if 'interaction' in locals():
                # Calculate combined moment ratio
                M_combined = Mux/Mcx + Muy/Mcy
                P_ratio = Pu_bc/Pc
                
                fig.add_trace(go.Scatter(
                    x=[M_combined], y=[P_ratio],
                    mode='markers',
                    name='Design Point',
                    marker=dict(color='#f44336', size=15, symbol='star'),
                    hovertemplate=f'Design Point<br>P/Pc: {P_ratio:.3f}<br>ΣM/Mc: {M_combined:.3f}<extra></extra>'
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
                title="P-M Interaction Diagram",
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
    
    if st.session_state.filtered_sections:
        st.info(f"Comparing {len(st.session_state.filtered_sections)} sections from your selection")
        
        # Select sections to compare
        sections_to_compare = st.multiselect(
            "Select sections to compare:",
            st.session_state.filtered_sections,
            default=st.session_state.filtered_sections[:3] if len(st.session_state.filtered_sections) >= 3 else st.session_state.filtered_sections
        )
        
        if sections_to_compare:
            # Comparison parameters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                comparison_type = st.selectbox("Comparison Type:",
                    ["Weight Efficiency", "Moment Capacity", "Compression Capacity", "Cost Analysis"])
            
            with col2:
                Lb_comp = st.number_input("Unbraced Length (m):", min_value=0.1, value=3.0, step=0.5)
            
            with col3:
                KL_comp = st.number_input("Effective Length (m):", min_value=0.1, value=3.0, step=0.5)
            
            # Perform comparison
            comparison_data = []
            
            for section in sections_to_compare:
                # Get basic properties
                weight = df.loc[section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in df.columns else df.loc[section, 'w [kg/m]']
                
                # Flexural analysis
                flex_results = flexural_analysis(df, df_mat, section, st.session_state.selected_material, Lb_comp)
                
                # Compression analysis
                comp_results = compression_analysis(df, df_mat, section, st.session_state.selected_material, KL_comp, KL_comp)
                
                if flex_results and comp_results:
                    comparison_data.append({
                        'Section': section,
                        'Weight': weight,
                        'φMn': flex_results['phi_Mn'],
                        'φPn': comp_results['phi_Pn'],
                        'Moment Efficiency': flex_results['phi_Mn'] / weight,
                        'Compression Efficiency': comp_results['phi_Pn'] / weight,
                        'Cost Index': weight * 1.0  # Simplified cost index
                    })
            
            if comparison_data:
                df_comparison = pd.DataFrame(comparison_data)
                
                # Display comparison chart
                if comparison_type == "Weight Efficiency":
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=df_comparison['Section'],
                        y=df_comparison['Moment Efficiency'],
                        name='Moment Efficiency',
                        marker_color='#2196f3'
                    ))
                    
                    fig.add_trace(go.Bar(
                        x=df_comparison['Section'],
                        y=df_comparison['Compression Efficiency'],
                        name='Compression Efficiency',
                        marker_color='#4caf50'
                    ))
                    
                    fig.update_layout(
                        title="Weight Efficiency Comparison",
                        yaxis_title="Efficiency (Capacity/Weight)",
                        barmode='group',
                        height=500,
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Display comparison table
                st.markdown("### 📊 Detailed Comparison Table")
                st.dataframe(df_comparison.round(2), use_container_width=True)
                
                # Best section recommendation
                st.markdown("### 🏆 Recommendations")
                
                if comparison_type == "Weight Efficiency":
                    best_moment = df_comparison.loc[df_comparison['Moment Efficiency'].idxmax()]
                    best_compression = df_comparison.loc[df_comparison['Compression Efficiency'].idxmax()]
                    
                    col_rec1, col_rec2 = st.columns(2)
                    
                    with col_rec1:
                        st.markdown('<div class="info-box"><b>Best for Flexure:</b><br>' +
                                  f'{best_moment["Section"]}<br>' +
                                  f'Efficiency: {best_moment["Moment Efficiency"]:.3f}</div>',
                                  unsafe_allow_html=True)
                    
                    with col_rec2:
                        st.markdown('<div class="info-box"><b>Best for Compression:</b><br>' +
                                  f'{best_compression["Section"]}<br>' +
                                  f'Efficiency: {best_compression["Compression Efficiency"]:.3f}</div>',
                                  unsafe_allow_html=True)
    else:
        st.warning("⚠️ Please select sections from the 'Section Selection' tab first to compare them.")
        st.markdown("""
        ### 📖 How to Use Comparison Tool:
        1. Go to **Section Selection** tab
        2. Input your design requirements
        3. Click **Find Suitable Sections**
        4. Return here to compare the filtered sections
        
        This tool allows you to:
        - Compare multiple sections simultaneously
        - Evaluate weight efficiency
        - Analyze moment and compression capacities
        - Make informed decisions based on performance metrics
        """)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><b>Steel Design Analysis System v3.0</b></p>
    <p>Based on AISC 360-16 Specification | Developed with Streamlit</p>
    <p>© 2024 - Educational Tool for Structural Engineers</p>
</div>
""", unsafe_allow_html=True)
