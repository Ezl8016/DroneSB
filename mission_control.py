"""
Drone Mission Control Server
Connects to MAVLink drone via serial, accepts commands from web UI.
"""

import math
import re
import threading
import time
from flask import Flask, jsonify, request, send_from_directory

try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False

SERIAL_PORT = "/dev/tty.usbserial-14110"
BAUD_RATE = 57600

app = Flask(__name__, static_folder=".")

# --- Drone connection state ---
drone = None
drone_lock = threading.Lock()
telemetry = {
    "connected": False,
    "armed": False,
    "mode": "UNKNOWN",
    "lat": 0.0,
    "lon": 0.0,
    "alt": 0.0,
    "heading": 0.0,
    "battery": 100,
    "gps_fix": 0,
    "satellites": 0,
    "log": [],
}

def log(msg):
    telemetry["log"].append({"t": time.strftime("%H:%M:%S"), "msg": msg})
    if len(telemetry["log"]) > 200:
        telemetry["log"].pop(0)
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# --- MAVLink helpers ---

def connect_drone():
    global drone
    if not MAVLINK_AVAILABLE:
        log("pymavlink not available — running in simulation mode")
        telemetry["connected"] = True
        return
    try:
        log(f"Connecting to {SERIAL_PORT} @ {BAUD_RATE} baud...")
        conn = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)
        conn.wait_heartbeat(timeout=10)
        log(f"Heartbeat received — system {conn.target_system}, component {conn.target_component}")
        with drone_lock:
            drone = conn
        telemetry["connected"] = True
        threading.Thread(target=telemetry_loop, daemon=True).start()
    except Exception as e:
        log(f"Connection failed: {e} — running in simulation mode")
        telemetry["connected"] = True  # allow UI to work in sim mode


def telemetry_loop():
    while True:
        try:
            with drone_lock:
                if drone is None:
                    break
                msg = drone.recv_match(blocking=False)
            if msg:
                t = msg.get_type()
                if t == "GLOBAL_POSITION_INT":
                    telemetry["lat"] = msg.lat / 1e7
                    telemetry["lon"] = msg.lon / 1e7
                    telemetry["alt"] = msg.relative_alt / 1000.0
                    telemetry["heading"] = msg.hdg / 100.0
                elif t == "HEARTBEAT":
                    from pymavlink import mavutil as mu
                    telemetry["armed"] = bool(msg.base_mode & mu.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                    telemetry["mode"] = mu.mode_string_v10(msg)
                elif t == "BATTERY_STATUS":
                    telemetry["battery"] = msg.battery_remaining
                elif t == "GPS_RAW_INT":
                    telemetry["gps_fix"] = msg.fix_type
                    telemetry["satellites"] = msg.satellites_visible
        except Exception:
            pass
        time.sleep(0.05)


def send_command_long(command, p1=0, p2=0, p3=0, p4=0, p5=0, p6=0, p7=0):
    with drone_lock:
        if drone is None:
            return False
        drone.mav.command_long_send(
            drone.target_system,
            drone.target_component,
            command, 0,
            p1, p2, p3, p4, p5, p6, p7
        )
    return True


def set_mode(mode_name):
    from pymavlink import mavutil as mu
    mode_id = drone.mode_mapping().get(mode_name.upper())
    if mode_id is None:
        return False, f"Unknown mode: {mode_name}"
    with drone_lock:
        drone.mav.set_mode_send(
            drone.target_system,
            mu.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
    return True, f"Mode set to {mode_name.upper()}"


def move_relative(north_m, east_m, down_m=0):
    """Send SET_POSITION_TARGET_LOCAL_NED for relative movement."""
    from pymavlink import mavutil as mu
    with drone_lock:
        if drone is None:
            return False
        drone.mav.set_position_target_local_ned_send(
            0,
            drone.target_system,
            drone.target_component,
            mu.mavlink.MAV_FRAME_BODY_OFFSET_NED,
            0b0000111111111000,  # position only
            north_m, east_m, down_m,
            0, 0, 0,
            0, 0, 0,
            0, 0
        )
    return True


# --- Command parser ---

def parse_command(text):
    t = text.strip().lower()

    # ARM
    if re.match(r"^arm$", t):
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
        log("ARM command sent")
        return "Arming motors..."

    # DISARM
    if re.match(r"^disarm$", t):
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0)
        log("DISARM command sent")
        return "Disarming motors..."

    # TAKEOFF [alt]
    m = re.match(r"^take ?off(?: (\d+(?:\.\d+)?)(?:m)?)?$", t)
    if m:
        alt = float(m.group(1)) if m.group(1) else 10.0
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, alt)
        log(f"TAKEOFF to {alt}m")
        return f"Taking off to {alt}m..."

    # LAND
    if re.match(r"^land$", t):
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_NAV_LAND)
        log("LAND command sent")
        return "Landing..."

    # RETURN TO HOME / RTH
    if re.match(r"^(return(?: to home)?|rth|go home)$", t):
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH)
        log("RTH command sent")
        return "Returning to home..."

    # HOVER / LOITER
    if re.match(r"^(hover|hold|loiter|stop)$", t):
        if drone:
            set_mode("LOITER")
        log("HOVER/LOITER mode set")
        return "Hovering in place..."

    # GO NORTH/SOUTH/EAST/WEST [distance]
    m = re.match(r"^(?:go |fly |move )?(north|south|east|west)(?: (\d+(?:\.\d+)?)(?:m|meters?)?)?$", t)
    if m:
        direction = m.group(1)
        dist = float(m.group(2)) if m.group(2) else 10.0
        north, east = 0.0, 0.0
        if direction == "north": north = dist
        elif direction == "south": north = -dist
        elif direction == "east": east = dist
        elif direction == "west": east = -dist
        if drone:
            move_relative(north, east)
        log(f"MOVE {direction.upper()} {dist}m")
        return f"Moving {direction} {dist}m..."

    # GO FORWARD/BACK/LEFT/RIGHT [distance]
    m = re.match(r"^(?:go |fly |move )?(forward|back(?:ward)?|left|right)(?: (\d+(?:\.\d+)?)(?:m|meters?)?)?$", t)
    if m:
        direction = m.group(1)
        dist = float(m.group(2)) if m.group(2) else 10.0
        north, east = 0.0, 0.0
        if direction == "forward": north = dist
        elif direction in ("back", "backward"): north = -dist
        elif direction == "right": east = dist
        elif direction == "left": east = -dist
        if drone:
            move_relative(north, east)
        log(f"MOVE {direction.upper()} {dist}m")
        return f"Moving {direction} {dist}m..."

    # UP [distance]
    m = re.match(r"^(?:go |fly |move )?up(?: (\d+(?:\.\d+)?)(?:m|meters?)?)?$", t)
    if m:
        dist = float(m.group(1)) if m.group(1) else 5.0
        if drone:
            move_relative(0, 0, -dist)  # NED: negative down = up
        log(f"CLIMB {dist}m")
        return f"Climbing {dist}m..."

    # DOWN [distance]
    m = re.match(r"^(?:go |fly |move )?down(?: (\d+(?:\.\d+)?)(?:m|meters?)?)?$", t)
    if m:
        dist = float(m.group(1)) if m.group(1) else 5.0
        if drone:
            move_relative(0, 0, dist)
        log(f"DESCEND {dist}m")
        return f"Descending {dist}m..."

    # ROTATE / YAW [degrees]
    m = re.match(r"^(?:rotate|yaw|turn)(?: (left|right|cw|ccw))?(?: (\d+(?:\.\d+)?)(?:deg(?:rees?)?)?)?$", t)
    if m:
        direction = m.group(1) or "right"
        deg = float(m.group(2)) if m.group(2) else 90.0
        if direction in ("left", "ccw"):
            deg = -deg
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_CONDITION_YAW, abs(deg), 0, 1 if deg > 0 else -1, 1)
        log(f"YAW {deg}°")
        return f"Rotating {abs(deg)}° {'right' if deg > 0 else 'left'}..."

    # SET SPEED [m/s]
    m = re.match(r"^(?:set )?speed (\d+(?:\.\d+)?)(?:m/s|mps)?$", t)
    if m:
        spd = float(m.group(1))
        if drone:
            from pymavlink import mavutil as mu
            send_command_long(mu.mavlink.MAV_CMD_DO_CHANGE_SPEED, 0, spd, -1, 0)
        log(f"SPEED set to {spd} m/s")
        return f"Speed set to {spd} m/s"

    # SET MODE
    m = re.match(r"^(?:set )?mode (.+)$", t)
    if m:
        mode = m.group(1).strip()
        if drone:
            ok, msg = set_mode(mode)
            log(msg)
            return msg
        log(f"MODE {mode} (sim)")
        return f"Mode set to {mode.upper()} (sim)"

    # WAYPOINT lat lon [alt]
    m = re.match(r"^(?:goto|waypoint|fly to) (-?\d+(?:\.\d+)?)[, ]+(-?\d+(?:\.\d+)?)(?:[, ]+(\d+(?:\.\d+)?))?$", t)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        alt = float(m.group(3)) if m.group(3) else 20.0
        if drone:
            from pymavlink import mavutil as mu
            drone.mav.mission_item_send(
                drone.target_system, drone.target_component,
                0, mu.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                mu.mavlink.MAV_CMD_NAV_WAYPOINT,
                2, 1, 0, 0, 0, 0,
                lat, lon, alt
            )
        log(f"WAYPOINT {lat},{lon} alt={alt}m")
        return f"Flying to {lat:.6f}, {lon:.6f} at {alt}m..."

    return None


# --- Flask routes ---

@app.route("/")
def index():
    return send_from_directory(".", "mission.html")

@app.route("/api/telemetry")
def api_telemetry():
    return jsonify(telemetry)

@app.route("/api/command", methods=["POST"])
def api_command():
    data = request.get_json(force=True)
    text = (data.get("cmd") or "").strip()
    if not text:
        return jsonify({"ok": False, "msg": "Empty command"})
    result = parse_command(text)
    if result is None:
        msg = f'Unknown command: "{text}". Try: arm, disarm, takeoff 10, land, go north 20, up 5, hover, rth, speed 5'
        log(msg)
        return jsonify({"ok": False, "msg": msg})
    return jsonify({"ok": True, "msg": result})

@app.route("/api/log")
def api_log():
    return jsonify(telemetry["log"])


if __name__ == "__main__":
    threading.Thread(target=connect_drone, daemon=True).start()
    print("\n=== Drone Mission Control ===")
    print("Open http://localhost:5050 in your browser\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
