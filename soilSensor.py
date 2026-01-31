import json
import base64
import os

def decode_makerfabs_manual(payload_b64):
    """Manually decodes the 9-byte Makerfabs payload if 'object' is empty."""
    try:
        data = base64.b64decode(payload_b64)
        if len(data) < 9: return None
        return {
            "soil_val": (data[2] << 8) | data[3],
            "battery_v": data[4] / 10.0,
            "temp": int.from_bytes(data[7:9], byteorder='big', signed=True) / 10.0
        }
    except:
        return None

def generate_sensor_csv(directory_path):
    all_readings = []

    # Iterate through all JSON files
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)
            
            with open(file_path, 'r') as f:
                try:
                    payload = json.load(f)
                    
                    # Only process Makerfabs Soil Moisture Sensor files
                    profile = payload.get("deviceInfo", {}).get("deviceProfileName", "")
                    if "Makerfabs" in profile:
                        timestamp = payload.get("time")
                        
                        # Extract data from server-decoded object or manual decode
                        sensor_data = payload.get("object")
                        if not sensor_data or "soil_val" not in sensor_data:
                            sensor_data = decode_makerfabs_manual(payload.get("data", ""))
                        
                        if sensor_data:
                            # Map varied keys (battery_v vs battery) to a single 'bat' column
                            all_readings.append({
                                "time": timestamp,
                                "soil": sensor_data.get("soil_val"),
                                "temp": sensor_data.get("temp"),
                                "bat": sensor_data.get("battery_v") or sensor_data.get("battery")
                            })
                except Exception:
                    continue

    # Sort the readings chronologically by the timestamp
    all_readings.sort(key=lambda x: x['time'])
    
    # Print the CSV header
    print("time,soil,temp,bat")
    
    # Print each row
    for r in all_readings:
        print(f"{r['time']},{r['soil']},{r['temp']},{r['bat']}")

# --- EXECUTION ---
# Path to the folder containing your JSON files
folder_path = "C:\\Users\\aryan\\Desktop\\computer-networks-hackathon-ssi-canada\\dataset\\Makerfabs Soil Moisture Sensor\\48e663fffe3000e3" 
generate_sensor_csv(folder_path)