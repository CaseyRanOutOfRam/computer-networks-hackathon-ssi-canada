import streamlit as st
import json
import base64
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta


# ---------------------------------------------------------
# 1. DECODER LOGIC (DDS75-LB Chirpstack V4)
# ---------------------------------------------------------
def decode_dds75_lb_full(fport, data_b64):
    if not data_b64: return []
    bytes_data = list(base64.b64decode(data_b64))
    records = []

    if fport == 2 and len(bytes_data) >= 8:
        if bytes_data[0] & 0x10:  # Multi-Distance Mode
            bat_v = ((bytes_data[0] << 8 | bytes_data[1]) & 0x0FFF) / 1000
            end_index = len(bytes_data) - 4
            for i in range(8, min(48, end_index), 2):
                dist = bytes_data[i] << 8 | bytes_data[i + 1]
                records.append({"Bat": bat_v, "Dist": dist})
        else:  # Standard Mode
            bat_v = ((bytes_data[0] << 8 | bytes_data[1]) & 0x3FFF) / 1000
            records.append({"Bat": bat_v, "Dist": bytes_data[2] << 8 | bytes_data[3]})
    return records


# ---------------------------------------------------------
# 2. DATA LOADING
# ---------------------------------------------------------
PATH = "/Users/caseyr/PycharmProjects/computer-networks-hackathon-ssi-canada/dataset/Dragino DDS75-LB Ultrasonic Distance Sensor/a84041bbbf5946fc/*.json"


@st.cache_data
def load_all_data():
    files = glob.glob(PATH)
    all_m = []
    for f in files:
        with open(f, "r") as file:
            try:
                up = json.load(file)
                decoded = decode_dds75_lb_full(up.get("fPort"), up.get("data"))
                for m in decoded:
                    m["Time"] = pd.to_datetime(up.get("time"))
                    all_m.append(m)
            except:
                continue
    return pd.DataFrame(all_m).sort_values('Time').reset_index(drop=True)


df = load_all_data()

# ---------------------------------------------------------
# 3. APP INTERFACE
# ---------------------------------------------------------
st.set_page_config(page_title="TankView Ultimate", layout="wide")
st.title("TankView | Tank Dashboard")

if not df.empty:
    # --- Sidebar Controls ---
    st.sidebar.header("Calibration")
    TANK_H = st.sidebar.number_input("Tank Height (mm)", value=5000)
    TANK_R = st.sidebar.number_input("Tank Radius (mm)", value=1500)

    playhead = st.sidebar.select_slider(
        "Simulation Timeline",
        options=list(range(len(df))),
        format_func=lambda x: df.iloc[x]['Time'].strftime('%H:%M:%S')
    )

    current_df = df.iloc[:playhead + 1]
    latest = current_df.iloc[-1]
    level_mm = TANK_H - latest['Dist']

    # --- TOP ROW: 3D MODEL & METRICS ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("3D Physical View")
        z = np.linspace(0, TANK_H, 40)
        theta = np.linspace(0, 2 * np.pi, 40)
        theta_grid, z_grid = np.meshgrid(theta, z)
        x_grid = TANK_R * np.cos(theta_grid)
        y_grid = TANK_R * np.sin(theta_grid)

        fig_3d = go.Figure()
        fig_3d.add_trace(go.Surface(x=x_grid, y=y_grid, z=z_grid, opacity=0.1, showscale=False))

        water_h = max(0, min(level_mm, TANK_H))
        w_z = np.linspace(0, water_h, 20)
        w_theta_grid, w_z_grid = np.meshgrid(theta, w_z)
        fig_3d.add_trace(go.Surface(
            x=TANK_R * np.cos(w_theta_grid), y=TANK_R * np.sin(w_theta_grid), z=w_z_grid,
            colorscale=[[0, '#00d1ff'], [1, '#00d1ff']], showscale=False
        ))
        fig_3d.update_layout(scene=dict(zaxis=dict(range=[0, TANK_H])), height=450, margin=dict(l=0, r=0, b=0, t=0))
        st.plotly_chart(fig_3d, use_container_width=True)

    with col_right:
        st.subheader("Live Telemetry")
        m1, m2 = st.columns(2)
        m1.metric("Liquid Level", f"{level_mm} mm")
        m2.metric("Fill %", f"{(level_mm / TANK_H) * 100:.1f}%")

        m3, m4 = st.columns(2)
        m3.metric("Battery Voltage", f"{latest['Bat']:.3f} V")
        m4.metric("Samples", f"{len(current_df)}")

        # Battery Health Logic
        if len(current_df) > 5:
            v_start, v_end = current_df['Bat'].iloc[0], current_df['Bat'].iloc[-1]
            if v_start > v_end:
                st.warning(f"🔋 Battery draining at {((v_start - v_end) / len(current_df)):.6f} V/sample")
            else:
                st.success("🔋 Power Supply Stable")

    # --- BOTTOM ROW: 2D GRAPHS ---
    st.markdown("---")
    st.subheader("📈 Historical Trends")

    # Dual Axis Chart for Distance and Battery
    fig_2d = go.Figure()

    # Level Trend
    fig_2d.add_trace(go.Scatter(
        x=current_df['Time'], y=TANK_H - current_df['Dist'],
        name="Level (mm)", line=dict(color='#00d1ff', width=3), fill='tozeroy'
    ))

    # Battery Trend (On secondary Y-axis)
    fig_2d.add_trace(go.Scatter(
        x=current_df['Time'], y=current_df['Bat'],
        name="Battery (V)", line=dict(color='#ff9f1c', width=2, dash='dot'),
        yaxis="y2"
    ))

    fig_2d.update_layout(
        template="plotly_dark",
        height=400,
        yaxis=dict(title="Level (mm)", side="left"),
        yaxis2=dict(title="Battery (V)", side="right", overlaying="y", range=[2.0, 4.0]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_2d, use_container_width=True)

else:
    st.error("No data found. Ensure JSON files are in the dataset folder.")