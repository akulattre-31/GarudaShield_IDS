#!/usr/bin/env python3
import argparse
import json
import time
from datetime import datetime, timezone

from pymavlink import mavutil


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(
        description="M3 MAVLink receiver for the isolated M4 test stream"
    )
    parser.add_argument("--port", type=int, default=14556)
    parser.add_argument(
        "--log",
        default="m3_received.jsonl",
        help="JSONL telemetry log",
    )
    parser.add_argument(
        "--print-all",
        action="store_true",
        help="Print every MAVLink message type",
    )

    args = parser.parse_args()

    conn = mavutil.mavlink_connection(
        f"udpin:0.0.0.0:{args.port}"
    )

    print(f"[M3] Listening on 0.0.0.0:{args.port}")
    print("[M3] Waiting for MAVLink...")

    last_position_print = 0.0
    heartbeat_seen = False

    while True:
        msg = conn.recv_match(blocking=True)

        if msg is None:
            continue

        msg_type = msg.get_type()
        now = time.monotonic()

        record = {
            "wall_time": now_iso(),
            "message_type": msg_type,
            "system": msg.get_srcSystem(),
            "component": msg.get_srcComponent(),
        }

        if msg_type == "GLOBAL_POSITION_INT":
            record.update(
                {
                    "lat": msg.lat / 1e7,
                    "lon": msg.lon / 1e7,
                    "alt_m": msg.alt / 1000.0,
                    "relative_alt_m": msg.relative_alt / 1000.0,
                    "vx_mps": msg.vx / 100.0,
                    "vy_mps": msg.vy / 100.0,
                    "vz_mps": msg.vz / 100.0,
                }
            )

            if now - last_position_print >= 1.0:
                print(
                    "[M3] POS "
                    f"lat={record['lat']:.7f} "
                    f"lon={record['lon']:.7f} "
                    f"alt={record['alt_m']:.2f}m "
                    f"vx={record['vx_mps']:.2f} "
                    f"vy={record['vy_mps']:.2f} "
                    f"vz={record['vz_mps']:.2f}"
                )
                last_position_print = now

        elif msg_type == "HEARTBEAT":
            if not heartbeat_seen:
                print(
                    "[M3] HEARTBEAT received "
                    f"(system={msg.get_srcSystem()}, "
                    f"component={msg.get_srcComponent()})"
                )
                heartbeat_seen = True

        elif args.print_all:
            print(f"[M3] {msg_type}")

        with open(args.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
