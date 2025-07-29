# Import libraries
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
file_path = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-H-Shape.csv"
file_path_mat = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-Material.csv"
file_path_chf = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main/2003-Steel-Beam-DataBase-CHF.csv"

# Initialize session state with safety checks
def safe_session_state_init():
    """Safely initialize session state variables"""
    try:
        if 'selected_sections' not in st.session_state:
            st.session_state.selected_sections = []
        if 'input_mode' not in st.session_state:
            st.session_state.input_mode = "slider"
        if 'section_lb_values' not in st.session_state:
            st.session_state.section_lb_values = {}
    except Exception as e:
        st.error(f"Error initializing session state: {e}")

# Call safe initialization
safe_session_state_init()

# Function to check if URL is accessible
@st.cache_data
def check_url(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        st.error(f"URL check error: {e}")
        return False

# Load data with better error handling
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(file_path, index_col=0, encoding='ISO-8859-1')
        df_mat = pd.read_csv(file_path_mat, index_col=0, encoding="utf-8")
        df_chf = pd.read_csv(file_path_chf, index_col=0, encoding="utf-8")
        
        # Ensure data is not empty
        if df.empty or df_mat.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False
        return df, df_mat, df_chf, True
    except Exception as e:
        st.error(f"An error occurred while loading the files: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False

# Initialize empty DataFrames
df = pd.DataFrame()
df_mat = pd.DataFrame()
df_chf = pd.DataFrame()
section_list = []
section_list_mat = []

# Load data with comprehensive error handling
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


def create_multi_section_comparison_plot(df, df_mat, selected_sections, option_mat, section_lb_values, use_global_lb=False, global_lb=6.0):
    """สร้างกราฟเปรียบเทียบ Moment Capacity vs Unbraced Length สำหรับหลายหน้าตัด"""
    try:
        fig = go.Figure()
        
        # สีที่แตกต่างกันสำหรับแต่ละหน้าตัด
        colors = px.colors.qualitative.Set3
        
        # เก็บข้อมูลสำหรับการแสดงผล
        legend_info = []
        
        for i, section in enumerate(selected_sections):
            try:
                if section not in df.index:
                    continue
                
                # กำหนด Lb range สำหรับการ plot
                Lr_max = df.loc[section, 'Lr [cm]'] / 100
                Lr_max = max(15, Lr_max + 5)  # ขยายช่วงให้เห็นชัดขึ้น
                
                # สร้าง Lb range
                lb_range = np.linspace(0.1, Lr_max, 100)
                mn_values = []
                
                # คำนวณ Mn สำหรับแต่ละค่า Lb
                for lb in lb_range:
                    try:
                        Mn, _, Lp, Lr, Mp, _, _, _ = F2(df, df_mat, section, option_mat, lb)
                        mn_values.append(Mn if Mn is not None else 0)
                    except:
                        mn_values.append(0)
                
                # เพิ่มเส้นโค้งของหน้าตัด
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
                
                # เพิ่มจุดปัจจุบันของแต่ละหน้าตัด
                current_lb = global_lb if use_global_lb else section_lb_values.get(section, 6.0)
                current_mn, _, current_lp, current_lr, current_mp, _, _, current_case = F2(df, df_mat, section, option_mat, current_lb)
                
                # จุดปัจจุบัน
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
                
                # เพิ่มเส้น Lp และ Lr (จะแสดงเฉพาะหน้าตัดแรกเพื่อไม่ให้ซ้อนทับ)
                if i == 0:  # แสดงเฉพาะหน้าตัดแรก
                    fig.add_vline(
                        x=current_lp,
                        line=dict(color="purple", dash="dash", width=1),
                        annotation_text=f"Lp ({section})",
                        annotation_position="top"
                    )
                    fig.add_vline(
                        x=current_lr,
                        line=dict(color="brown", dash="dash", width=1),
                        annotation_text=f"Lr ({section})",
                        annotation_position="top"
                    )
                
                # เก็บข้อมูลสำหรับ legend
                legend_info.append({
                    'section': section,
                    'current_lb': current_lb,
                    'current_mn': current_mn,
                    'mp': current_mp,
                    'efficiency': (0.9 * current_mn) / safe_get_weight(df, section) if safe_get_weight(df, section) > 0 else 0
                })
                
            except Exception as e:
                st.warning(f"⚠️ Error processing section {section}: {e}")
                continue
        
        # ปรับแต่ง layout
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
        
        # เพิ่มกริด
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        
        return fig, legend_info
        
    except Exception as e:
        st.error(f"Error creating multi-section comparison plot: {e}")
        return None, []

def create_multi_section_efficiency_plot(df, df_mat, selected_sections, option_mat, section_lb_values, use_global_lb=False, global_lb=6.0):
    """สร้างกราฟแสดงประสิทธิภาพของหลายหน้าตัด"""
    try:
        fig = go.Figure()
        
        # เก็บข้อมูล
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
        
        # สร้าง subplot
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Design Moment Capacity', 'Unit Weight', 
                          'Efficiency Ratio', 'Capacity Utilization'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        sections = [d['Section'] for d in sections_data]
        colors = px.colors.qualitative.Set3[:len(sections)]
        
        # Plot 1: Design Moment Capacity
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
        
        # Plot 2: Weight
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
        
        # Plot 3: Efficiency
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
        
        # Plot 4: Capacity Ratio
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
        
        # Update layout
        fig.update_layout(
            height=700,
            showlegend=False,
            title_text="📊 Multi-Section Performance Dashboard"
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="φMn (t⋅m)", row=1, col=1)
        fig.update_yaxes(title_text="Weight (kg/m)", row=1, col=2)
        fig.update_yaxes(title_text="Efficiency", row=2, col=1)
        fig.update_yaxes(title_text="Capacity Ratio", row=2, col=2)
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating efficiency plot: {e}")
        return None


# Validation functions
def validate_section_data(df_selected):
    """ตรวจสอบความถูกต้องของข้อมูลที่เลือก"""
    required_columns = ['Section']
    missing_columns = [col for col in required_columns if col not in df_selected.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {missing_columns}"
    
    return True, "Data validation passed"

def safe_analysis(section, df, df_mat, option_mat, lb_value):
    """ทำการวิเคราะห์อย่างปลอดภัยพร้อมการจัดการ Error"""
    try:
        if section not in df.index:
            return None, f"Section {section} not found in database"
        
        result = F2(df, df_mat, section, option_mat, lb_value)
        return result, None
    except Exception as e:
        return None, f"Analysis error for {section}: {str(e)}"

def standardize_column_names(df):
    """แปลงชื่อ column ให้เป็นมาตรฐาน"""
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
    """ดึงค่า weight อย่างปลอดภัย"""
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

# Helper Functions for Steel Analysis
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

def create_safe_subplot_dashboard(plot_data, comparison_results):
    """สร้าง subplot อย่างปลอดภัย"""
    try:
        if not plot_data['sections'] or len(plot_data['sections']) == 0:
            st.warning("⚠️ No data available for plotting")
            return None
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Moment Capacity vs Lb Used', 'Weight vs Efficiency', 
                          'Capacity Utilization', 'Performance Ranking'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Plot 1: Moment vs Lb
        if len(plot_data['sections']) > 0:
            colors = px.colors.qualitative.Set3[:len(plot_data['sections'])]
            for i, (section, lb, mn) in enumerate(zip(plot_data['sections'], plot_data['lb_used'], plot_data['phi_Mn'])):
                if mn is not None and lb is not None:
                    fig.add_trace(
                        go.Scatter(x=[lb], y=[mn], mode='markers+text', 
                                 name=section, text=[section], textposition="top center",
                                 marker=dict(size=12, color=colors[i % len(colors)])),
                        row=1, col=1
                    )
        
        # Plot 2: Weight vs Efficiency
        valid_weights = [w for w in plot_data['weight'] if w is not None and w > 0]
        valid_efficiency = [e for e in plot_data['efficiency'] if e is not None and e > 0]
        valid_sections = [s for i, s in enumerate(plot_data['sections']) 
                         if plot_data['weight'][i] is not None and plot_data['weight'][i] > 0 
                         and plot_data['efficiency'][i] is not None and plot_data['efficiency'][i] > 0]
        
        if valid_weights and valid_efficiency:
            fig.add_trace(
                go.Scatter(x=valid_weights, y=valid_efficiency,
                         mode='markers+text', text=valid_sections,
                         textposition="top center", name='Weight vs Efficiency',
                         marker=dict(size=10, color='blue')),
                row=1, col=2
            )
        
        # Plot 3: Capacity utilization
        if comparison_results:
            capacity_ratios = [r.get('Capacity Ratio', 0) for r in comparison_results if r.get('Capacity Ratio') is not None]
            sections_with_ratios = [r.get('Section', '') for r in comparison_results if r.get('Capacity Ratio') is not None]
            
            if capacity_ratios and sections_with_ratios:
                fig.add_trace(
                    go.Bar(x=sections_with_ratios, y=capacity_ratios,
                           name='Mn/Mp Ratio', marker_color='orange'),
                    row=2, col=1
                )
        
        # Plot 4: Performance ranking
        valid_efficiency_for_ranking = [e for e in plot_data['efficiency'] if e is not None and e > 0]
        valid_sections_for_ranking = [s for i, s in enumerate(plot_data['sections']) 
                                    if plot_data['efficiency'][i] is not None and plot_data['efficiency'][i] > 0]
        
        if valid_efficiency_for_ranking and valid_sections_for_ranking:
            fig.add_trace(
                go.Bar(x=valid_sections_for_ranking, y=valid_efficiency_for_ranking,
                       name='Efficiency Ranking', marker_color='purple'),
                row=2, col=2
            )
        
        fig.update_layout(height=800, showlegend=False, 
                         title_text="Steel Section Analysis Dashboard")
        fig.update_xaxes(tickangle=45)
        
        return fig
        
    except Exception as e:
        st.error(f"Error creating subplot: {e}")
        return None

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
        if section_list:
            option = st.selectbox("🔩 Choose Steel Section:", section_list, index=0 if option in section_list else 0)
        if section_list_mat:
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
        if option and option in df.index:
            try:
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
            except Exception as e:
                st.error(f"Error creating visualization: {e}")
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
        try:
            filtered_data = df.copy()
            filtered_data = filtered_data[filtered_data["Zx [cm3]"] >= zx_min]
            if depth_min > 0:
                filtered_data = filtered_data[filtered_data["d [mm]"] >= depth_min]
            if weight_max < 1000:
                # Use safe_get_weight function or find correct column name
                weight_col = None
                for col in ['Unit Weight [kg/m]', 'w [kg/m]', 'Weight [kg/m]']:
                    if col in filtered_data.columns:
                        weight_col = col
                        break
                
                if weight_col:
                    filtered_data = filtered_data[filtered_data[weight_col] <= weight_max]

            # Reset index to make Section a column
            filtered_data_display = filtered_data.reset_index()
            
            st.markdown(f"**📋 Filtered Results: {len(filtered_data_display)} sections**")

            # Configure AgGrid
            gb = GridOptionsBuilder.from_dataframe(filtered_data_display)
            gb.configure_selection("multiple", use_checkbox=True, groupSelectsChildren=False)
            gb.configure_grid_options(enableCellTextSelection=True)
            gb.configure_column("Section", headerCheckboxSelection=True)
            grid_options = gb.build()

            # Display grid
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
                
                # Handle selected rows
                selected_rows = grid_response.get("selected_rows", [])
                
                if selected_rows is not None and len(selected_rows) > 0:
                    # Convert to DataFrame and check columns
                    df_selected = pd.DataFrame(selected_rows)
                    
                    # Check if 'Section' column exists
                    if 'Section' in df_selected.columns:
                        # Store in session state
                        st.session_state.selected_sections = df_selected.to_dict('records')
                        st.success(f"✅ Selected {len(selected_rows)} sections for analysis")
                        
                        # Show complete summary
                        with st.expander("📋 Selected Sections Summary", expanded=True):
                            # Select important columns
                            summary_cols = ['Section', 'Zx [cm3]', 'Zy [cm3]', 'd [mm]', 'bf [mm]', 
                                          'tf [mm]', 'tw [mm]', 'Unit Weight [kg/m]', 'Sx [cm3]', 
                                          'Sy [cm3]', 'Ix [cm4]', 'Iy [cm4]']
                            available_cols = [col for col in summary_cols if col in df_selected.columns]
                            
                            if available_cols:
                                st.dataframe(df_selected[available_cols], use_container_width=True)
                                
                                # Show individual Lb inputs
                                st.markdown("### 📏 Individual Unbraced Length Settings")
                                
                                # Create dictionary to store Lb for each section
                                if 'section_lb_values' not in st.session_state:
                                    st.session_state.section_lb_values = {}
                                
                                # Create input for Lb for each section
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

with tab4:
    st.markdown('<h2 class="sub-header">Comparative Analysis Dashboard</h2>', unsafe_allow_html=True)
    
    # Check selected sections
    has_selected_sections = False
    selected_sections_data = []
    
    if 'selected_sections' in st.session_state and st.session_state.selected_sections:
        selected_sections_data = st.session_state.selected_sections
        has_selected_sections = True
    
    if has_selected_sections:
        df_selected = pd.DataFrame(selected_sections_data)
        
        # Fix column names
        df = standardize_column_names(df)
        
        # Input controls for analysis
        col_input1, col_input2, col_input3 = st.columns(3)
        
        with col_input1:
            # Global Lb setting
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
        
        # Check if Section column exists
        if 'Section' in df_selected.columns and len(df_selected) > 0:
            section_names = df_selected["Section"].unique()
            
            # Initialize results storage
            comparison_results = []
            plot_data = {'sections': [], 'Mp': [], 'Mn': [], 'phi_Mn': [], 'weight': [], 
                        'efficiency': [], 'lb_used': []}
            
            # Analyze each section
            for section in section_names:
                try:
                    if section not in df.index:
                        st.warning(f"⚠️ Section {section} not found in database")
                        continue
                    
                    # Determine Lb to use
                    if use_global_lb:
                        lb_to_use = global_lb
                    else:
                        lb_to_use = st.session_state.section_lb_values.get(section, 6.0)
                    
                    # Perform F2 analysis
                    Mn, Lb_calc, Lp, Lr, Mp, Mni, Lni, Case = F2(df, df_mat, section, option_mat, lb_to_use)
                    
                    Fib = 0.9
                    FibMn = Fib * Mn
                    
                    # Get weight safely
                    weight = safe_get_weight(df, section)
                    
                    # Calculate efficiency
                    efficiency = FibMn / weight if weight > 0 else 0
                    
                    # Store results (check for None values)
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
                    
                    # Store plot data (check for None values)
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
            
            if comparison_results:
                results_df = pd.DataFrame(comparison_results)
                results_df = results_df.sort_values('Efficiency', ascending=False)
                
                # Display enhanced results table
                st.markdown("### 📊 Enhanced Comparative Analysis Results")
                
                # Create color-coded styling
                def highlight_performance(s):
                    if s.name == 'Efficiency':
                        max_val = s.max()
                        return ['background-color: #d4edda; font-weight: bold' if v == max_val else 
                               'background-color: #fff3cd' if v >= max_val * 0.9 else '' for v in s]
                    elif s.name == 'φMn (t⋅m)':
                        max_val = s.max()
                        return ['background-color: #d4edda; font-weight: bold' if v == max_val else 
                               'background-color: #fff3cd' if v >= max_val * 0.9 else '' for v in s]
                    elif s.name == 'Weight (kg/m)':
                        min_val = s.min()
                        return ['background-color: #d4edda; font-weight: bold' if v == min_val else 
                               'background-color: #fff3cd' if v <= min_val * 1.1 else '' for v in s]
                    elif s.name == 'Capacity Ratio':
                        return ['background-color: #d4edda' if v >= 0.9 else
                               'background-color: #fff3cd' if v >= 0.7 else
                               'background-color: #f8d7da' for v in s]
                    return [''] * len(s)
                
                styled_results = results_df.style.apply(highlight_performance, axis=0)
                st.dataframe(styled_results, use_container_width=True)
                
                # Enhanced plotting section
                st.markdown("### 📈 Enhanced Visual Analysis")
                
                if analysis_type == "Detailed Comparison":
                    fig = create_safe_subplot_dashboard(plot_data, comparison_results)
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("❌ Unable to create detailed comparison chart")
                
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
                
                elif analysis_type == "Weight Comparison":
                    try:
                        valid_weights = [w for w in plot_data['weight'] if w > 0]
                        valid_sections = [s for i, s in enumerate(plot_data['sections']) if plot_data['weight'][i] > 0]
                        
                        if valid_weights and valid_sections:
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=valid_sections,
                                y=valid_weights,
                                name='Weight',
                                marker_color='orange',
                                text=[f'{v:.1f}' for v in valid_weights],
                                textposition='auto'
                            ))
                            fig.update_layout(
                                title="Unit Weight Comparison",
                                xaxis_title="Steel Sections",
                                yaxis_title="Weight (kg/m)",
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("⚠️ No valid weight data for comparison")
                    except Exception as e:
                        st.error(f"Error creating weight comparison chart: {e}")
                
                elif analysis_type == "Efficiency Ratio":
                    try:
                        valid_efficiency = [e for e in plot_data['efficiency'] if e > 0]
                        valid_sections = [s for i, s in enumerate(plot_data['sections']) if plot_data['efficiency'][i] > 0]
                        
                        if valid_efficiency and valid_sections:
                            fig = go.Figure()
                            fig.add_trace(go.Bar(
                                x=valid_sections,
                                y=valid_efficiency,
                                name='Efficiency',
                                marker_color='green',
                                text=[f'{v:.3f}' for v in valid_efficiency],
                                textposition='auto'
                            ))
                            fig.update_layout(
                                title="Efficiency Ratio (φMn/Weight)",
                                xaxis_title="Steel Sections",
                                yaxis_title="Efficiency (t⋅m)/(kg/m)",
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("⚠️ No valid efficiency data for comparison")
                    except Exception as e:
                        st.error(f"Error creating efficiency chart: {e}")
                
                elif analysis_type == "Multi-Section Moment Curve":
                    st.markdown("#### 🔧 Multi-Section Moment Capacity vs Unbraced Length")
                    
                    # สร้างกราฟเปรียบเทียบ
                    fig, legend_info = create_multi_section_comparison_plot(
                        df, df_mat, section_names, option_mat, 
                        st.session_state.section_lb_values, use_global_lb, 
                        global_lb if use_global_lb else None
                    )
                    
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # ✅ เพิ่มตารางสรุป Lp และ Lr ของทุก section
                        st.markdown("#### 📐 Critical Lengths Summary (Lp & Lr)")
                        
                        # สร้างข้อมูลสำหรับตาราง Lp และ Lr
                        critical_lengths_data = []
                        
                        for section in section_names:
                            try:
                                if section not in df.index:
                                    continue
                                
                                current_lb = global_lb if use_global_lb else st.session_state.section_lb_values.get(section, 6.0)
                                Mn, _, Lp, Lr, Mp, _, _, Case = F2(df, df_mat, section, option_mat, current_lb)
                                
                                critical_lengths_data.append({
                                    'Section': section,
                                    'Lp (m)': f"{Lp:.2f}",
                                    'Lr (m)': f"{Lr:.2f}",
                                    'Current Lb (m)': f"{current_lb:.2f}",
                                    'Zone': (
                                        "🟢 Zone 1 (Lb < Lp)" if current_lb < Lp else
                                        "🟡 Zone 2 (Lp ≤ Lb < Lr)" if Lp <= current_lb < Lr else
                                        "🔴 Zone 3 (Lb ≥ Lr)"
                                    ),
                                    'Governing Case': Case,
                                    'Capacity Ratio': f"{(Mn/Mp):.3f}" if Mp > 0 else "N/A"
                                })
                                
                            except Exception as e:
                                critical_lengths_data.append({
                                    'Section': section,
                                    'Lp (m)': "Error",
                                    'Lr (m)': "Error", 
                                    'Current Lb (m)': f"{current_lb:.2f}" if 'current_lb' in locals() else "N/A",
                                    'Zone': "❌ Error",
                                    'Governing Case': "Error",
                                    'Capacity Ratio': "N/A"
                                })
                        
                        if critical_lengths_data:
                            critical_df = pd.DataFrame(critical_lengths_data)
                            
                            # จัดกลุ่มตาม Zone
                            col_table1, col_table2 = st.columns([2, 1])
                            
                            with col_table1:
                                # แสดงตารางหลัก
                                st.dataframe(critical_df, use_container_width=True, height=300)
                            
                            with col_table2:
                                # สถิติสรุป
                                st.markdown("##### 📊 Zone Distribution")
                                
                                zone_counts = critical_df['Zone'].value_counts()
                                total_sections = len(critical_df)
                                
                                for zone, count in zone_counts.items():
                                    percentage = (count / total_sections) * 100
                                    st.write(f"{zone}: {count} ({percentage:.0f}%)")
                                
                                # แสดงช่วงของ Lp และ Lr
                                try:
                                    lp_values = [float(x) for x in critical_df['Lp (m)'] if x != "Error"]
                                    lr_values = [float(x) for x in critical_df['Lr (m)'] if x != "Error"]
                                    
                                    if lp_values and lr_values:
                                        st.markdown("##### 📏 Critical Length Ranges")
                                        st.write(f"**Lp Range**: {min(lp_values):.2f} - {max(lp_values):.2f} m")
                                        st.write(f"**Lr Range**: {min(lr_values):.2f} - {max(lr_values):.2f} m")
                                        st.write(f"**Average Lp**: {sum(lp_values)/len(lp_values):.2f} m")
                                        st.write(f"**Average Lr**: {sum(lr_values)/len(lr_values):.2f} m")
                                except:
                                    st.warning("Unable to calculate statistics")
                        
                        # แสดงข้อมูลสรุปเดิม
                        if legend_info:
                            st.markdown("#### 📋 Section Summary")
                            
                            summary_df = pd.DataFrame(legend_info)
                            summary_df = summary_df.round(3)
                            
                            # เรียงตามประสิทธิภาพ
                            summary_df = summary_df.sort_values('efficiency', ascending=False)
                            
                            st.dataframe(summary_df, use_container_width=True)
                            
                            # แสดงผู้ชนะ
                            if len(summary_df) > 0:
                                best_section = summary_df.iloc[0]
                                st.success(f"🏆 **Best Performance**: {best_section['section']} with efficiency {best_section['efficiency']:.3f}")
                        
                        # เพิ่มข้อมูลเปรียบเทียบแบบ interactive
                        with st.expander("🔍 Interactive Analysis Tools", expanded=False):
                            col_analysis1, col_analysis2 = st.columns(2)
                            
                            with col_analysis1:
                                st.markdown("##### 📊 Section Performance Metrics")
                                if legend_info:
                                    performance_df = pd.DataFrame(legend_info)
                                    
                                    # แสดงสถิติ
                                    avg_efficiency = performance_df['efficiency'].mean()
                                    max_mn = performance_df['current_mn'].max()
                                    min_lb = performance_df['current_lb'].min()
                                    max_lb = performance_df['current_lb'].max()
                                    
                                    st.metric("Average Efficiency", f"{avg_efficiency:.3f}")
                                    st.metric("Max Moment Capacity", f"{max_mn:.2f} t⋅m")
                                    st.write(f"**Lb Range**: {min_lb:.1f} - {max_lb:.1f} m")
                            
                            with col_analysis2:
                                st.markdown("##### 🎯 Design Recommendations")
                                if legend_info:
                                    sorted_sections = sorted(legend_info, key=lambda x: x['efficiency'], reverse=True)
                                    
                                    st.write("**Top 3 Recommendations:**")
                                    for i, section_info in enumerate(sorted_sections[:3]):
                                        rank_emoji = ["🥇", "🥈", "🥉"][i]
                                        st.write(f"{rank_emoji} **{section_info['section']}** - Efficiency: {section_info['efficiency']:.3f}")
                                        
                                # ✅ เพิ่มส่วนแนะนำตาม Lp, Lr
                                if critical_lengths_data:
                                    st.markdown("##### 💡 Critical Length Insights")
                                    
                                    # หา section ที่มี Lp และ Lr สูงสุด/ต่ำสุด
                                    try:
                                        valid_data = [d for d in critical_lengths_data if d['Lp (m)'] != "Error"]
                                        if valid_data:
                                            max_lp_section = max(valid_data, key=lambda x: float(x['Lp (m)']))
                                            min_lp_section = min(valid_data, key=lambda x: float(x['Lp (m)']))
                                            max_lr_section = max(valid_data, key=lambda x: float(x['Lr (m)']))
                                            
                                            st.write(f"**🔹 Highest Lp**: {max_lp_section['Section']} ({max_lp_section['Lp (m)']} m)")
                                            st.write(f"**🔸 Lowest Lp**: {min_lp_section['Section']} ({min_lp_section['Lp (m)']} m)")
                                            st.write(f"**🔷 Highest Lr**: {max_lr_section['Section']} ({max_lr_section['Lr (m)']} m)")
                                    except:
                                        st.write("Unable to analyze critical lengths")
                    else:
                        st.error("❌ Unable to create multi-section comparison chart")
                
                elif analysis_type == "Multi-Section Dashboard":
                    st.markdown("#### 📊 Multi-Section Performance Dashboard")
                    
                    fig = create_multi_section_efficiency_plot(
                        df, df_mat, section_names, option_mat,
                        st.session_state.section_lb_values, use_global_lb,
                        global_lb if use_global_lb else None
                    )
                    
                    if fig is not None:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # เพิ่มการแสดงข้อมูลเปรียบเทียบแบบละเอียด
                        col_summary1, col_summary2 = st.columns(2)
                        
                        with col_summary1:
                            st.markdown("##### 🎯 Key Insights")
                            # สร้างข้อมูลสำหรับ insights
                            insights_data = []
                            for section in section_names:
                                try:
                                    if section not in df.index:
                                        continue
                                    
                                    current_lb = global_lb if use_global_lb else st.session_state.section_lb_values.get(section, 6.0)
                                    Mn, _, Lp, Lr, Mp, _, _, Case = F2(df, df_mat, section, option_mat, current_lb)
                                    weight = safe_get_weight(df, section)
                                    efficiency = (0.9 * Mn) / weight if weight > 0 else 0
                                    
                                    insights_data.append({
                                        'Section': section,
                                        'Efficiency': efficiency,
                                        'Weight': weight,
                                        'φMn': 0.9 * Mn,
                                        'Case': Case
                                    })
                                except:
                                    continue
                            
                            if insights_data:
                                insights_df = pd.DataFrame(insights_data)
                                
                                # หาค่าที่ดีที่สุด
                                best_efficiency = insights_df.loc[insights_df['Efficiency'].idxmax()]
                                lightest = insights_df.loc[insights_df['Weight'].idxmin()]  
                                strongest = insights_df.loc[insights_df['φMn'].idxmax()]
                                
                                st.success(f"**🏆 Most Efficient**: {best_efficiency['Section']} ({best_efficiency['Efficiency']:.3f})")
                                st.info(f"**⚖️ Lightest**: {lightest['Section']} ({lightest['Weight']:.1f} kg/m)")
                                st.warning(f"**💪 Strongest**: {strongest['Section']} ({strongest['φMn']:.2f} t⋅m)")
                                
                                # แสดงสถิติเพิ่มเติม
                                st.markdown("**📈 Statistics:**")
                                avg_eff = insights_df['Efficiency'].mean()
                                std_eff = insights_df['Efficiency'].std()
                                st.write(f"- Average Efficiency: {avg_eff:.3f} ± {std_eff:.3f}")
                                st.write(f"- Efficiency Range: {insights_df['Efficiency'].min():.3f} - {insights_df['Efficiency'].max():.3f}")
                        
                        with col_summary2:
                            st.markdown("##### ⚙️ Analysis Settings & Status")
                            if use_global_lb:
                                st.info(f"**🌐 Global Lb**: {global_lb} m")
                            else:
                                st.info("**🔧 Individual Lb settings**:")
                                for section in section_names[:5]:  # แสดงแค่ 5 อันแรก
                                    lb_val = st.session_state.section_lb_values.get(section, 6.0)
                                    st.write(f"- {section}: {lb_val} m")
                                
                                if len(section_names) > 5:
                                    st.write(f"... และอีก {len(section_names) - 5} หน้าตัด")
                            
                            # แสดงสถานะการวิเคราะห์
                            st.markdown("**📊 Analysis Status:**")
                            st.write(f"- Sections analyzed: {len(section_names)}")
                            st.write(f"- Material grade: {option_mat}")
                            st.write(f"- Analysis method: F2 (AISC)")
                            
                            # แสดง governing cases
                            if insights_data:
                                case_counts = pd.Series([d['Case'] for d in insights_data]).value_counts()
                                st.markdown("**🎯 Governing Cases:**")
                                for case, count in case_counts.items():
                                    percentage = (count / len(insights_data)) * 100
                                    st.write(f"- {case}: {count} ({percentage:.0f}%)")
                        
                        # เพิ่มส่วนวิเคราะห์เทรนด์
                        with st.expander("📈 Trend Analysis", expanded=False):
                            if insights_data and len(insights_data) > 1:
                                trend_df = pd.DataFrame(insights_data).sort_values('Weight')
                                
                                # สร้างกราฟ trend
                                fig_trend = go.Figure()
                                
                                # Efficiency vs Weight
                                fig_trend.add_trace(go.Scatter(
                                    x=trend_df['Weight'],
                                    y=trend_df['Efficiency'],
                                    mode='markers+lines',
                                    name='Efficiency Trend',
                                    text=trend_df['Section'],
                                    hovertemplate='<b>%{text}</b><br>Weight: %{x:.1f} kg/m<br>Efficiency: %{y:.3f}<extra></extra>'
                                ))
                                
                                fig_trend.update_layout(
                                    title="Efficiency vs Weight Trend",
                                    xaxis_title="Weight (kg/m)",
                                    yaxis_title="Efficiency",
                                    height=400
                                )
                                
                                st.plotly_chart(fig_trend, use_container_width=True)
                                
                                # วิเคราะห์ correlation
                                correlation = trend_df['Weight'].corr(trend_df['Efficiency'])
                                if correlation < -0.5:
                                    st.success(f"💡 **Strong negative correlation** (r={correlation:.3f}): Lighter sections tend to be more efficient")
                                elif correlation > 0.5:
                                    st.warning(f"⚠️ **Strong positive correlation** (r={correlation:.3f}): Heavier sections tend to be more efficient")
                                else:
                                    st.info(f"📊 **Weak correlation** (r={correlation:.3f}): Weight and efficiency are not strongly related")
                    else:
                        st.error("❌ Unable to create multi-section dashboard")
                
                # Export functionality
                if show_details:
                    st.markdown("### 📤 Export Options")
                    
                    # Create export data
                    export_data = results_df.copy()
                    csv_data = export_data.to_csv(index=False)
                    
                    col_export1, col_export2, col_export3 = st.columns(3)
                    
                    with col_export1:
                        st.download_button(
                            label="📊 Download CSV Report",
                            data=csv_data,
                            file_name=f"steel_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col_export2:
                        # Create detailed report
                        report_text = f"""
# Steel Section Comparative Analysis Report

## Analysis Parameters
- Analysis Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
- Number of Sections Analyzed: {len(results_df)}
- Material Grade: {option_mat}
- Analysis Type: {analysis_type}

## Summary Results
Best Overall Performance: {results_df.iloc[0]['Section']}
- Efficiency: {results_df.iloc[0]['Efficiency']:.3f} t⋅m/(kg/m)
- Design Moment: {results_df.iloc[0]['φMn (t⋅m)']:.2f} t⋅m
- Unbraced Length Used: {results_df.iloc[0]['Lb Used (m)']} m

## Individual Lb Settings
{chr(10).join([f"- {row['Section']}: {row['Lb Used (m)']} m" for _, row in results_df.iterrows()])}

## Detailed Results
{results_df.to_string(index=False)}

## Analysis Notes
- All calculations based on AISC Steel Construction Manual
- F2 analysis for doubly symmetric compact I-shaped members
- Safety factor (φ) = 0.9 applied to nominal moment capacity
"""
                        
                        st.download_button(
                            label="📋 Download Report",
                            data=report_text,
                            file_name=f"steel_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain"
                        )
                    
                    with col_export3:
                        # สร้าง summary JSON
                        summary_data = {
                            "analysis_info": {
                                "date": pd.Timestamp.now().isoformat(),
                                "sections_analyzed": len(results_df),
                                "material_grade": option_mat,
                                "analysis_type": analysis_type
                            },
                            "best_performance": {
                                "section": results_df.iloc[0]['Section'],
                                "efficiency": float(results_df.iloc[0]['Efficiency']),
                                "design_moment": float(results_df.iloc[0]['φMn (t⋅m)']),
                                "weight": float(results_df.iloc[0]['Weight (kg/m)'])
                            },
                            "sections_data": results_df.to_dict('records')
                        }
                        
                        import json
                        json_data = json.dumps(summary_data, indent=2, ensure_ascii=False)
                        
                        st.download_button(
                            label="🔧 Download JSON",
                            data=json_data,
                            file_name=f"steel_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                
                # Debug information
                with st.expander("🔍 Debug Information", expanded=False):
                    st.write("**Available columns in dataframe:**")
                    st.write(df.columns.tolist())
                    
                    st.write("**Plot data structure:**")
                    for key, value in plot_data.items():
                        st.write(f"- {key}: {len(value)} items")
                    
                    st.write("**Weight columns found:**")
                    weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'kg' in col.lower()]
                    st.write(weight_cols)
                    
                    st.write("**Session state keys:**")
                    st.write(list(st.session_state.keys()))
                    
                    if 'section_lb_values' in st.session_state:
                        st.write("**Individual Lb values:**")
                        st.write(st.session_state.section_lb_values)
                
            else:
                st.warning("⚠️ No analysis results available")
        else:
            st.error("❌ Selected data does not contain 'Section' column or no sections available")
    else:
        st.info("ℹ️ Please select sections in the 'Section Selection' tab first")
        
        # Show instructions
        st.markdown("""
        ### 📖 How to use:
        1. Go to **Section Selection** tab
        2. Apply filters to narrow down sections
        3. Select multiple sections using checkboxes
        4. Set individual Lb values for each section
        5. Come back to this tab for comparative analysis
        
        ### 🔧 Features Available:
        - **Standard Analysis**: Moment Capacity, Weight, Efficiency comparisons
        - **🆕 Multi-Section Moment Curve**: Interactive curve comparison like Tab 2
        - **🆕 Multi-Section Dashboard**: Comprehensive 4-chart dashboard
        - **🆕 Critical Lengths Table**: Shows Lp and Lr of all selected sections
        - **Advanced Analytics**: Trend analysis, correlation studies
        - **Export Options**: CSV, detailed reports, JSON data
        
        ### 🚀 Troubleshooting:
        - If weight values show as 0, check the column names in debug section
        - If plots don't appear, ensure you have selected valid sections
        - For Multi-Section analysis, at least 2 sections are recommended
        - Check individual Lb settings in Tab 3 if results seem unexpected
        """)

