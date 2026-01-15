import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


AIRCRAFT_JSON = "/run/dump1090-fa/aircraft.json"

TB_HOST = "#IPHost"
TB_PORT = "#Port"

SLOTS = {
    1:  "#Device-Token1",
    2:  "#Device-Token2",
    3:  "#Device-Token3",
    4:  "#Device-Token4",
    5:  "#Device-Token5",
    6:  "#Device-Token6",
    7:  "#Device-Token7",
    8:  "#Device-Token8",
    9:  "#Device-Token9",
    10: "#Device-Token10",
}

MAX_SLOTS = 10
STALE_SECONDS = 45
PUBLISH_INTERVAL = 1.0

TOPIC = "v1/devices/me/telemetry"


def now_utc_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def load_aircraft():
    try:
        with open(AIRCRAFT_JSON, "r") as f:
            return json.load(f).get("aircraft", [])
    except Exception as e:
        print(f"[ERROR] Failed to load aircraft data: {e}", flush=True)
        return []


def score(aircraft):
    if aircraft.get("hex") is None:
        return -1
    if aircraft.get("lat") is None or aircraft.get("lon") is None:
        return -1

    s = 0
    if aircraft.get("flight"):
        s += 5
    if aircraft.get("alt_baro") is not None:
        s += 2
    if aircraft.get("gs") is not None:
        s += 1

    seen = aircraft.get("seen")
    if seen is not None:
        try:
            s += max(0, 5 - min(5, float(seen)))
        except ValueError:
            pass

    return s


def pick_top_n(aircraft, n):
    ranked = [a for a in aircraft if score(a) >= 0]
    ranked.sort(key=score, reverse=True)

    selected = []
    used_hex = set()

    for a in ranked:
        h = a.get("hex")
        if h in used_hex:
            continue
        used_hex.add(h)
        selected.append(a)
        if len(selected) == n:
            break

    return selected


def normalize(aircraft, slot):
    return {
        "slot": slot,
        "hex": aircraft.get("hex"),
        "callsign": (aircraft.get("flight") or "").strip(),
        "lat": aircraft.get("lat"),
        "lon": aircraft.get("lon"),
        "altitude": aircraft.get("alt_baro"),
        "ground_speed": aircraft.get("gs"),
        "heading": aircraft.get("track"),
        "squawk": aircraft.get("squawk"),
        "seen_s": aircraft.get("seen"),
        "timestamp_utc": now_utc_ms(),
    }


class SlotPublisher:
    def __init__(self, token: str):
        self.client = mqtt.Client(protocol=mqtt.MQTTv311)
        self.client.username_pw_set(token)

        self.connected = False
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        self.client.connect(TB_HOST, TB_PORT, 60)
        self.client.loop_start()

        start = time.time()
        while not self.connected and time.time() - start < 5:
            time.sleep(0.05)

        if not self.connected:
            raise RuntimeError("MQTT connection timeout")

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = (rc == 0)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def publish(self, payload):
        msg = self.client.publish(TOPIC, json.dumps(payload), qos=1)
        msg.wait_for_publish(timeout=2)

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()


def main():
    print("[INFO] Starting ADS-B slot tracking", flush=True)

    slot_hex = {i: None for i in range(1, MAX_SLOTS + 1)}
    slot_last_seen = {i: 0.0 for i in range(1, MAX_SLOTS + 1)}

    publishers = {i: SlotPublisher(SLOTS[i]) for i in range(1, MAX_SLOTS + 1)}
    print("[INFO] MQTT connected for all slots", flush=True)

    try:
        while True:
            aircraft = load_aircraft()
            top = pick_top_n(aircraft, MAX_SLOTS)
            aircraft_by_hex = {a["hex"]: a for a in top}

            now = time.time()

            for slot, h in slot_hex.items():
                if h in aircraft_by_hex:
                    slot_last_seen[slot] = now

            for slot, h in slot_hex.items():
                if h and now - slot_last_seen[slot] > STALE_SECONDS:
                    slot_hex[slot] = None

            used = {h for h in slot_hex.values() if h}
            free_slots = [s for s in slot_hex if slot_hex[s] is None]
            unassigned = [h for h in aircraft_by_hex if h not in used]

            for slot in free_slots:
                if not unassigned:
                    break
                h = unassigned.pop(0)
                slot_hex[slot] = h
                slot_last_seen[slot] = now

                a = aircraft_by_hex[h]
                print(
                    f"[INFO] Slot {slot:02d} assigned to {h} "
                    f"({(a.get('flight') or '').strip()})",
                    flush=True,
                )

            for slot, h in slot_hex.items():
                if not h:
                    continue
                aircraft = aircraft_by_hex.get(h)
                if aircraft:
                    publishers[slot].publish(normalize(aircraft, slot))

            time.sleep(PUBLISH_INTERVAL)

    finally:
        for p in publishers.values():
            p.close()


if __name__ == "__main__":
    main()
