# Import libraries
import streamlit as st #version 1.42.0
import pandas as pd #version 2.2.2.
import matplotlib.pyplot as plt  # Correct import for matplotlib
import matplotlib.patches as patches #version 3.9.2.
import math as mt 
import numpy as np #version 2.1.0
import altair as alt #version 5.4.1.
import plotly.express as px #6.0.0
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from st_aggrid import AgGrid,GridOptionsBuilder #version 1.1.0
import os 
import requests

# Configure page
st.set_page_config(
    page_title="Steel Design Analysis",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
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

# File paths
file_path = r"https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = r"https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-Material.csv"

# Initialize session state with comprehensive safety checks
def safe_session_state_init():
    """Safely initialize session state variables"""
    try:
        if 'selected_sections' not in st.session_state:
            st.session_state.selected_sections = []
        if 'input_mode' not in st.session_state:
            st.session_state.input_mode = "slider"
    except Exception as e:
        st.error(f"Error initializing session state: {e}")

# Call safe initialization
safe_session_state_init()

# Initialize empty DataFrames with error handling
try:
    df = pd.DataFrame()
    df_mat = pd.DataFrame()
    section_list = []
    section_list_mat = []
except Exception as e:
    st.error(f"Error initializing data structures: {e}")
    df = pd.DataFrame()
    df_mat = pd.DataFrame()
    section_list = []
    section_list_mat = []

# Function to check if URL is accessible
@st.cache_data
def check_url(url):
    try:
        response = requests.get(url)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        st.error(f"Error: {e}")
        return False

# Load data with better error handling
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        # Ensure data is not empty
        if df.empty or df_mat.empty:
            return pd.DataFrame(), pd.DataFrame(), False
        return df, df_mat, True
    except Exception as e:
        st.error(f"An error occurred while loading the files: {e}")
        return pd.DataFrame(), pd.DataFrame(), False

# Load data with comprehensive error handling
try:
    if check_url(file_path) and check_url(file_path_mat):
        df, df_mat, success = load_data()
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
    df = pd.DataFrame()
    df_mat = pd.DataFrame()
    section_list = []
    section_list_mat = []

# Main header
st.markdown('<h1 class="main-header">🏗️ Structural Steel Design Analysis</h1>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("## 🔧 Configuration Panel")
    
    # Default selected options
    option = section_list[0] if section_list else ""
    option_mat = section_list_mat[0] if section_list_mat else ""
    bending_axis = "Major axis bending"

    # Toggle for enabling Chapter F Strength input
    ChapterF_Strength = st.checkbox("🔍 Enable Chapter F Strength Analysis")
    if ChapterF_Strength:
        option = st.selectbox("🔩 Choose Steel Section:", section_list, index=0 if option in section_list else 0)
        option_mat = st.selectbox("⚙️ Choose Steel Grade:", section_list_mat, index=0 if option_mat in section_list_mat else 0)
        bending_axis = st.selectbox("📐 Select Bending Axis:", ["Major axis bending", "Minor axis bending"], index=0)

    st.divider()
    
    # Input method selection
    st.markdown("### 📊 Input Method")
    col1, col2 = st.columns(2)
    if col1.button("🎚️ Slider", use_container_width=True):
        st.session_state.input_mode = "slider"
    if col2.button("🔢 Number", use_container_width=True):
        st.session_state.input_mode = "number"

    # Toggle for enabling Chapter F Design input
    Mu = 100
    Vu = 100
    ChapterF_Design = st.checkbox("📋 Enable Chapter F Design Analysis")
    if ChapterF_Design:
        Mu = st.number_input("⚡ Ultimate Bending Moment (kN·m):", value=100.0)
        Vu = st.number_input("⚡ Ultimate Shear Force (kN):", value=100.0)

# Helper Functions
def Flexural_classify(df, df_mat, option, option_mat):
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
    Fy = float(df_mat.loc[option_mat,"Yield Point (ksc)"])
    E = float(df_mat.loc[option_mat,"E"])          
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
        Mn = Mp/100000
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100
    elif Lp <= Lb < Lr:
        Case = "F2.2 - Lateral-Torsional Buckling"
        Mp = Fy * Z_Major
        Mn = Cb * (Mp - ((Mp - 0.7 * Fy * S_Major) * ((Lb - Lp) / (Lr - Lp))))
        Mn = Mn / 100000
        Mp = Mp/100000
        Mn = min(Mp,Mn)
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100
    else:
        Case = "F2.3 - Lateral-Torsional Buckling"
        Term_1 = (Cb * mt.pi ** 2 * E) / (((Lb) / rts) ** 2)
        Term_2 = 0.078 * ((j * c) / (S_Major * h0)) * (((Lb) / rts) ** 2)
        Term12 = Term_1 * mt.sqrt(1 + Term_2)
        Mn = Term12*S_Major
        Mn = Mn/100000
        Mp = Fy * Z_Major 
        Mp = Mp/100000
        Mn = np.floor(Mn * 100) / 100
        Mp = np.floor(Mp * 100) / 100

    Mn = np.floor(Mn * 100) / 100
    Mn_F2C = 0.7 * Fy * S_Major / 100000
    Mn_F2C = np.floor(Mn_F2C * 100) / 100

    Mni.append(Mp)
    Lni.append(np.floor(0 * 100) / 100)

    Mni.append(Mp)
    Lni.append(np.floor((Lp/100) * 100) / 100)

    Mni.append(Mn_F2C)
    Lni.append(np.floor((Lr/100) * 100) / 100)

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
        Mnc = fcr*S_Major
        Mnc = Mnc / 100000
        Mnc = np.floor(Mnc * 100) / 100
        Mnr.append(Mnc)
        
        i += 0.5

    Mni.append(Mnr)
    Lni.append(Lri_values)

    Lb = Lb/100
    Lp = Lp/100
    Lr = Lro/100

    Lb = np.floor(Lb * 100) / 100
    Lp = np.floor(Lp * 100) / 100
    Lr = np.floor(Lr * 100) / 100

    return Mn, Lb, Lp, Lr, Mp, Mni, Lni, Case

def classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis):
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
            return "F3: Slender Flange, Compact Web"
        # Add other combinations...
    elif bending_axis == "Minor axis bending":
        if flange == "Compact Flange":
            return "F6: Minor Axis Bending (Compact Flange)"
        elif flange == "Non-Compact Flange":
            return "F6: Minor Axis Bending (Non-Compact Flange)"
        elif flange == "Slender Flange":
            return "F6: Minor Axis Bending (Slender Flange)"
    
    return "Classification not determined"

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Steel Catalogue", "🔧 Chapter F Analysis", "📋 Section Selection", "📈 Comparative Analysis"])

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
        if option in df.index:
            bf = float(df.loc[option, 'bf [mm]'])
            d = float(df.loc[option, 'd [mm]'])
            tw = float(df.loc[option, 'tw [mm]'])
            tf = float(df.loc[option, 'tf [mm]'])

            fig, ax = plt.subplots(figsize=(6, 6))
            fig.patch.set_facecolor('white')
            ax.set_facecolor('white')

            # Draw H-section
            flange_top = patches.Rectangle((-bf/2, d/2 - tf), bf, tf, 
                                         linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)
            flange_bottom = patches.Rectangle((-bf/2, -d/2), bf, tf, 
                                            linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)
            web = patches.Rectangle((-tw/2, -d/2 + tf), tw, d - 2*tf, 
                                  linewidth=2, edgecolor='#1f77b4', facecolor='lightblue', alpha=0.7)

            ax.add_patch(flange_top)
            ax.add_patch(flange_bottom)
            ax.add_patch(web)

            # Centroid axes
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
        else:
            st.warning("⚠️ Please select a valid section!")

    with col3:
        st.markdown("### 🔍 Classification Results")
        if option and option_mat and not df.empty and not df_mat.empty:
            try:
                # Classification
                lamf, lamw, lamf_lim, lamf_lim, Classify_flange_Compression, Classify_Web_Compression = compression_classify(df, df_mat, option, option_mat)
                lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural = Flexural_classify(df, df_mat, option, option_mat)

                # Create classification summary
                classification_data = {
                    "Element": ["Flange (Compression)", "Web (Compression)", "Flange (Flexural)", "Web (Flexural)"],
                    "Classification": [Classify_flange_Compression, Classify_Web_Compression, 
                                     Classify_flange_Flexural, Classify_Web_Flexural],
                    "λ": [f"{lamf:.2f}", f"{lamw:.2f}", f"{lamf:.2f}", f"{lamw:.2f}"]
                }
                
                classification_df = pd.DataFrame(classification_data)
                
                # Color-code classifications
                def color_classification(val):
                    if "Compact" in val:
                        return 'background-color: #d4edda'
                    elif "Non-Compact" in val:
                        return 'background-color: #fff3cd'
                    else:
                        return 'background-color: #f8d7da'

                styled_df = classification_df.style.applymap(color_classification, subset=['Classification'])
                st.dataframe(styled_df, use_container_width=True)

                # Design code section
                result = classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis)
                st.markdown(f"**🎯 Design Code Section:** {result}")

            except Exception as e:
                st.error(f"❌ Error in classification: {e}")

with tab2:
    st.markdown('<h2 class="sub-header">Chapter F: Flexural Design Analysis</h2>', unsafe_allow_html=True)
    
    if option and option_mat and not df.empty and not df_mat.empty:
        try:
            # Get classification
            lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, Classify_flange_Flexural, Classify_Web_Flexural = Flexural_classify(df, df_mat, option, option_mat)
            result = classify_section(lamf, lamw, lamf_limp, lamf_limr, lamw_limp, lamw_limr, bending_axis)
            
            st.markdown(f"**📋 Analysis Method:** {result}")
            
            # Input for unbraced length
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

            # Analysis based on classification
            if "F2:" in result:
                col_result, col_plot = st.columns([1, 2])
                
                with col_result:
                    Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, option, option_mat, Lb)
                    
                    Fib = 0.9
                    FibMn = Fib * Mn
                    FibMp = Fib * Mp

                    # Results table
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
                    
                    # Safety check
                    if Mn >= Mp * 0.9:
                        st.success("✅ Close to plastic capacity")
                    elif Mn >= Mp * 0.7:
                        st.warning("⚠️ Moderate capacity reduction")
                    else:
                        st.error("❌ Significant capacity reduction")

                with col_plot:
                    # Create interactive plot
                    try:
                        Mni_flat = Mni[:3] + (Mni[3] if len(Mni) > 3 else [])
                        Lni_flat = Lni[:3] + (Lni[3] if len(Lni) > 3 else [])

                        fig = go.Figure()
                        
                        # Add capacity curve
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=Mni_flat,
                            mode='lines+markers',
                            name='Nominal Moment Capacity',
                            line=dict(color='blue', width=3),
                            marker=dict(size=6)
                        ))
                        
                        # Add current point
                        fig.add_trace(go.Scatter(
                            x=[Lb], y=[Mn],
                            mode='markers',
                            name=f'Current Design Point (Lb={Lb}m)',
                            marker=dict(color='red', size=12, symbol='diamond')
                        ))
                        
                        # Add design capacity line
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=[FibMn] * len(Lni_flat),
                            mode='lines',
                            name='φMn (Design Capacity)',
                            line=dict(color='green', width=2, dash='dash')
                        ))
                        
                        # Add plastic capacity line
                        fig.add_trace(go.Scatter(
                            x=Lni_flat, y=[Mp] * len(Lni_flat),
                            mode='lines',
                            name='Mp (Plastic Capacity)',
                            line=dict(color='orange', width=2, dash='dot')
                        ))
                        
                        # Add vertical lines for Lp and Lr
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

with tab3:
    st.markdown('<h2 class="sub-header">Steel Section Selection Tool</h2>', unsafe_allow_html=True)
    
    # Filter controls
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        zx_min = st.number_input("🔍 Min Zx [cm³]:", min_value=0, value=0, step=100)
    
    with col_filter2:
        depth_min = st.number_input("📏 Min Depth [mm]:", min_value=0, value=0, step=50)
    
    with col_filter3:
        weight_max = st.number_input("⚖️ Max Weight [kg/m]:", min_value=0, value=1000, step=10)

    # Apply filters
    if not df.empty:
        filtered_data = df.copy()
        filtered_data = filtered_data[filtered_data["Zx [cm3]"] >= zx_min]
        if depth_min > 0:
            filtered_data = filtered_data[filtered_data["d [mm]"] >= depth_min]
        if weight_max < 1000:
            filtered_data = filtered_data[filtered_data["Unit Weight [kg/m]"] <= weight_max]

        st.markdown(f"**📋 Filtered Results: {len(filtered_data)} sections**")

        # Configure AgGrid for better selection
        gb = GridOptionsBuilder.from_dataframe(filtered_data)
        gb.configure_selection("multiple", use_checkbox=True, groupSelectsChildren=False)
        gb.configure_grid_options(enableCellTextSelection=True)
        gb.configure_column("Section", headerCheckboxSelection=True)
        grid_options = gb.build()

        # Display grid with error handling
        try:
            grid_response = AgGrid(
                filtered_data,
                gridOptions=grid_options,
                height=400,
                width="100%",
                theme="streamlit",
                allow_unsafe_jscode=True,
                update_mode='SELECTION_CHANGED'
            )
        except Exception as e:
            st.error(f"Error displaying grid: {e}")
            grid_response = {"selected_rows": []}

        # Get selected rows with safe checking
        selected_rows = grid_response.get("selected_rows", [])
        
        if selected_rows is not None and len(selected_rows) > 0:
            # Initialize session state for selected sections safely
            try:
                if 'selected_sections' not in st.session_state:
                    st.session_state.selected_sections = []
                
                # Store as list to avoid DataFrame boolean issues
                st.session_state.selected_sections = list(selected_rows)
                df_selected = pd.DataFrame(selected_rows)
                
                st.success(f"✅ Selected {len(selected_rows)} sections for analysis")
            except Exception as e:
                st.error(f"Error storing selected sections: {e}")
                st.session_state.selected_sections = []
            
            # Show selected sections summary with comprehensive error handling
            with st.expander("📋 Selected Sections Summary", expanded=True):
                try:
                    summary_cols = ['Nominal Size [mm]', 'Zx [cm3]', 'd [mm]', 'Unit Weight [kg/m]']
                    available_cols = [col for col in summary_cols if col in df_selected.columns]
                    if available_cols and not df_selected.empty:
                        st.dataframe(df_selected[available_cols], use_container_width=True)
                    else:
                        st.warning("⚠️ Summary data not available or no columns found")
                except Exception as e:
                    st.error(f"Error displaying summary: {e}")
        else:
            st.info("ℹ️ Please select sections for comparative analysis")
    else:
        st.error("❌ No data available")

with tab4:
    st.markdown('<h2 class="sub-header">Comparative Analysis Dashboard</h2>', unsafe_allow_html=True)
    
    # Safe checking for selected sections
    has_selected_sections = False
    selected_sections_data = []
    
    try:
        if 'selected_sections' in st.session_state:
            selected_sections_raw = st.session_state.selected_sections
            
            # Handle different data types
            if selected_sections_raw is not None:
                if isinstance(selected_sections_raw, (list, tuple)):
                    selected_sections_data = list(selected_sections_raw)
                    has_selected_sections = len(selected_sections_data) > 0
                elif isinstance(selected_sections_raw, pd.DataFrame):
                    if not selected_sections_raw.empty:
                        selected_sections_data = selected_sections_raw.to_dict('records')
                        has_selected_sections = True
                else:
                    # Try to convert to list
                    try:
                        selected_sections_data = list(selected_sections_raw)
                        has_selected_sections = len(selected_sections_data) > 0
                    except:
                        selected_sections_data = []
                        has_selected_sections = False
    except Exception as e:
        st.error(f"Error processing selected sections: {e}")
        selected_sections_data = []
        has_selected_sections = False
    
    if has_selected_sections:
        try:
            df_selected = pd.DataFrame(selected_sections_data)
        except Exception as e:
            st.error(f"Error creating DataFrame from selected sections: {e}")
            df_selected = pd.DataFrame()
        
        # Input controls for analysis
        col_input1, col_input2, col_input3 = st.columns(3)
        
        with col_input1:
            if st.session_state.input_mode == "slider":
                Lbd = st.slider("📏 Design Unbraced Length [m]", 0.0, 20.0, 6.0, 0.5)
            else:
                Lbd = st.number_input("📏 Design Unbraced Length [m]", value=6.0, step=0.5)
        
        with col_input2:
            analysis_type = st.selectbox("🔍 Analysis Type", 
                                       ["Moment Capacity", "Weight Comparison", "Efficiency Ratio"])
        
        with col_input3:
            show_details = st.checkbox("📊 Show Detailed Results", value=True)

        if 'Section' in df_selected.columns and len(df_selected) > 0:
            try:
                section_names = df_selected["Section"].unique()
            except Exception as e:
                st.error(f"Error getting section names: {e}")
                section_names = []
            
            # Initialize results storage
            comparison_results = []
            plot_data = {'sections': [], 'Mp': [], 'Mn': [], 'phi_Mn': [], 'weight': [], 'efficiency': []}
            
            # Analyze each section with comprehensive error handling
            for section in section_names:
                try:
                    # Check if section exists in main dataframe
                    if section not in df.index:
                        st.warning(f"⚠️ Section {section} not found in database")
                        continue
                        
                    # Perform F2 analysis
                    Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, section, option_mat, Lbd)
                    
                    Fib = 0.9
                    FibMn = Fib * Mn
                    
                    # Safely get weight
                    try:
                        weight = float(df.loc[section, 'Unit Weight [kg/m]'])
                    except (KeyError, ValueError):
                        weight = 0.0
                        st.warning(f"⚠️ Weight data not available for {section}")
                    
                    efficiency = FibMn / weight if weight > 0 else 0
                    
                    # Store results
                    comparison_results.append({
                        'Section': section,
                        'Mp (t⋅m)': Mp,
                        'Mn (t⋅m)': Mn,
                        'φMn (t⋅m)': FibMn,
                        'Weight (kg/m)': weight,
                        'Efficiency': efficiency,
                        'Lp (m)': Lp,
                        'Lr (m)': Lr,
                        'Case': Case
                    })
                    
                    # Store plot data
                    plot_data['sections'].append(section)
                    plot_data['Mp'].append(Mp)
                    plot_data['Mn'].append(Mn)
                    plot_data['phi_Mn'].append(FibMn)
                    plot_data['weight'].append(weight)
                    plot_data['efficiency'].append(efficiency)
                    
                except Exception as e:
                    st.error(f"❌ Error analyzing section {section}: {e}")
                    continue
            
            if comparison_results:
                results_df = pd.DataFrame(comparison_results)
                
                # Sort by efficiency (highest first)
                results_df = results_df.sort_values('Efficiency', ascending=False)
                
                # Display summary table
                st.markdown("### 📊 Comparative Analysis Results")
                
                # Create styled dataframe
                def highlight_best(s):
                    if s.name == 'Efficiency':
                        max_val = s.max()
                        return ['background-color: #d4edda' if v == max_val else '' for v in s]
                    elif s.name == 'Weight (kg/m)':
                        min_val = s.min()
                        return ['background-color: #d4edda' if v == min_val else '' for v in s]
                    elif s.name == 'φMn (t⋅m)':
                        max_val = s.max()
                        return ['background-color: #d4edda' if v == max_val else '' for v in s]
                    return [''] * len(s)
                
                styled_results = results_df.style.apply(highlight_best, axis=0)
                st.dataframe(styled_results, use_container_width=True)
                
                # Create comparison plots
                st.markdown("### 📈 Visual Comparison")
                
                if analysis_type == "Moment Capacity":
                    # Moment capacity comparison
                    fig = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=('Plastic vs Nominal Moment', 'Design Moment Capacity', 
                                      'Moment Breakdown', 'Efficiency Ranking'),
                        specs=[[{"secondary_y": False}, {"secondary_y": False}],
                               [{"secondary_y": False}, {"secondary_y": False}]]
                    )
                    
                    # Plot 1: Mp vs Mn
                    fig.add_trace(
                        go.Bar(name='Mp', x=plot_data['sections'], y=plot_data['Mp'], 
                               marker_color='orange', opacity=0.7),
                        row=1, col=1
                    )
                    fig.add_trace(
                        go.Bar(name='Mn', x=plot_data['sections'], y=plot_data['Mn'], 
                               marker_color='blue', opacity=0.7),
                        row=1, col=1
                    )
                    
                    # Plot 2: Design capacity
                    fig.add_trace(
                        go.Bar(name='φMn', x=plot_data['sections'], y=plot_data['phi_Mn'], 
                               marker_color='green', opacity=0.7),
                        row=1, col=2
                    )
                    
                    # Plot 3: Stacked comparison
                    fig.add_trace(
                        go.Bar(name='Mp', x=plot_data['sections'], y=plot_data['Mp'], 
                               marker_color='orange'),
                        row=2, col=1
                    )
                    fig.add_trace(
                        go.Bar(name='Mn', x=plot_data['sections'], y=plot_data['Mn'], 
                               marker_color='blue'),
                        row=2, col=1
                    )
                    fig.add_trace(
                        go.Bar(name='φMn', x=plot_data['sections'], y=plot_data['phi_Mn'], 
                               marker_color='green'),
                        row=2, col=1
                    )
                    
                    # Plot 4: Efficiency
                    fig.add_trace(
                        go.Bar(name='Efficiency', x=plot_data['sections'], y=plot_data['efficiency'], 
                               marker_color='purple', opacity=0.7),
                        row=2, col=2
                    )
                    
                    fig.update_layout(height=800, showlegend=True, 
                                    title_text=f"Moment Capacity Comparison (Lb = {Lbd}m)")
                    fig.update_xaxes(tickangle=45)
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                elif analysis_type == "Weight Comparison":
                    # Weight vs capacity scatter plot
                    fig = px.scatter(
                        x=plot_data['weight'], 
                        y=plot_data['phi_Mn'],
                        text=plot_data['sections'],
                        labels={'x': 'Weight (kg/m)', 'y': 'Design Moment φMn (t⋅m)'},
                        title='Weight vs Design Moment Capacity'
                    )
                    fig.update_traces(textposition="top center", marker_size=12)
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                
                elif analysis_type == "Efficiency Ratio":
                    # Efficiency comparison
                    fig = px.bar(
                        x=plot_data['sections'], 
                        y=plot_data['efficiency'],
                        labels={'x': 'Steel Section', 'y': 'Efficiency (t⋅m/kg/m)'},
                        title='Structural Efficiency Comparison',
                        color=plot_data['efficiency'],
                        color_continuous_scale='Viridis'
                    )
                    fig.update_layout(height=500)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Detailed individual analysis
                if show_details:
                    st.markdown("### 🔍 Detailed Section Analysis")
                    
                    # Create tabs for each section
                    if len(section_names) <= 5:  # Limit tabs to avoid UI clutter
                        section_tabs = st.tabs([f"📊 {section}" for section in section_names])
                        
                        for idx, section in enumerate(section_names):
                            with section_tabs[idx]:
                                col_detail1, col_detail2 = st.columns([1, 2])
                                
                                with col_detail1:
                                    # Section details
                                    section_result = results_df[results_df['Section'] == section].iloc[0]
                                    
                                    st.markdown(f"#### 📋 {section} Analysis")
                                    detail_data = {
                                        'Parameter': ['Plastic Moment (Mp)', 'Nominal Moment (Mn)', 
                                                    'Design Moment (φMn)', 'Weight', 'Efficiency',
                                                    'Compact Length (Lp)', 'LTB Length (Lr)', 'Governing Case'],
                                        'Value': [f"{section_result['Mp (t⋅m)']:.2f} t⋅m",
                                                f"{section_result['Mn (t⋅m)']:.2f} t⋅m",
                                                f"{section_result['φMn (t⋅m)']:.2f} t⋅m",
                                                f"{section_result['Weight (kg/m)']:.1f} kg/m",
                                                f"{section_result['Efficiency']:.3f} t⋅m/(kg/m)",
                                                f"{section_result['Lp (m)']:.2f} m",
                                                f"{section_result['Lr (m)']:.2f} m",
                                                section_result['Case']]
                                    }
                                    
                                    detail_df = pd.DataFrame(detail_data)
                                    st.dataframe(detail_df, use_container_width=True)
                                
                                with col_detail2:
                                    # Individual capacity curve
                                    try:
                                        Mn_plot, Lb_calc, Lp_plot, Lr_plot, Mp_plot, Mni_plot, Lni_plot, Case_plot = F2(df, df_mat, section, option_mat, Lbd)
                                        
                                        # Flatten plot data
                                        Mni_flat = Mni_plot[:3] + (Mni_plot[3] if len(Mni_plot) > 3 else [])
                                        Lni_flat = Lni_plot[:3] + (Lni_plot[3] if len(Lni_plot) > 3 else [])
                                        
                                        fig_individual = go.Figure()
                                        
                                        # Capacity curve
                                        fig_individual.add_trace(go.Scatter(
                                            x=Lni_flat, y=Mni_flat,
                                            mode='lines+markers',
                                            name='Capacity Curve',
                                            line=dict(color='blue', width=2),
                                            marker=dict(size=4)
                                        ))
                                        
                                        # Current design point
                                        fig_individual.add_trace(go.Scatter(
                                            x=[Lbd], y=[Mn_plot],
                                            mode='markers',
                                            name=f'Design Point',
                                            marker=dict(color='red', size=10, symbol='diamond')
                                        ))
                                        
                                        # Add limiting lengths
                                        fig_individual.add_vline(x=Lp_plot, line=dict(color="purple", dash="dash"), 
                                                               annotation_text="Lp")
                                        fig_individual.add_vline(x=Lr_plot, line=dict(color="brown", dash="dash"), 
                                                               annotation_text="Lr")
                                        
                                        fig_individual.update_layout(
                                            title=f"Capacity Curve - {section}",
                                            xaxis_title="Unbraced Length (m)",
                                            yaxis_title="Moment (t⋅m)",
                                            height=400
                                        )
                                        
                                        st.plotly_chart(fig_individual, use_container_width=True)
                                        
                                    except Exception as e:
                                        st.error(f"Error plotting {section}: {e}")
                    else:
                        st.info("ℹ️ Too many sections selected. Showing summary only.")
                
                # Export functionality
                st.markdown("### 💾 Export Results")
                col_export1, col_export2 = st.columns(2)
                
                with col_export1:
                    if st.button("📊 Download Comparison Table", use_container_width=True):
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="Download CSV",
                            data=csv,
                            file_name=f"steel_comparison_Lb_{Lbd}m.csv",
                            mime="text/csv"
                        )
                
                with col_export2:
                    if st.button("📈 Generate Report", use_container_width=True):
                        # Create summary report
                        best_section = results_df.iloc[0]
                        report = f"""
                        Steel Section Comparison Report
                        ================================
                        
                        Analysis Parameters:
                        - Unbraced Length: {Lbd} m
                        - Material Grade: {option_mat}
                        - Number of Sections: {len(section_names)}
                        
                        Best Performing Section: {best_section['Section']}
                        - Design Moment: {best_section['φMn (t⋅m)']:.2f} t⋅m
                        - Weight: {best_section['Weight (kg/m)']:.1f} kg/m
                        - Efficiency: {best_section['Efficiency']:.3f} t⋅m/(kg/m)
                        - Case: {best_section['Case']}
                        
                        Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """
                        
                        st.download_button(
                            label="Download Report",
                            data=report,
                            file_name=f"steel_analysis_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.txt",
                            mime="text/plain"
                        )
            
            else:
                st.warning("⚠️ No analysis results available")
        else:
            st.error("❌ Selected data does not contain 'Section' column")
    else:
        st.info("ℹ️ Please select sections in the 'Section Selection' tab first")
        
        # Show instruction card
        st.markdown("""
        <div class="warning-card">
            <h4>📋 How to use Comparative Analysis:</h4>
            <ol>
                <li>Go to the <strong>"Section Selection"</strong> tab</li>
                <li>Filter sections based on your requirements</li>
                <li>Select multiple sections using checkboxes</li>
                <li>Return to this tab to see comparative analysis</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    🏗️ <strong>Structural Steel Design Analysis Tool</strong><br>
    Based on AISC 360 Design Specifications<br>
    <em>Developed for educational and professional use</em>
</div>
""", unsafe_allow_html=True)
