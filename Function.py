"""
Sa Design Response Spectrum Generator
อ้างอิง: มยผ. 1301/1302-61 หน้าที่ 25-26 (พื้นที่ทั่วประเทศ ยกเว้นแอ่งกรุงเทพ)

รันด้วยคำสั่ง:
    pip install streamlit numpy plotly pandas
    streamlit run spectrum_app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Sa Design Response Spectrum", layout="wide")

# ----------------------------------------------------------------------
# ฟังก์ชันคำนวณ Sa สำหรับแต่ละวิธี
# ----------------------------------------------------------------------

def sa_equivalent_static(T: np.ndarray, SDS: float, SD1: float):
    """วิธีแรงสถิตเทียบเท่า (รูปที่ 1.4-1 / 1.4-2)"""
    T = np.asarray(T, dtype=float)
    Sa = np.zeros_like(T)

    if SD1 <= SDS:
        # รูปที่ 1.4-1
        Ts = SD1 / SDS
        T0 = 0.0
        mask1 = T <= Ts
        Sa[mask1] = SDS
        mask2 = ~mask1
        Sa[mask2] = SD1 / T[mask2]
    else:
        # รูปที่ 1.4-2
        T0, Ts = 0.2, 1.0
        mask1 = T <= T0
        mask2 = (T > T0) & (T <= Ts)
        mask3 = T > Ts
        Sa[mask1] = SDS
        Sa[mask2] = SDS + (SD1 - SDS) * (T[mask2] - T0) / (Ts - T0)
        Sa[mask3] = SD1 / T[mask3]

    return Sa, T0, Ts


def sa_dynamic(T: np.ndarray, SDS: float, SD1: float):
    """วิธีเชิงพลศาสตร์ (รูปที่ 1.4-3 / 1.4-4)"""
    T = np.asarray(T, dtype=float)
    Sa = np.zeros_like(T)

    if SD1 <= SDS:
        # รูปที่ 1.4-3
        Ts = SD1 / SDS
        T0 = 0.2 * Ts
        mask1 = T <= T0
        mask2 = (T > T0) & (T <= Ts)
        mask3 = T > Ts
        # สมการ 1.4-5
        Sa[mask1] = SDS * (3.88 * (T[mask1] / Ts) + 0.4)
        Sa[mask2] = SDS
        Sa[mask3] = SD1 / T[mask3]
    else:
        # รูปที่ 1.4-4
        T0, Ts = 0.2, 1.0
        mask1 = T <= T0
        mask2 = (T > T0) & (T <= Ts)
        mask3 = T > Ts
        Sa[mask1] = 0.4 * SDS + (SDS - 0.4 * SDS) * (T[mask1] / T0)
        Sa[mask2] = SDS + (SD1 - SDS) * (T[mask2] - T0) / (Ts - T0)
        Sa[mask3] = SD1 / T[mask3]

    return Sa, T0, Ts


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------

st.title("กราฟความเร่งตอบสนองเชิงสเปกตรัมสำหรับการออกแบบ (Sa Design Response Spectrum)")
st.caption("อ้างอิง: มยผ. 1301/1302-61 หน้าที่ 25–26 (พื้นที่ทั่วประเทศ ยกเว้นแอ่งกรุงเทพ)")

with st.sidebar:
    st.header("พารามิเตอร์นำเข้า")
    SDS = st.number_input("SDS (g)", min_value=0.001, value=0.451, step=0.001, format="%.3f")
    SD1 = st.number_input("SD1 (g)", min_value=0.001, value=0.233, step=0.001, format="%.3f")
    T_max = st.number_input("คาบการสั่นสูงสุดของกราฟ T_max (วินาที)", min_value=1.0, value=6.0, step=0.5)
    n_points = st.slider("ความละเอียดของเส้นกราฟ (จำนวนจุด)", 100, 2000, 600)

    case_label = "SD1 ≤ SDS  →  รูปที่ 1.4-1 / 1.4-3" if SD1 <= SDS else "SD1 > SDS  →  รูปที่ 1.4-2 / 1.4-4"
    st.info(f"**กรณีที่ตรวจพบ:** {case_label}")

# ช่วงคาบการสั่น (เริ่มที่ค่าน้อย ๆ ที่ไม่ใช่ 0 เป๊ะ เพื่อเลี่ยงหารด้วยศูนย์ในบาง branch)
T = np.linspace(1e-6, T_max, n_points)

Sa_static, T0_static, Ts_static = sa_equivalent_static(T, SDS, SD1)
Sa_dynamic, T0_dyn, Ts_dyn = sa_dynamic(T, SDS, SD1)

# ----------------------------------------------------------------------
# ตารางสรุปพารามิเตอร์
# ----------------------------------------------------------------------

col1, col2 = st.columns(2)
with col1:
    st.subheader("วิธีแรงสถิตเทียบเท่า (Equivalent Static)")
    st.table(pd.DataFrame({
        "พารามิเตอร์": ["SDS", "SD1", "T0", "Ts"],
        "ค่า": [f"{SDS:.3f}", f"{SD1:.3f}", f"{T0_static:.3f}", f"{Ts_static:.3f}"],
    }).set_index("พารามิเตอร์"))

with col2:
    st.subheader("วิธีเชิงพลศาสตร์ (Dynamic)")
    st.table(pd.DataFrame({
        "พารามิเตอร์": ["SDS", "SD1", "T0", "Ts"],
        "ค่า": [f"{SDS:.3f}", f"{SD1:.3f}", f"{T0_dyn:.3f}", f"{Ts_dyn:.3f}"],
    }).set_index("พารามิเตอร์"))

# ----------------------------------------------------------------------
# กราฟ
# ----------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs(["วิธีแรงสถิตเทียบเท่า", "วิธีเชิงพลศาสตร์", "เปรียบเทียบทั้งสองวิธี"])


def make_figure(T, Sa, T0, Ts, SDS, SD1, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=T, y=Sa, mode="lines", name="Sa", line=dict(width=3)))

    # จุดหมายสำคัญ
    key_T = sorted(set([0.0, T0, Ts]))
    for t in key_T:
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

    fig.update_layout(
        title=title,
        xaxis_title="คาบการสั่น T (วินาที)",
        yaxis_title="Sa (g)",
        height=520,
        template="plotly_white",
    )
    return fig


with tab1:
    fig1 = make_figure(T, Sa_static, T0_static, Ts_static, SDS, SD1,
                        "วิธีแรงสถิตเทียบเท่า (Equivalent Static Method)")
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = make_figure(T, Sa_dynamic, T0_dyn, Ts_dyn, SDS, SD1,
                        "วิธีเชิงพลศาสตร์ (Dynamic Method)")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=T, y=Sa_static, mode="lines", name="แรงสถิตเทียบเท่า", line=dict(width=3)))
    fig3.add_trace(go.Scatter(x=T, y=Sa_dynamic, mode="lines", name="เชิงพลศาสตร์", line=dict(width=3, dash="dash")))
    fig3.update_layout(
        title="เปรียบเทียบกราฟ Sa ทั้งสองวิธี",
        xaxis_title="คาบการสั่น T (วินาที)",
        yaxis_title="Sa (g)",
        height=520,
        template="plotly_white",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ----------------------------------------------------------------------
# ดาวน์โหลดข้อมูล
# ----------------------------------------------------------------------

st.subheader("ดาวน์โหลดข้อมูลกราฟ")
df_out = pd.DataFrame({
    "T (s)": T,
    "Sa_equivalent_static (g)": Sa_static,
    "Sa_dynamic (g)": Sa_dynamic,
})
csv = df_out.to_csv(index=False).encode("utf-8-sig")
st.download_button("ดาวน์โหลดเป็น CSV", data=csv, file_name="sa_design_spectrum.csv", mime="text/csv")

with st.expander("ดูตารางข้อมูลดิบ"):
    st.dataframe(df_out, use_container_width=True)
