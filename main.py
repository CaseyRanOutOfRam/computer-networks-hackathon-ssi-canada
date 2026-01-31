import os
import json
import base64

def decode_milesight_payload(data_b64):
    """
    Decodes the Base64 payload from Milesight EM500-UDL sensors.
    Logic based on Milesight-IoT SensorDecoders repository.
    """
    if not data_b64:
        return None
    
    try:
        data_bytes = base64.b64decode(data_b64)
    except Exception:
        return None

    res = {}
    i = 0
    while i < len(data_bytes):
        channel_id = data_bytes[i]
        channel_type = data_bytes[i + 1]
        i += 2
        
        # Battery Reading (0x01 0x75)
        if channel_id == 0x01 and channel_type == 0x75:
            res["Battery (%)"] = data_bytes[i]
            i += 1
        
        # Distance Reading (0x03 0x82)
        elif channel_id == 0x03 and channel_type == 0x82:
            # Distance is 2 bytes, Little Endian
            distance_mm = data_bytes[i] | (data_bytes[i + 1] << 8)
            res["Distance (mm)"] = distance_mm
            res["Distance (m)"] = distance_mm / 1000.0
            i += 2
        else:
            # Advance index if unknown to prevent loops
            i += 1
            
    return res

def process_folder(folder_path):
    print(f"{'File Name':<30} | {'Time':<25} | {'Battery':<8} | {'Distance'}")
    print("-" * 85)

    # List all files in the directory
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            
            with open(file_path, 'r') as f:
                try:
                    payload = json.load(f)
                    
                    # Extracting key info
                    time_val = payload.get("time", "N/A")
                    data_b64 = payload.get("data", "")
                    f_port = payload.get("fPort", -1)
                    
                    # Check if there is actual sensor data
                    if f_port == 85 and data_b64:
                        decoded = decode_milesight_payload(data_b64)
                        batt = f"{decoded.get('Battery (%)', 'N/A')}%"
                        dist = f"{decoded.get('Distance (mm)', 'N/A')} mm"
                        print(f"{filename[:30]:<30} | {time_val[:25]:<25} | {batt:<8} | {dist}")
                    #else:
                        # Skip or note empty/network packets
                        #print(f"{filename[:30]:<30} | {time_val[:25]:<25} | [No Sensor Data]")
                        
                except Exception as e:
                    print(f"Error reading {filename}: {e}")

# --- EXECUTION ---
# Change 'your_folder_path' to the actual path where your JSON files are stored
folder_path = 'C:\\Users\\aryan\\Desktop\\computer-networks-hackathon-ssi-canada\\dataset\\EM500-UDL\\24e124713d392240' 
process_folder(folder_path)