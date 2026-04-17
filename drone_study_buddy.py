import os
import subprocess
import threading

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CORRECT_SFX = os.path.join(_SCRIPT_DIR, "correct.mp3")
_WRONG_SFX = os.path.join(_SCRIPT_DIR, "wrong.mp3")
_FIVE_SFX = os.path.join(_SCRIPT_DIR, "five.mp3")


def _play(path):
    if os.path.exists(path):
        threading.Thread(target=lambda: subprocess.run(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), daemon=True).start()


KB = {
    "aerodynamics": """Drones generate lift through spinning rotors. Each rotor blade is an airfoil — curved on top, flatter on the bottom — which creates lower pressure above and higher pressure below, generating upward force (Bernoulli's principle). Multirotor drones use 4+ rotors spinning in alternating directions to cancel torque and maintain stability.

Key concepts:
  - Thrust: upward force from rotors
  - Drag: air resistance opposing movement
  - Weight/gravity: drone must produce thrust > weight to ascend
  - Roll, Pitch, Yaw: three axes of rotation controlled by varying motor speeds""",

    "controllers": """A flight controller (FC) is the brain of the drone. It reads sensor data and adjusts motor speeds thousands of times per second to maintain stability.

Components:
  - IMU (Inertial Measurement Unit): accelerometer + gyroscope that detects orientation
  - Barometer: measures altitude via air pressure
  - ESCs (Electronic Speed Controllers): convert FC signals to motor power
  - PID tuning: Proportional-Integral-Derivative algorithm that corrects flight errors

Popular FC firmware: Betaflight (FPV), ArduPilot (autonomous), DJI's proprietary systems""",

    "types": """Main drone categories:

  1. Multirotors (quadcopters, hexacopters) — most common, stable, great for photography. Examples: DJI Phantom, Mavic.
  2. Fixed-wing — more like planes, longer range & endurance, used in agriculture/surveying.
  3. Hybrid VTOL — takes off vertically, transitions to fixed-wing flight.
  4. Single-rotor — helicopter design, more efficient for heavy payloads.
  5. FPV racing drones — tiny, ultra-fast, manual control through goggles.
  6. Nano/micro drones — indoor use, palm-sized.

Use cases: photography, agriculture, delivery, search & rescue, mapping, inspection, racing.""",

    "faa": """FAA drone rules (USA) as of 2024:

Recreational flyers:
  - Register if drone weighs 250g+ ($5, at FAA DroneZone)
  - Fly below 400 ft AGL (above ground level)
  - Stay within visual line of sight (VLOS)
  - Never fly over people or moving vehicles
  - Avoid controlled airspace without LAANC authorization
  - No flying near airports without permission

Commercial pilots:
  - Require Part 107 certificate (written FAA exam)
  - Can fly over people with waiver in some cases
  - Must follow airspace rules and file waivers for exceptions

No-fly zones: National parks, military bases, stadiums during events, Washington DC area.""",

    "gps": """GPS on drones enables autonomous flight and position hold.

How it works:
  1. GPS receiver picks up signals from 4+ satellites
  2. Triangulates position (lat, long, altitude)
  3. Flight controller uses position data to maintain hover or follow a path

Modes enabled by GPS:
  - Position Hold (Loiter): stays in place when you let go of sticks
  - Return to Home (RTH): auto-flies back if signal is lost
  - Waypoint missions: pre-programmed flight paths
  - Follow Me: drone tracks a moving GPS target

GLONASS (Russian) and Galileo (EU) are alternatives/supplements to US GPS. Most modern drones use multi-constellation receivers for better accuracy.""",

    "fpv": """FPV (First Person View) racing is a high-speed drone sport where pilots wear video goggles to see live feed from the drone's camera — feeling like you're in the cockpit.

Key gear:
  - Frame: 3"-5" carbon fiber, designed to survive crashes
  - Motors: high-KV brushless (2300-2700KV for 5" props)
  - VTX (Video Transmitter): sends live video to goggles
  - FPV Goggles: DJI O3, Fat Shark, Orqa
  - Radio controller: FrSky, RadioMaster, TBS

Racing classes: Toothpick (lightweight 2-3"), Standard 5", Long Range (7+")

Leagues: MultiGP (US), Drone Racing League (DRL — professional), FAI World Drone Racing Championship""",

    "components": """Core drone components:

  - Frame: structural skeleton, usually carbon fiber
  - Motors: brushless DC motors, rated by KV (RPM per volt)
  - Propellers: push/pull air; size = diameter x pitch (e.g., 5x4.5)
  - Battery: LiPo (Lithium Polymer), rated in mAh and C-rating
  - ESC: Electronic Speed Controller, converts signals to motor power
  - Flight Controller: brain, runs stabilization firmware
  - Receiver: receives pilot inputs from radio transmitter
  - GPS module: position hold and autonomous flight
  - Gimbal: stabilizes camera on 2 or 3 axes
  - FPV camera: wide-angle, low latency for piloting"""
}

QUIZ = [
    {
        "q": "What does 'KV' mean when describing a drone motor?",
        "opts": ["Kilovolts of power", "RPM per volt", "Kilo-watt capacity", "Kilogram load rating"],
        "ans": 1,
        "exp": "KV = RPM per volt. A 2400KV motor spins at 2400 RPM per volt applied."
    },
    {
        "q": "What does IMU stand for in a flight controller?",
        "opts": ["Internal Motor Unit", "Inertial Measurement Unit", "Integrated Motor Uplink", "Input Management Utility"],
        "ans": 1,
        "exp": "IMU = Inertial Measurement Unit. It contains an accelerometer and gyroscope to detect orientation and movement."
    },
    {
        "q": "What altitude limit do recreational drone pilots follow in the US?",
        "opts": ["200 ft AGL", "400 ft AGL", "500 ft MSL", "1000 ft AGL"],
        "ans": 1,
        "exp": "FAA requires recreational flyers to stay below 400 ft AGL (Above Ground Level) unless in controlled airspace with authorization."
    },
    {
        "q": "In a quadcopter, why do adjacent motors spin in opposite directions?",
        "opts": ["To generate more lift", "To cancel out rotational torque", "To reduce power consumption", "To improve GPS accuracy"],
        "ans": 1,
        "exp": "Counter-rotating props cancel torque — if all spun the same way, the drone body would spin in the opposite direction."
    },
    {
        "q": "What is a 'Return to Home' function?",
        "opts": ["Manual landing mode", "Auto-flight back to takeoff point", "FPV racing term", "GPS calibration sequence"],
        "ans": 1,
        "exp": "RTH = Return to Home. Triggered automatically on signal loss, it flies the drone back to its recorded takeoff GPS coordinates."
    }
]

QUICK_ASKS = {
    "1": "How do drones generate lift?",
    "2": "Explain drone flight controllers and how they work",
    "3": "What are the main types of drones and their uses?",
    "4": "Explain FAA drone regulations for hobbyists in the US",
    "5": "How does GPS work on drones?",
    "6": "What is FPV drone racing?",
    "7": "Quiz me on drone components",
}

quiz_idx = 0


def get_response(q):
    ql = q.lower()
    if any(w in ql for w in ["quiz", "test me", "question"]):
        return "__QUIZ__"
    if any(w in ql for w in ["lift", "aerody", "rotor", "thrust", "propell"]):
        return KB["aerodynamics"]
    if any(w in ql for w in ["flight controller", "imu", "esc", "pid", "betaflight", "stabiliz"]):
        return KB["controllers"]
    if any(w in ql for w in ["type", "kind", "category", "fixed wing", "multirot", "vtol"]):
        return KB["types"]
    if any(w in ql for w in ["faa", "regulat", "law", "legal", "part 107", "airspace", "register"]):
        return KB["faa"]
    if any(w in ql for w in ["gps", "navigation", "waypoint", "position hold", "return to home", "glonass"]):
        return KB["gps"]
    if any(w in ql for w in ["fpv", "racing", "goggles", "first person"]):
        return KB["fpv"]
    if any(w in ql for w in ["component", "parts", "motor", "battery", "lipo", "frame", "gimbal"]):
        return KB["components"]
    if any(w in ql for w in ["hello", "hi", "hey"]):
        return "Hey there! Ready to study drones? Ask me about aerodynamics, flight controllers, FAA rules, GPS navigation, FPV racing, or any drone topic."
    return f'That\'s a great question about "{q}"! This study buddy covers core drone topics — aerodynamics, components, flight controllers, FAA regulations, GPS navigation, and FPV racing. Try rephrasing your question.'


def run_quiz():
    global quiz_idx
    q = QUIZ[quiz_idx % len(QUIZ)]
    qnum = (quiz_idx % len(QUIZ)) + 1
    print(f"\n[Question {qnum} of {len(QUIZ)}]")
    print(f"  {q['q']}\n")
    for i, opt in enumerate(q["opts"]):
        print(f"  {i + 1}. {opt}")
    while True:
        try:
            raw = input("\nYour answer (1-4): ").strip()
            if raw == "5":
                _play(_FIVE_SFX)
            choice = int(raw) - 1
            if 0 <= choice <= 3:
                break
            print("Please enter a number between 1 and 4.")
        except ValueError:
            print("Please enter a number between 1 and 4.")
    if choice == q["ans"]:
        _play(_CORRECT_SFX)
        print(f"\n[D] Correct! {q['exp']}")
    else:
        _play(_WRONG_SFX)
        print(f"\n[D] Not quite. The answer is: {q['opts'][q['ans']]}\n    {q['exp']}")
    quiz_idx += 1


def print_topics():
    topics = [
        ("1", "Aerodynamics"),
        ("2", "Flight Controllers"),
        ("3", "Drone Types"),
        ("4", "FAA Rules"),
        ("5", "GPS & Navigation"),
        ("6", "FPV Racing"),
        ("7", "Quiz me"),
    ]
    print("\nQuick topics: " + "  |  ".join(f"[{n}] {t}" for n, t in topics))


def main():
    print("=" * 60)
    print("         Drone Study Buddy")
    print("=" * 60)
    print("\n[D] Hey! I'm your drone study buddy. Ask me anything about")
    print("    drones — aerodynamics, components, regulations, FPV,")
    print("    navigation, or anything else. Type 'quit' to exit.")
    print_topics()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[D] Happy flying!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye"):
            print("[D] Happy flying!")
            break

        if user_input in QUICK_ASKS:
            user_input = QUICK_ASKS[user_input]
            print(f"You: {user_input}")

        resp = get_response(user_input)
        if resp == "__QUIZ__":
            print("\n[D] Let's test your drone knowledge!")
            run_quiz()
        else:
            print(f"\n[D] {resp}")

        print_topics()


if __name__ == "__main__":
    main()
