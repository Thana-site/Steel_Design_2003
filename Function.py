# ==================== AISC STEEL DESIGN TOOL v4.1 ====================
# Fixed version with correct F2 calculations and plotting
# GitHub: Thana-site/Steel_Design_2003

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import plotly.graph_objects as go
import math as mt
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import requests

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="AISC Steel Design Tool v4.1",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
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
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: white;
        border-radius: 5px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #1976d2;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATA PATHS ====================
file_path = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-Material.csv"

# ==================== SESSION STATE ====================
if 'selected_section' not in st.session_state:
    st.session_state.selected_section = None
if 'selected_material' not in st.session_state:
    st.session_state.selected_material = 'SS400'
if 'selected_sections' not in st.session_state:
    st.session_state.selected_sections = []

# ==================== DATA LOADING ====================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        
        # Ensure required columns exist
        required_cols = ['Lp [cm]', 'Lr [cm]', 'Sx [cm3]', 'Zx [cm3]', 'rts [cm6]', 'j [cm4]', 'ho [mm]']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.warning(f"Missing columns in data: {missing_cols}")
        
        return df, df_mat, True
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# ==================== ORIGINAL F2 FUNCTION ====================
def F2(df, df_mat, option, option_mat, Lb):
    """F2 Analysis for doubly symmetric compact I-shaped members - Original Version"""
    try:
        Cb = 1
        section = option
        Lb = Lb * 100  # Convert Lb to cm
        
        # Get section properties
        Lp = float(df.loc[section, "Lp [cm]"])
        Lr = float(df.loc[section, "Lr [cm]"])
        S_Major = float(df.loc[section, "Sx [cm3]"])
        Z_Major = float(df.loc[section, 'Zx [cm3]'])
        
        # Handle rts column variations
        if 'rts [cm6]' in df.columns:
            rts = float(df.loc[section, 'rts [cm6]'])
        elif 'rts [cm]' in df.columns:
            rts = float(df.loc[section, 'rts [cm]'])
        else:
            # Calculate rts if not available
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
        Lni.append(np.floor(0 * 100) / 100)
        
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
        # Return default values to prevent crash
        return 0, 0, 0, 0, 0, [], [], "Error"

# ==================== COMPRESSION CALCULATION ====================
def calculate_compression_capacity(df, df_mat, section, material, KLx, KLy):
    """Calculate compression capacity per AISC 360-16 Chapter E"""
    try:
        # Material properties
        Fy = float(df_mat.loc[material, "Yield Point (ksc)"])
        E = float(df_mat.loc[material, "E"])
        
        # Section properties
        Ag = float(df.loc[section, 'A [cm2]'])
        rx = float(df.loc[section, 'rx [cm]'])
        ry = float(df.loc[section, 'ry [cm]'])
        
        # Convert KL from m to cm
        KLx_cm = KLx * 100
        KLy_cm = KLy * 100
        
        # Slenderness ratios
        lambda_x = KLx_cm / rx
        lambda_y = KLy_cm / ry
        lambda_max = max(lambda_x, lambda_y)
        
        # Limiting slenderness (4.71√(E/Fy))
        lambda_limit = 4.71 * mt.sqrt(E / Fy)
        
        # Elastic buckling stress
        Fe = (mt.pi**2 * E) / (lambda_max**2)
        
        # Critical stress
        if lambda_max <= lambda_limit:
            # Inelastic buckling
            Fcr = Fy * (0.658**(Fy/Fe))
        else:
            # Elastic buckling
            Fcr = 0.877 * Fe
        
        # Nominal capacity
        Pn = Fcr * Ag / 1000  # Convert to tons
        phi_Pn = 0.9 * Pn
        
        return {
            'Pn': Pn,
            'phi_Pn': phi_Pn,
            'Fcr': Fcr,
            'Fe': Fe,
            'lambda_x': lambda_x,
            'lambda_y': lambda_y,
            'lambda_max': lambda_max,
            'lambda_limit': lambda_limit
        }
        
    except Exception as e:
        st.error(f"Error in compression calculation: {e}")
        return None

# ==================== SERVICE LOAD CALCULATION ====================
def calculate_service_load_capacity(df, df_mat, section, material, L, Lb, loading="uniform"):
    """Calculate service load capacity in kg/m"""
    try:
        # Get moment capacity using F2 function
        Mn, _, _, _, _, _, _, _ = F2(df, df_mat, section, material, Lb)
        
        phi_Mn = 0.9 * Mn  # t·m
        
        # Convert to kg·cm
        phi_Mn_kg_cm = phi_Mn * 100000
        
        # Calculate service load based on loading type
        L_cm = L * 100  # Convert to cm
        
        if loading == "uniform":
            # w = 8M/L²
            w = (8 * phi_Mn_kg_cm) / (L_cm**2)  # kg/cm
            w_per_m = w * 100  # kg/m
        else:
            w_per_m = 0
        
        return w_per_m
        
    except Exception as e:
        st.error(f"Error calculating service load: {e}")
        return 0

# ==================== COLUMN VISUALIZATION ====================
def visualize_column_2d(df, section, plane="both"):
    """Create 2D visualization of column showing both principal planes"""
    try:
        fig, axes = plt.subplots(1, 3, figsize=(15, 6))
        
        # Get section dimensions
        d = float(df.loc[section, 'd [mm]'])
        bf = float(df.loc[section, 'bf [mm]'])
        tw = float(df.loc[section, 'tw [mm]'])
        tf = float(df.loc[section, 'tf [mm]'])
        
        # Elevation view - Strong axis (X-X)
        ax1 = axes[0]
        ax1.set_title('Elevation View\n(Strong Axis X-X)', fontsize=12, fontweight='bold')
        
        # Draw column elevation
        column_height = 3000  # 3m column
        
        # Column outline
        ax1.add_patch(Rectangle((-bf/2, 0), bf, column_height, 
                                linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd'))
        
        # Add buckling shape
        y = np.linspace(0, column_height, 100)
        x = (bf/4) * np.sin(np.pi * y / column_height)
        ax1.plot(x, y, 'r--', lw=2, alpha=0.7, label='Buckled shape')
        
        # Load arrow
        ax1.arrow(0, column_height + 200, 0, -150, head_width=bf/3, 
                 head_length=50, fc='red', ec='red')
        ax1.text(0, column_height + 300, 'P', ha='center', fontsize=14, fontweight='bold')
        
        # Base
        ax1.add_patch(Rectangle((-bf*0.75, -50), bf*1.5, 50,
                                linewidth=2, edgecolor='black', facecolor='gray'))
        
        ax1.set_xlim([-bf, bf])
        ax1.set_ylim([-100, column_height + 400])
        ax1.set_aspect('equal')
        ax1.set_xlabel('Width (mm)')
        ax1.set_ylabel('Height (mm)')
        ax1.legend()
        
        # Elevation view - Weak axis (Y-Y)
        ax2 = axes[1]
        ax2.set_title('Elevation View\n(Weak Axis Y-Y)', fontsize=12, fontweight='bold')
        
        # Column outline
        ax2.add_patch(Rectangle((-d/2, 0), d, column_height,
                                linewidth=2, edgecolor='#1a237e', facecolor='#e3f2fd'))
        
        # Buckling shape
        x2 = (d/4) * np.sin(np.pi * y / column_height)
        ax2.plot(x2, y, 'r--', lw=2, alpha=0.7, label='Buckled shape')
        
        # Load arrow
        ax2.arrow(0, column_height + 200, 0, -150, head_width=d/3,
                 head_length=50, fc='red', ec='red')
        ax2.text(0, column_height + 300, 'P', ha='center', fontsize=14, fontweight='bold')
        
        # Base
        ax2.add_patch(Rectangle((-d*0.75, -50), d*1.5, 50,
                                linewidth=2, edgecolor='black', facecolor='gray'))
        
        ax2.set_xlim([-d, d])
        ax2.set_ylim([-100, column_height + 400])
        ax2.set_aspect('equal')
        ax2.set_xlabel('Depth (mm)')
        ax2.legend()
        
        # Cross-section view
        ax3 = axes[2]
        ax3.set_title(f'Cross-Section\n{section}', fontsize=12, fontweight='bold')
        
        # Draw H-section
        # Top flange
        ax3.add_patch(Rectangle((-bf/2, d/2 - tf), bf, tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#bbdefb'))
        # Bottom flange
        ax3.add_patch(Rectangle((-bf/2, -d/2), bf, tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#bbdefb'))
        # Web
        ax3.add_patch(Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf,
                                linewidth=2, edgecolor='#1a237e', facecolor='#90caf9'))
        
        # Axes
        ax3.axhline(y=0, color='red', linewidth=1, linestyle='--', alpha=0.7)
        ax3.axvline(x=0, color='red', linewidth=1, linestyle='--', alpha=0.7)
        ax3.text(bf/2 + 10, 0, 'X', fontsize=12, color='red', fontweight='bold')
        ax3.text(0, d/2 + 10, 'Y', fontsize=12, color='red', fontweight='bold')
        
        # Dimensions
        ax3.annotate('', xy=(bf/2, d/2), xytext=(-bf/2, d/2),
                    arrowprops=dict(arrowstyle='<->', color='black', lw=1))
        ax3.text(0, d/2 + 5, f'{bf:.0f}', ha='center', fontsize=10)
        
        ax3.annotate('', xy=(bf/2 + 20, d/2), xytext=(bf/2 + 20, -d/2),
                    arrowprops=dict(arrowstyle='<->', color='black', lw=1))
        ax3.text(bf/2 + 30, 0, f'{d:.0f}', ha='center', rotation=90, fontsize=10)
        
        ax3.set_xlim([-bf, bf])
        ax3.set_ylim([-d, d])
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
    st.error("❌ Failed to load data. Please check the data source.")
    st.stop()

# ==================== HEADER ====================
st.markdown('<h1 class="main-header">🏗️ AISC Steel Design Tool v4.1</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Fixed Version with Correct F2 Calculations</p>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    if not df_mat.empty:
        material_list = list(df_mat.index)
        selected_material = st.selectbox(
            "Steel Grade:",
            material_list,
            index=material_list.index('SS400') if 'SS400' in material_list else 0
        )
        st.session_state.selected_material = selected_material
        
        if selected_material:
            Fy = df_mat.loc[selected_material, "Yield Point (ksc)"]
            Fu = df_mat.loc[selected_material, "Tensile Strength (ksc)"]
            E = df_mat.loc[selected_material, "E"]
            st.info(f"""
            **Material Properties:**
            - Fy = {Fy} ksc
            - Fu = {Fu} ksc  
            - E = {E} ksc
            """)

# ==================== MAIN TABS ====================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Section Properties",
    "🔍 Section Selection", 
    "📈 Flexural Design",
    "🏢 Column Design"
])

# ==================== TAB 1: SECTION PROPERTIES ====================
with tab1:
    st.markdown('<h2 class="section-header">Section Properties & Visualization</h2>', unsafe_allow_html=True)
    
    if not df.empty:
        # Section selection
        section_list = list(df.index)
        selected_section = st.selectbox("Select Section:", section_list)
        st.session_state.selected_section = selected_section
        
        if selected_section:
            # Display ALL properties in table format
            st.markdown("### Complete Section Properties Table")
            
            # Get all properties for the section
            section_data = df.loc[selected_section]
            
            # Create a formatted dataframe
            properties_df = pd.DataFrame({
                'Property': section_data.index,
                'Value': section_data.values
            })
            
            # Display in columns for better organization
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### Geometric Properties")
                geometric_props = ['d [mm]', 'bf [mm]', 'tw [mm]', 'tf [mm]', 'A [cm2]', 
                                 'Unit Weight [kg/m]', 'w [kg/m]']
                geometric_df = properties_df[properties_df['Property'].isin([p for p in geometric_props if p in properties_df['Property'].values])]
                st.dataframe(geometric_df, use_container_width=True, hide_index=True)
                
                st.markdown("#### Section Moduli")
                moduli_props = ['Sx [cm3]', 'Sy [cm3]', 'Zx [cm3]', 'Zy [cm3]']
                moduli_df = properties_df[properties_df['Property'].isin([p for p in moduli_props if p in properties_df['Property'].values])]
                st.dataframe(moduli_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### Moment of Inertia")
                inertia_props = ['Ix [cm4]', 'Iy [cm4]', 'rx [cm]', 'ry [cm]']
                inertia_df = properties_df[properties_df['Property'].isin([p for p in inertia_props if p in properties_df['Property'].values])]
                st.dataframe(inertia_df, use_container_width=True, hide_index=True)
                
                st.markdown("#### Stability Properties")
                stability_props = ['Lp [cm]', 'Lr [cm]', 'j [cm4]', 'Cw [cm6]', 'ho [mm]', 'rts [cm6]', 'rts [cm]']
                stability_df = properties_df[properties_df['Property'].isin([p for p in stability_props if p in properties_df['Property'].values])]
                if not stability_df.empty:
                    st.dataframe(stability_df, use_container_width=True, hide_index=True)
            
            # Complete properties table
            with st.expander("View All Properties"):
                st.dataframe(properties_df, use_container_width=True, hide_index=True)

# ==================== TAB 2: SECTION SELECTION ====================
with tab2:
    st.markdown('<h2 class="section-header">Section Selection Tool</h2>', unsafe_allow_html=True)
    
    if not df.empty and not df_mat.empty:
        # Design inputs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Moment Design")
            Mu = st.number_input("Design Moment Mu (kN·m):", min_value=0.0, value=500.0, step=50.0)
            phi_b = st.selectbox("φb:", [0.9, 0.85], index=0)
            
            # Calculate required Zx
            Mu_tm = Mu / 9.81  # Convert to t·m
            Fy = float(df_mat.loc[st.session_state.selected_material, "Yield Point (ksc)"])
            Zx_req = (Mu_tm * 100000) / (phi_b * Fy)  # cm³
            st.success(f"Required Zx ≥ {Zx_req:.0f} cm³")
        
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
        filtered_df = filtered_df[filtered_df['Zx [cm3]'] >= Zx_req]
        
        if depth_max > 0:
            filtered_df = filtered_df[filtered_df['d [mm]'] <= depth_max]
        
        if weight_max > 0:
            weight_col = 'Unit Weight [kg/m]' if 'Unit Weight [kg/m]' in filtered_df.columns else 'w [kg/m]'
            filtered_df = filtered_df[filtered_df[weight_col] <= weight_max]
        
        # Calculate capacities for filtered sections
        results = []
        for section in filtered_df.index[:20]:  # Limit to first 20 for performance
            try:
                Mn, _, _, _, Mp, _, _, _ = F2(df, df_mat, section, st.session_state.selected_material, Lb_service)
                weight = filtered_df.loc[section, 'Unit Weight [kg/m]'] if 'Unit Weight [kg/m]' in filtered_df.columns else filtered_df.loc[section, 'w [kg/m]']
                service_load = calculate_service_load_capacity(df, df_mat, section, st.session_state.selected_material, L_span, Lb_service)
                
                results.append({
                    'Section': section,
                    'Weight (kg/m)': weight,
                    'Zx (cm³)': filtered_df.loc[section, 'Zx [cm3]'],
                    'φMn (t·m)': 0.9 * Mn,
                    'Service w (kg/m)': service_load,
                    'Efficiency': (0.9 * Mn) / weight if weight > 0 else 0
                })
            except:
                continue
        
        if results:
            results_df = pd.DataFrame(results)
            results_df = results_df.sort_values('Weight (kg/m)')
            
            st.markdown(f"### Found {len(results_df)} Suitable Sections")
            
            # Display results
            st.dataframe(results_df.round(2), use_container_width=True, height=400)

# ==================== TAB 3: FLEXURAL DESIGN ====================
with tab3:
    st.markdown('<h2 class="section-header">Flexural Design - Mn vs Lb Curves</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and not df.empty and not df_mat.empty:
        section = st.session_state.selected_section
        
        # Interactive controls
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("### Parameters")
            Lb_current = st.slider("Unbraced Length Lb (m):", 0.1, 20.0, 3.0, 0.1)
            Cb = st.slider("Cb Factor:", 1.0, 2.3, 1.0, 0.1)
            show_phi = st.checkbox("Show φMn curve", value=True)
            show_mn = st.checkbox("Show Mn curve", value=True)
        
        # Calculate current values using F2 function
        Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, section, st.session_state.selected_material, Lb_current)
        
        if Mn > 0:  # Check if calculation was successful
            st.markdown("### Current Design Point")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Mn", f"{Mn:.2f} t·m")
            with col_m2:
                st.metric("φMn", f"{0.9*Mn:.2f} t·m")
            with col_m3:
                st.metric("Case", Case)
            
            # Safety check
            if Mn >= Mp * 0.9:
                st.success("✅ Close to plastic capacity")
            elif Mn >= Mp * 0.7:
                st.warning("⚠️ Moderate capacity reduction")
            else:
                st.error("❌ Significant capacity reduction")
        
        with col2:
            # Create plot using the arrays from F2
            if Mni and Lni:
                try:
                    # Flatten the arrays for plotting
                    Mni_flat = []
                    Lni_flat = []
                    
                    # Process the arrays from F2
                    for i in range(len(Mni)):
                        if isinstance(Mni[i], list):
                            Mni_flat.extend(Mni[i])
                            Lni_flat.extend(Lni[i])
                        else:
                            Mni_flat.append(Mni[i])
                            Lni_flat.append(Lni[i])
                    
                    # Create plot
                    fig = go.Figure()
                    
                    # Add Mn curve
                    if show_mn:
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=Mni_flat,
                            mode='lines+markers',
                            name='Mn',
                            line=dict(color='#1976d2', width=3),
                            marker=dict(size=6),
                            hovertemplate='Lb: %{x:.1f} m<br>Mn: %{y:.2f} t·m<extra></extra>'
                        ))
                    
                    # Add φMn curve
                    if show_phi:
                        phi_Mni = [0.9 * m for m in Mni_flat]
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=phi_Mni,
                            mode='lines',
                            name='φMn (0.9×Mn)',
                            line=dict(color='#4caf50', width=2, dash='dash'),
                            hovertemplate='Lb: %{x:.1f} m<br>φMn: %{y:.2f} t·m<extra></extra>'
                        ))
                    
                    # Add current design point
                    fig.add_trace(go.Scatter(
                        x=[Lb_current], y=[Mn],
                        mode='markers',
                        name=f'Current Design (Lb={Lb_current}m)',
                        marker=dict(color='#f44336', size=12, symbol='diamond'),
                        hovertemplate=f'Lb: {Lb_current:.1f} m<br>Mn: {Mn:.2f} t·m<extra></extra>'
                    ))
                    
                    # Add Mp line
                    fig.add_hline(y=Mp, 
                                line_dash="dot", line_color='#ff9800', line_width=2,
                                annotation_text=f"Mp = {Mp:.2f} t·m",
                                annotation_font_size=14)
                    
                    # Add vertical lines for Lp and Lr
                    fig.add_vline(x=Lp, 
                                line_dash="dash", line_color='#9c27b0', line_width=2,
                                annotation_text=f"Lp = {Lp:.2f} m",
                                annotation_font_size=14)
                    fig.add_vline(x=Lr, 
                                line_dash="dash", line_color='#e91e63', line_width=2,
                                annotation_text=f"Lr = {Lr:.2f} m",
                                annotation_font_size=14)
                    
                    # Add zones with larger labels
                    fig.add_vrect(x0=0, x1=Lp,
                                fillcolor='#4caf50', opacity=0.15,
                                annotation_text="<b>YIELDING</b>", 
                                annotation_position="top",
                                annotation_font_size=16)
                    fig.add_vrect(x0=Lp, x1=Lr,
                                fillcolor='#ff9800', opacity=0.15,
                                annotation_text="<b>INELASTIC LTB</b>", 
                                annotation_position="top",
                                annotation_font_size=16)
                    
                    # Get max Lb for elastic region
                    max_Lb = max(Lni_flat) if Lni_flat else Lr + 10
                    fig.add_vrect(x0=Lr, x1=max_Lb,
                                fillcolor='#f44336', opacity=0.15,
                                annotation_text="<b>ELASTIC LTB</b>", 
                                annotation_position="top",
                                annotation_font_size=16)
                    
                    fig.update_layout(
                        title=f"Moment Capacity vs Unbraced Length - {section}",
                        xaxis_title="Unbraced Length, Lb (m)",
                        yaxis_title="Moment Capacity (t·m)",
                        height=600,
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(x=0.02, y=0.98),
                        template='plotly_white'
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error in plotting: {str(e)}")
            
            # Summary table
            st.markdown("### Critical Lengths Summary")
            summary_df = pd.DataFrame({
                'Parameter': ['Mp (Plastic)', 'Lp (Compact Limit)', 'Lr (Inelastic Limit)', 'Current Lb', 'Current Mn'],
                'Value': [f"{Mp:.2f} t·m", f"{Lp:.2f} m", f"{Lr:.2f} m", f"{Lb_current:.2f} m", f"{Mn:.2f} t·m"],
                'Status': ['Maximum Capacity', 'Yielding → Inelastic', 'Inelastic → Elastic', 'Design Point', Case]
            })
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section from Tab 1 first.")

# ==================== TAB 4: COLUMN DESIGN ====================
with tab4:
    st.markdown('<h2 class="section-header">Column Design - Compression Capacity</h2>', unsafe_allow_html=True)
    
    if st.session_state.selected_section and not df.empty and not df_mat.empty:
        section = st.session_state.selected_section
        
        # Input parameters
        st.markdown("### Design Parameters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Effective Length Factors")
            Kx = st.selectbox("Kx:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            Ky = st.selectbox("Ky:", [0.5, 0.65, 0.7, 0.8, 1.0, 1.2, 2.0], index=4)
            st.info(f"""
            **K Factors:**
            - 0.5: Fixed-Fixed
            - 0.65: Fixed-Pinned (theoretical)
            - 0.7: Fixed-Pinned (recommended)
            - 1.0: Pinned-Pinned
            - 2.0: Fixed-Free
            """)
        
        with col2:
            st.markdown("#### Unbraced Lengths")
            Lx = st.number_input("Lx (m):", min_value=0.1, value=3.0, step=0.1)
            Ly = st.number_input("Ly (m):", min_value=0.1, value=3.0, step=0.1)
            
            # Calculate KL/r
            rx = float(df.loc[section, 'rx [cm]'])
            ry = float(df.loc[section, 'ry [cm]'])
            KLr_x = (Kx * Lx * 100) / rx
            KLr_y = (Ky * Ly * 100) / ry
            
            st.metric("KL/rx", f"{KLr_x:.1f}")
            if KLr_x > 200:
                st.error("⚠️ KL/rx > 200 (exceeds limit)")
            
            st.metric("KL/ry", f"{KLr_y:.1f}")
            if KLr_y > 200:
                st.error("⚠️ KL/ry > 200 (exceeds limit)")
        
        with col3:
            st.markdown("#### Applied Load")
            Pu = st.number_input("Applied Load Pu (tons):", min_value=0.0, value=100.0, step=10.0)
            
            # Select plane to display
            display_plane = st.selectbox("Display Plane:", ["Both", "Strong Axis (X-X)", "Weak Axis (Y-Y)"])
        
        # Calculate capacity
        comp_results = calculate_compression_capacity(df, df_mat, section, st.session_state.selected_material, Kx*Lx, Ky*Ly)
        
        if comp_results:
            # Display results
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
                    buckling_type = "Inelastic"
                    color = "🟡"
                else:
                    buckling_type = "Elastic"
                    color = "🔵"
                st.metric("Buckling Mode", f"{color} {buckling_type}",
                         delta=f"λ = {comp_results['lambda_max']:.1f}")
            
            # Check status
            if ratio <= 1.0:
                st.success(f"✅ Design PASSES - Safety Factor: {1/ratio:.2f}")
            else:
                st.error(f"❌ Design FAILS - Overstressed by {(ratio-1)*100:.1f}%")
        
        # Column visualization
        st.markdown("### Column Visualization")
        fig_col = visualize_column_2d(df, section, display_plane.lower())
        if fig_col:
            st.pyplot(fig_col)
        
        # Capacity curve
        st.markdown("### Column Capacity Curve")
        
        # Generate curve for selected plane
        col_curve1, col_curve2 = st.columns([1, 2])
        
        with col_curve1:
            curve_plane = st.radio("Select Axis:", ["Strong (X-X)", "Weak (Y-Y)"])
            show_inelastic = st.checkbox("Show inelastic region", value=True)
            show_elastic = st.checkbox("Show elastic region", value=True)
        
        with col_curve2:
            # Generate capacity curve
            KLr_range = np.linspace(1, 250, 500)
            Pn_values = []
            
            Fy = float(df_mat.loc[st.session_state.selected_material, "Yield Point (ksc)"])
            E = float(df_mat.loc[st.session_state.selected_material, "E"])
            Ag = float(df.loc[section, 'A [cm2]'])
            
            lambda_limit = 4.71 * mt.sqrt(E / Fy)
            
            for klr in KLr_range:
                Fe = (mt.pi**2 * E) / (klr**2)
                
                if klr <= lambda_limit:
                    # Inelastic buckling
                    Fcr = Fy * (0.658**(Fy/Fe))
                else:
                    # Elastic buckling
                    Fcr = 0.877 * Fe
                
                Pn = 0.9 * Fcr * Ag / 1000  # φPn in tons
                Pn_values.append(Pn)
            
            # Create plot
            fig_curve = go.Figure()
            
            # Add capacity curve
            fig_curve.add_trace(go.Scatter(
                x=KLr_range, y=Pn_values,
                mode='lines',
                name='φPn',
                line=dict(color='#1976d2', width=3),
                hovertemplate='KL/r: %{x:.1f}<br>φPn: %{y:.1f} tons<extra></extra>'
            ))
            
            # Add current point
            if comp_results:
                current_klr = comp_results['lambda_x'] if "Strong" in curve_plane else comp_results['lambda_y']
                fig_curve.add_trace(go.Scatter(
                    x=[current_klr], y=[comp_results['phi_Pn']],
                    mode='markers',
                    name='Current Design',
                    marker=dict(color='#f44336', size=12, symbol='star')
                ))
            
            # Add transition line
            fig_curve.add_vline(x=lambda_limit, 
                              line_dash="dash", line_color='#ff9800', line_width=2,
                              annotation_text=f"λ = {lambda_limit:.1f}",
                              annotation_font_size=14)
            
            # Add regions
            if show_inelastic:
                fig_curve.add_vrect(x0=0, x1=lambda_limit,
                                   fillcolor='#ffc107', opacity=0.1,
                                   annotation_text="<b>INELASTIC</b><br>Fcr = 0.658^(Fy/Fe)·Fy",
                                   annotation_position="top left",
                                   annotation_font_size=14)
            
            if show_elastic:
                fig_curve.add_vrect(x0=lambda_limit, x1=250,
                                   fillcolor='#2196f3', opacity=0.1,
                                   annotation_text="<b>ELASTIC</b><br>Fcr = 0.877·Fe",
                                   annotation_position="top right",
                                   annotation_font_size=14)
            
            # Add limit line at KL/r = 200
            fig_curve.add_vline(x=200, 
                              line_dash="dot", line_color='#f44336', line_width=2,
                              annotation_text="KL/r = 200 (Limit)",
                              annotation_font_size=12)
            
            # Add demand line
            if Pu > 0:
                fig_curve.add_hline(y=Pu, 
                                  line_dash="dash", line_color='#4caf50', line_width=2,
                                  annotation_text=f"Pu = {Pu:.1f} tons",
                                  annotation_font_size=14)
            
            fig_curve.update_layout(
                title=f"Column Capacity Curve - {curve_plane}",
                xaxis_title="Slenderness Ratio (KL/r)",
                yaxis_title="Design Capacity φPn (tons)",
                height=500,
                hovermode='x unified',
                template='plotly_white',
                showlegend=True
            )
            
            st.plotly_chart(fig_curve, use_container_width=True)
        
        # Summary table
        if comp_results:
            st.markdown("### Design Summary")
            summary_col = pd.DataFrame({
                'Parameter': ['λx (KLx/rx)', 'λy (KLy/ry)', 'λ limit', 'Fe (ksc)', 'Fcr (ksc)', 
                             'Pn (tons)', 'φPn (tons)', 'Pu (tons)', 'Utilization'],
                'Value': [f"{comp_results['lambda_x']:.1f}", f"{comp_results['lambda_y']:.1f}",
                         f"{comp_results['lambda_limit']:.1f}", f"{comp_results['Fe']:.1f}",
                         f"{comp_results['Fcr']:.1f}", f"{comp_results['Pn']:.2f}",
                         f"{comp_results['phi_Pn']:.2f}", f"{Pu:.2f}", 
                         f"{Pu/comp_results['phi_Pn']:.3f}" if comp_results['phi_Pn'] > 0 else "N/A"]
            })
            st.dataframe(summary_col, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Please select a section from Tab 1 first.")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><b>AISC Steel Design Tool v4.1</b></p>
    <p>Based on AISC 360-16 Specification</p>
    <p>Using Original F2 Function with Correct Calculations</p>
    <p>Units: Forces in kg/cm², Dimensions in cm, Service Loads in kg/m</p>
</div>
""", unsafe_allow_html=True)
