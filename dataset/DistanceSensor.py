import streamlit as st
import json
import base64
import glob
import pandas as pd
import plotly.graph_objects as go


# ---------------------------------------------------------
# 1. DECODER LOGIC (DDS75-LB Chirpstack V4)
# ---------------------------------------------------------
def decode_dds75_lb_full(fport, data_b64):
    """Accurately decodes Standard and Multi-Distance bursts."""
    if not data_b64: return []
    bytes_data = list(base64.b64decode(data_b64))
    records = []

    if fport == 2 and len(bytes_data) >= 8:
        # Multi-Distance Mode (5th bit of byte 0 is set)
        if bytes_data[0] & 0x10:
            bat_v = ((bytes_data[0] << 8 | bytes_data[1]) & 0x0FFF) / 1000
            end_index = len(bytes_data) - 4
            for i in range(8, min(48, end_index), 2):
                dist = bytes_data[i] << 8 | bytes_data[i + 1]
                records.append({"Type": "MULTI", "Bat": bat_v, "Dist": dist})
        else:
            # Standard Mode (Single distance reading)
            bat_v = ((bytes_data[0] << 8 | bytes_data[1]) & 0x3FFF) / 1000
            records.append({"Type": "SINGLE", "Bat": bat_v, "Dist": bytes_data[2] << 8 | bytes_data[3]})
    return records


# ---------------------------------------------------------
# 2. APP SETUP & DATA LOADING
# ---------------------------------------------------------
st.set_page_config(page_title="TankView", layout="wide")
PATH = "/Users/caseyr/PycharmProjects/computer-networks-hackathon-ssi-canada/dataset/Dragino DDS75-LB Ultrasonic Distance Sensor/a84041bbbf5946fc/*.json"


@st.cache_data
def load_all_data():
    files = glob.glob(PATH)
    all_m = []
    for f in files:
        with open(f, "r") as file:
            try:
                up = json.load(file)
                # Process only Port 2 (Data) messages
                decoded = decode_dds75_lb_full(up.get("fPort"), up.get("data"))
                for m in decoded:
                    m["Time"] = pd.to_datetime(up.get("time"))
                    all_m.append(m)
            except:
                continue
    return pd.DataFrame(all_m).sort_values('Time').reset_index(drop=True)


df = load_all_data()

# ---------------------------------------------------------
# 3. TankView GUI
# ---------------------------------------------------------
st.title("🌊 TankView | Dashboard")
st.markdown("---")

if not df.empty:
    # Sidebar Controls
    st.sidebar.header("System Configuration")
    TANK_H = st.sidebar.number_input("Tank Max Height (mm)", value=5000)
    ALARM_LEVEL = st.sidebar.slider("Alarm Threshold (%)", 0, 100, 20)

    # REPLAY SCRUBBER (The Time-Travel Control)
    st.subheader("⏱️ Simulation Time-Travel")
    playhead = st.select_slider(
        "Move slider to replay sensor history:",
        options=list(range(len(df))),
        format_func=lambda x: df.iloc[x]['Time'].strftime('%Y-%m-%d %H:%M:%S')
    )

    # Slice data based on playhead
    current_df = df.iloc[:playhead + 1]
    latest = current_df.iloc[-1]
    level_mm = TANK_H - latest['Dist']
    fill_pct = (level_mm / TANK_H) * 100

    # METRICS ROW
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Level", f"{level_mm} mm")
    m2.metric("Fill Percentage", f"{fill_pct:.1f}%")
    m3.metric("Battery Status", f"{latest['Bat']:.3f} V")

    # ANOMALY & ALERT SYSTEM
    if latest['Dist'] == 0:
        m4.error("🚨 ECHO LOSS")
        st.warning("Sensor reported 0mm. Check for physical obstructions or internal foam.")
    elif fill_pct < ALARM_LEVEL:
        m4.warning("⚠️ LOW LEVEL")
    else:
        m4.success("✅ NOMINAL")

    # INTERACTIVE CHART

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=current_df['Time'],
        y=TANK_H - current_df['Dist'],
        mode='lines+markers',
        fill='tozeroy',
        line=dict(color='#00d1ff', width=2),
        name="Water Level"
    ))

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Time",
        yaxis_title="Height (mm)",
        yaxis=dict(range=[0, TANK_H + 500])
    )
    st.plotly_chart(fig, use_container_width=True)

    # RAW DATA PREVIEW
    with st.expander("View Raw Decoded Logs"):
        st.dataframe(current_df.tail(10))

else:
    st.error("Check your path: No JSON files found in the specified directory.")