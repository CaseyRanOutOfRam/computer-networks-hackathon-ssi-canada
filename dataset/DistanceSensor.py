import streamlit as st
import json
import base64
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time


# ---------------------------------------------------------
# 1. DECODER LOGIC (DDS75-LB Chirpstack V4)
# ---------------------------------------------------------
def decode_dds75_lb(fport, data_b64):
    if not data_b64: return []
    try:
        bytes_data = list(base64.b64decode(data_b64))
    except:
        return []

    records = []
    if fport == 2 and len(bytes_data) >= 8:
        if bytes_data[0] & 0x10:  # Multi-Distance Mode
            bat = ((bytes_data[0] << 8 | bytes_data[1]) & 0x0FFF) / 1000
            end_index = len(bytes_data) - 4
            for i in range(8, min(48, end_index), 2):
                dist = bytes_data[i] << 8 | bytes_data[i + 1]
                records.append({"Bat": bat, "Dist": dist})
        else:  # Standard Mode
            bat = ((bytes_data[0] << 8 | bytes_data[1]) & 0x3FFF) / 1000
            records.append({"Bat": bat, "Dist": bytes_data[2] << 8 | bytes_data[3]})
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
                decoded = decode_dds75_lb(up.get("fPort"), up.get("data"))
                for m in decoded:
                    m["Time"] = pd.to_datetime(up.get("time"))
                    all_m.append(m)
            except:
                continue
    return pd.DataFrame(all_m).sort_values('Time').reset_index(drop=True)


# ---------------------------------------------------------
# 3. INTERFACE SETUP
# ---------------------------------------------------------
st.set_page_config(page_title="TankView AI", layout="wide")
st.title("TankView | Live Tank Dashboard")

df = load_all_data()

# Sidebar Configuration
st.sidebar.header("⚙️ System Config")
TANK_H = st.sidebar.number_input("Tank Height (mm)", value=5000)
TANK_R = st.sidebar.number_input("Tank Radius (mm)", value=1000)
OVERFILL_PCT = st.sidebar.slider("Overfill Alarm (%)", 80, 100, 95)
EMPTY_PCT = st.sidebar.slider("Empty Alarm (%)", 0, 20, 5)

is_live = st.sidebar.toggle("RUN LIVE SIMULATION", value=False)
playback_speed = st.sidebar.select_slider("Speed", options=[0.05, 0.1, 0.3, 0.5], value=0.1)

if 'step' not in st.session_state: st.session_state.step = 0


# ---------------------------------------------------------
# 4. THE FLICKER-FREE FRAGMENT
# ---------------------------------------------------------
@st.fragment(run_every=playback_speed if is_live else None)
def render_dashboard():
    # Update step in session state if live
    if is_live and st.session_state.step < len(df) - 1:
        st.session_state.step += 1

    # Timeline Scrubbing Slider
    st.session_state.step = st.select_slider(
        "Simulation Timeline",
        options=list(range(len(df))),
        value=st.session_state.step,
        format_func=lambda x: df.iloc[x]['Time'].strftime('%H:%M:%S'),
        key="scrubber"
    )

    current_df = df.iloc[:st.session_state.step + 1]
    latest = current_df.iloc[-1]
    level_mm = max(0, TANK_H - latest['Dist'])
    fill_pct = (level_mm / TANK_H) * 100
    volume_liters = (np.pi * (TANK_R ** 2) * level_mm) / 1_000_000

    col1, col2 = st.columns([1.5, 1])

    with col1:
        # 3D MODEL
        theta = np.linspace(0, 2 * np.pi, 30)
        w_z = np.linspace(0, level_mm, 10)
        th_grid, z_grid = np.meshgrid(theta, w_z)
        fig3d = go.Figure(go.Surface(
            x=TANK_R * np.cos(th_grid), y=TANK_R * np.sin(th_grid), z=z_grid,
            colorscale=[[0, '#00d1ff'], [1, '#00d1ff']], showscale=False
        ))
        fig3d.update_layout(scene=dict(zaxis=dict(range=[0, TANK_H])), height=450, margin=dict(l=0, r=0, b=0, t=0))
        st.plotly_chart(fig3d, use_container_width=True)

    with col2:
        st.metric("Liquid Level", f"{level_mm} mm")
        st.metric("Total Volume", f"{volume_liters:.1f} L")
        st.metric("Battery Status", f"{latest['Bat']:.3f} V")

        if fill_pct >= OVERFILL_PCT:
            st.error(f"🚨 OVERFILL ALARM: {fill_pct:.1f}% Full")
        elif fill_pct <= EMPTY_PCT:
            st.error(f"🚨 EMPTY ALARM: {fill_pct:.1f}% Remaining")
        else:
            st.success("✅ Level Status: Nominal")

    # 2D HISTORY
    fig_hist = go.Figure()
    fig_hist.add_trace(
        go.Scatter(x=current_df['Time'], y=TANK_H - current_df['Dist'], fill='tozeroy', name="Level (mm)"))
    fig_hist.update_layout(title="Historical Consumption", height=250, template="plotly_dark")
    st.plotly_chart(fig_hist, use_container_width=True)


# Run the fragment
if not df.empty:
    render_dashboard()
else:
    st.error("No JSON data found.")