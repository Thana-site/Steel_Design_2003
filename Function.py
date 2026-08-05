"""
Seismic Design Parameter Calculator + Sa Design Response Spectrum
อ้างอิง: มยผ. 1301/1302-61 (พื้นที่ทั่วประเทศ ยกเว้นแอ่งกรุงเทพ)

ข้อมูลตารางดึงมาจาก GitHub:
https://github.com/Thana-site/Steel_Design_2003

รันด้วยคำสั่ง:
    pip install streamlit numpy plotly pandas requests
    streamlit run seismic_design_calculator.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Seismic Design Calculator", layout="wide")

RAW_BASE = "https://raw.githubusercontent.com/Thana-site/Steel_Design_2003/main"

FILES = {
    "ss_s1": "table_1_4-1_Ss_S1_table_EN.csv",
    "fa": "table_1_4-2_site_coefficient_Fa_EN.csv",
    "fv": "table_1_4-3_site_coefficient_Fv_EN.csv",
    "occupancy": "table_1_5-1_occupancy_category_importance_factor_EN.csv",
    "sdc_sds": "table_1_6-1_seismic_design_category_by_SDS_EN.csv",
    "sdc_sd1": "table_1_6-2_seismic_design_category_by_SD1_EN.csv",
    "r_factor": "table_2_3-1_response_modification_factors_EN.csv",
}


@st.cache_data(ttl=3600)
def load_table(name: str) -> pd.DataFrame:
    import requests
    url = f"{RAW_BASE}/{FILES[name]}"
    if name == "occupancy":
        # ไฟล์นี้บนต้นทางมีบรรทัดหนึ่งที่ไม่ได้ครอบ description ด้วย " "
        # ทำให้ pandas.read_csv ตีความจำนวนคอลัมน์ผิด จึงต้อง parse เองแบบ robust
        text = requests.get(url, timeout=15).text
        lines = [l for l in text.strip().split("\n") if l.strip()]
        header = [h.strip() for h in lines[0].split(",")]
        rows = []
        for line in lines[1:]:
            desc, cat, factor = line.rsplit(",", 2)
            rows.append([desc.strip().strip('"'), cat.strip(), factor.strip()])
        return pd.DataFrame(rows, columns=header)
    return pd.read_csv(url)


# ----------------------------------------------------------------------
# Fa / Fv interpolation
# ----------------------------------------------------------------------

FA_BREAKPOINTS = [0.25, 0.5, 0.75, 1.0, 1.25]
FV_BREAKPOINTS = [0.1, 0.2, 0.3, 0.4, 0.5]


def interp_coefficient(df: pd.DataFrame, site_class: str, value: float, breakpoints: list):
    row = df[df["Site Class"] == site_class]
    if row.empty:
        return None
    if site_class == "F":
        return None  # requires site-specific analysis
    coeffs = row.iloc[0, 1:6].astype(float).values
    if value <= breakpoints[0]:
        return float(coeffs[0])
    if value >= breakpoints[-1]:
        return float(coeffs[-1])
    return float(np.interp(value, breakpoints, coeffs))


# ----------------------------------------------------------------------
# Seismic Design Category logic (ตาราง 1.6-1 / 1.6-2)
# ----------------------------------------------------------------------

SDC_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


def sdc_from_sds(sds: float, occ_group: str) -> str:
    if sds < 0.167:
        return "A"
    elif sds < 0.33:
        return "C" if occ_group == "IV" else "B"
    elif sds < 0.50:
        return "D" if occ_group == "IV" else "C"
    else:
        return "D"


def sdc_from_sd1(sd1: float, occ_group: str) -> str:
    if sd1 < 0.067:
        return "A"
    elif sd1 < 0.133:
        return "C" if occ_group == "IV" else "B"
    elif sd1 < 0.20:
        return "D" if occ_group == "IV" else "C"
    else:
        return "D"


# ----------------------------------------------------------------------
# Sa Design Response Spectrum equations (รูปที่ 1.4-1 ถึง 1.4-4)
# ----------------------------------------------------------------------

def sa_equivalent_static(T, SDS, SD1):
    T = np.asarray(T, dtype=float)
    Sa = np.zeros_like(T)
    if SD1 <= SDS:
        Ts = SD1 / SDS
        T0 = 0.0
        m1 = T <= Ts
        Sa[m1] = SDS
        Sa[~m1] = SD1 / T[~m1]
    else:
        T0, Ts = 0.2, 1.0
        m1 = T <= T0
        m2 = (T > T0) & (T <= Ts)
        m3 = T > Ts
        Sa[m1] = SDS
        Sa[m2] = SDS + (SD1 - SDS) * (T[m2] - T0) / (Ts - T0)
        Sa[m3] = SD1 / T[m3]
    return Sa, T0, Ts


def sa_dynamic(T, SDS, SD1):
    T = np.asarray(T, dtype=float)
    Sa = np.zeros_like(T)
    if SD1 <= SDS:
        Ts = SD1 / SDS
        T0 = 0.2 * Ts
        m1 = T <= T0
        m2 = (T > T0) & (T <= Ts)
        m3 = T > Ts
        Sa[m1] = SDS * (3.88 * (T[m1] / Ts) + 0.4)
        Sa[m2] = SDS
        Sa[m3] = SD1 / T[m3]
    else:
        T0, Ts = 0.2, 1.0
        m1 = T <= T0
        m2 = (T > T0) & (T <= Ts)
        m3 = T > Ts
        Sa[m1] = 0.4 * SDS + (SDS - 0.4 * SDS) * (T[m1] / T0)
        Sa[m2] = SDS + (SD1 - SDS) * (T[m2] - T0) / (Ts - T0)
        Sa[m3] = SD1 / T[m3]
    return Sa, T0, Ts


def make_figure(T, Sa, T0, Ts, SDS, SD1, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=T, y=Sa, mode="lines", name="Sa", line=dict(width=3)))
    for t in sorted(set([0.0, T0, Ts])):
        idx = (np.abs(T - t)).argmin()
        fig.add_trace(go.Scatter(
            x=[T[idx]], y=[Sa[idx]], mode="markers+text",
            text=[f"T={T[idx]:.3f}, Sa={Sa[idx]:.3f}"],
            textposition="top center", showlegend=False,
            marker=dict(size=8, color="crimson"),
        ))
    fig.add_hline(y=SDS, line_dash="dot", line_color="gray",
                   annotation_text=f"SDS = {SDS:.3f}", annotation_position="right")
    fig.add_hline(y=SD1, line_dash="dot", line_color="gray",
                   annotation_text=f"SD1 = {SD1:.3f}", annotation_position="right")
    fig.update_layout(title=title, xaxis_title="คาบการสั่น T (วินาที)", yaxis_title="Sa (g)",
                       height=480, template="plotly_white")
    return fig


# ========================================================================
# UI
# ========================================================================

st.title("โปรแกรมคำนวณพารามิเตอร์การออกแบบต้านทานแผ่นดินไหว")
st.caption("อ้างอิง: มยผ. 1301/1302-61 · ข้อมูลตารางจาก github.com/Thana-site/Steel_Design_2003")

try:
    df_ss_s1 = load_table("ss_s1")
    df_fa = load_table("fa")
    df_fv = load_table("fv")
    df_occ = load_table("occupancy")
    df_r = load_table("r_factor")
except Exception as e:
    st.error(f"ไม่สามารถโหลดข้อมูลตารางจาก GitHub ได้: {e}")
    st.stop()

# ---- 1. Location ----
st.header("1. ตำแหน่งที่ตั้งอาคาร → Ss, S1")
c1, c2 = st.columns(2)
with c1:
    province = st.selectbox("จังหวัด (Province)", sorted(df_ss_s1["Province"].unique()))
with c2:
    districts = sorted(df_ss_s1[df_ss_s1["Province"] == province]["District"].unique())
    district = st.selectbox("อำเภอ (District)", districts)

row = df_ss_s1[(df_ss_s1["Province"] == province) & (df_ss_s1["District"] == district)].iloc[0]
Ss, S1 = float(row["Ss"]), float(row["S1"])
st.write(f"**Ss = {Ss:.3f} g**   |   **S1 = {S1:.3f} g**")

# ---- 2. Site Class ----
st.header("2. ประเภทชั้นดิน (Site Class) → Fa, Fv")
site_class = st.selectbox("Site Class", ["A", "B", "C", "D", "E", "F"], index=1)

Fa = interp_coefficient(df_fa, site_class, Ss, FA_BREAKPOINTS)
Fv = interp_coefficient(df_fv, site_class, S1, FV_BREAKPOINTS)

if site_class == "F":
    st.warning("Site Class F ต้องทำการวิเคราะห์การตอบสนองของดินเป็นกรณีๆ ไป (site-specific analysis) — "
               "ไม่สามารถใช้ตาราง Fa/Fv มาตรฐานได้ ผลลัพธ์ด้านล่างจะไม่ถูกคำนวณต่อ")
    st.stop()

st.write(f"**Fa = {Fa:.3f}** (interpolated)   |   **Fv = {Fv:.3f}** (interpolated)")

# ---- 3. SMS, SM1, SDS, SD1 ----
st.header("3. คำนวณ SMS, SM1, SDS, SD1")
SMS = Fa * Ss
SM1 = Fv * S1
SDS = (2 / 3) * SMS
SD1 = (2 / 3) * SM1

df_params = pd.DataFrame({
    "พารามิเตอร์": ["SMS = Fa·Ss", "SM1 = Fv·S1", "SDS = (2/3)·SMS", "SD1 = (2/3)·SM1"],
    "ค่า (g)": [f"{SMS:.4f}", f"{SM1:.4f}", f"{SDS:.4f}", f"{SD1:.4f}"],
})
st.table(df_params.set_index("พารามิเตอร์"))

# ---- 4. Occupancy Category ----
st.header("4. ประเภทความสำคัญของอาคาร (Occupancy Category)")
occ_choice = st.selectbox("เลือกประเภทความสำคัญ", df_occ["Occupancy Category"].tolist())
importance_factor = float(df_occ[df_occ["Occupancy Category"] == occ_choice]["Importance Factor"].iloc[0])
st.write(f"**Importance Factor, Ie = {importance_factor}**")

if occ_choice.startswith("IV"):
    occ_group = "IV"
elif occ_choice.startswith("III"):
    occ_group = "III"
else:
    occ_group = "I_II"

# ---- 5. Seismic Design Category ----
st.header("5. ประเภทการออกแบบต้านทานแผ่นดินไหว (Seismic Design Category)")
sdc1 = sdc_from_sds(SDS, occ_group)
sdc2 = sdc_from_sd1(SD1, occ_group)
sdc_final = max(sdc1, sdc2, key=lambda x: SDC_ORDER[x])

c1, c2, c3 = st.columns(3)
c1.metric("SDC จาก SDS", sdc1)
c2.metric("SDC จาก SD1", sdc2)
c3.metric("SDC ที่ใช้ (ค่าที่รุนแรงกว่า)", sdc_final)

if sdc_final == "A":
    st.success("SDC = A → ไม่ต้องออกแบบต้านทานแผ่นดินไหวตามข้อกำหนดนี้ (ไม่บังคับ)")

# ---- 6. Response Modification Factor ----
st.header("6. ระบบต้านทานแรงด้านข้าง (R, Ω0, Cd)")
system_options = (df_r["Overall Structural System"] + " — " + df_r["Lateral Force-Resisting System"]).tolist()
sel = st.selectbox("เลือกระบบโครงสร้าง", system_options)
sel_row = df_r.iloc[system_options.index(sel)]

sdc_col_map = {"A": None, "B": "SDC_B", "C": "SDC_C", "D": "SDC_D"}
permit_col = sdc_col_map.get(sdc_final)
permit_status = "Permitted (SDC A ไม่บังคับ)" if permit_col is None else sel_row[permit_col]

c1, c2, c3, c4 = st.columns(4)
c1.metric("R", sel_row["R"])
c2.metric("Ω0", sel_row["Omega0"])
c3.metric("Cd", sel_row["Cd"])
c4.metric(f"สถานะที่ SDC {sdc_final}", permit_status if isinstance(permit_status, str) else "-")

if isinstance(permit_status, str) and "Not Permitted" in permit_status:
    st.error(f"⚠️ ระบบนี้ **ไม่อนุญาต** ให้ใช้ที่ SDC {sdc_final} ตามตาราง 2.3-1 กรุณาเลือกระบบอื่น")

# ---- 7. Sa Design Response Spectrum ----
st.header("7. กราฟ Sa Design Response Spectrum")
c1, c2 = st.columns(2)
with c1:
    T_max = st.number_input("คาบการสั่นสูงสุด T_max (วินาที)", min_value=1.0, value=6.0, step=0.5)
with c2:
    n_points = st.slider("ความละเอียดของเส้นกราฟ", 100, 2000, 600)

T = np.linspace(1e-6, T_max, n_points)
Sa_static, T0_s, Ts_s = sa_equivalent_static(T, SDS, SD1)
Sa_dyn, T0_d, Ts_d = sa_dynamic(T, SDS, SD1)

tab1, tab2, tab3 = st.tabs(["วิธีแรงสถิตเทียบเท่า", "วิธีเชิงพลศาสตร์", "เปรียบเทียบ"])
with tab1:
    st.plotly_chart(make_figure(T, Sa_static, T0_s, Ts_s, SDS, SD1,
                                 "วิธีแรงสถิตเทียบเท่า (Equivalent Static)"), use_container_width=True)
with tab2:
    st.plotly_chart(make_figure(T, Sa_dyn, T0_d, Ts_d, SDS, SD1,
                                 "วิธีเชิงพลศาสตร์ (Dynamic)"), use_container_width=True)
with tab3:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=T, y=Sa_static, name="แรงสถิตเทียบเท่า", line=dict(width=3)))
    fig.add_trace(go.Scatter(x=T, y=Sa_dyn, name="เชิงพลศาสตร์", line=dict(width=3, dash="dash")))
    fig.update_layout(xaxis_title="T (s)", yaxis_title="Sa (g)", height=480, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ---- Download ----
st.header("ดาวน์โหลดผลลัพธ์")
df_out = pd.DataFrame({"T (s)": T, "Sa_static (g)": Sa_static, "Sa_dynamic (g)": Sa_dyn})
csv = df_out.to_csv(index=False).encode("utf-8-sig")
st.download_button("ดาวน์โหลดกราฟเป็น CSV", data=csv, file_name="sa_spectrum.csv", mime="text/csv")

with st.expander("สรุปพารามิเตอร์ทั้งหมด"):
    st.json({
        "Province": province, "District": district,
        "Ss": Ss, "S1": S1, "Site Class": site_class,
        "Fa": Fa, "Fv": Fv, "SMS": SMS, "SM1": SM1, "SDS": SDS, "SD1": SD1,
        "Occupancy Category": occ_choice, "Importance Factor": importance_factor,
        "SDC (SDS)": sdc1, "SDC (SD1)": sdc2, "SDC (Final)": sdc_final,
        "Structural System": sel, "R": float(sel_row["R"]), "Omega0": float(sel_row["Omega0"]),
        "Cd": float(sel_row["Cd"]),
    })
