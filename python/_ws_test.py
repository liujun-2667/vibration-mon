import asyncio
import json
import websockets


async def main():
    out = []
    try:
        async with websockets.connect("ws://127.0.0.1:8000/ws/3") as ws:
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=8)
                d = json.loads(msg)
                out.append(
                    "type=%s device=%s ts=%s data_len=%d sr=%s rms=%s freq=%s health=%s"
                    % (
                        d.get("type"),
                        d.get("device_id"),
                        d.get("timestamp"),
                        len(d.get("data", [])),
                        d.get("sample_rate"),
                        d.get("rms"),
                        d.get("dominant_frequency"),
                        d.get("health_index"),
                    )
                )
    except Exception as e:
        out.append("ERROR: %r" % e)

    with open("_ws_out.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))


asyncio.run(main())
