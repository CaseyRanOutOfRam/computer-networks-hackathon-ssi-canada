import json
import os

def print_sw3l_csv(directory_path):
    all_readings = []

    # Iterate through all JSON files in the folder
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)
            
            with open(file_path, 'r') as f:
                try:
                    payload = json.load(f)
                    
                    # Filter for Dragino SW3L sensors
                    profile = payload.get("deviceInfo", {}).get("deviceProfileName", "")
                    if profile == "SW3L":
                        timestamp = payload.get("time")
                        obj = payload.get("object", {})
                        
                        # Only include entries with valid sensor data
                        if obj:
                            all_readings.append({
                                "time": timestamp,
                                "battery": obj.get("BAT"),
                                "firmware": obj.get("FIRMWARE_VERSION"),
                                "band": obj.get("FREQUENCY_BAND")
                            })
                except Exception:
                    continue

    # Sort chronologically by timestamp
    all_readings.sort(key=lambda x: x['time'])
    
    # Print the CSV Header
    print("time,battery_v,firmware,band")
    
    # Print each row
    print(len(all_readings))
    for r in all_readings:
        print(f"{r['time']},{r['battery']},{r['firmware']},{r['band']}")

# Run the script for the current directory
print_sw3l_csv("C:\\Users\\aryan\\Desktop\\computer-networks-hackathon-ssi-canada")