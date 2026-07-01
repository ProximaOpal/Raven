"""
Raven AI CCTV — Camera Feed Simulator
Feeds demo images into the analysis pipeline at a configurable rate.
Simulates 1-4 simultaneous RTSP camera streams.

Usage:
  python demo/simulate_camera.py                    # default: 4 streams, 10s interval
  python demo/simulate_camera.py --streams 2 --interval 5
  python demo/simulate_camera.py --mode stress --streams 4 --interval 2
"""
import argparse
import asyncio
import base64
import httpx
import sys
import random
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


API_BASE = "http://localhost:8000"
DEMO_DIR = Path(__file__).parent / "sample_incidents"


def get_demo_images() -> list[Path]:
    if DEMO_DIR.exists():
        images = list(DEMO_DIR.glob("*.jpg")) + list(DEMO_DIR.glob("*.png"))
        if images:
            return images
    return []


def encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def minimal_b64() -> str:
    """Tiny 1x1 JPEG for when no demo images are present."""
    data = b"\xff\xd8\xff\xd9"
    return base64.b64encode(data).decode()


async def simulate_camera(
    camera_id: int,
    interval: float,
    client: httpx.AsyncClient,
    images: list[Path],
    stats: dict,
):
    """Continuously submit frames for one camera."""
    print(f"  [CAM] Camera #{camera_id} started (interval: {interval}s)")
    while True:
        await asyncio.sleep(interval + random.uniform(-1, 1))
        if images:
            img_path = random.choice(images)
            try:
                b64 = encode_image(img_path)
            except Exception:
                b64 = minimal_b64()
        else:
            b64 = minimal_b64()

        try:
            t0 = time.monotonic()
            resp = await client.post(
                f"{API_BASE}/api/incidents/analyze",
                json={"camera_id": camera_id, "image_b64": b64},
                timeout=30.0,
            )
            elapsed = time.monotonic() - t0

            if resp.status_code == 200:
                data = resp.json()
                severity = data.get("severity", "?")
                threat = data.get("threat_type", "?")
                inc_id = data.get("id", "?")
                print(
                    f"  [OK] CAM-{camera_id:02d} | Incident #{inc_id} "
                    f"[{severity:8s}] {threat[:40]:<40} ({elapsed:.1f}s)"
                )
                stats["total"] += 1
                stats.setdefault("severities", {})
                stats["severities"][severity] = stats["severities"].get(severity, 0) + 1

                # Couple with RF movement simulation based on camera location
                coords = {
                    1: {"x": 150.0, "y": 120.0},
                    2: {"x": 350.0, "y": 420.0},
                    3: {"x": 150.0, "y": 120.0},
                    4: {"x": 450.0, "y": 220.0},
                }
                c = coords.get(camera_id, {"x": 300.0, "y": 300.0})
                try:
                    await client.post(f"{API_BASE}/api/rf/simulate-move", json=c, timeout=5.0)
                except Exception:
                    pass
            else:
                print(f"  [ERR] CAM-{camera_id:02d} | HTTP {resp.status_code}: {resp.text[:80]}")
                stats["errors"] += 1

        except httpx.ConnectError:
            print(f"  [ERR] CAM-{camera_id:02d} | Cannot connect to {API_BASE} - is the server running?")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"  [ERR] CAM-{camera_id:02d} | Error: {e}")
            stats["errors"] += 1


async def run_simulation(num_streams: int, interval: float, duration: float | None):
    images = get_demo_images()
    if images:
        print(f"  Found {len(images)} demo images in {DEMO_DIR}")
    else:
        print(f"  No demo images found — using minimal placeholder frames")

    # Verify cameras exist
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{API_BASE}/api/cameras", timeout=5.0)
            cameras = resp.json()
            if not cameras:
                print("  Creating demo cameras...")
                camera_defs = [
                    {"name": f"CAM-{i+1:02d} - Zone {chr(65+i)}", "location": f"Zone {chr(65+i)} Perimeter", "is_mock": True}
                    for i in range(num_streams)
                ]
                for cam in camera_defs:
                    await client.post(f"{API_BASE}/api/cameras", json=cam)
                resp = await client.get(f"{API_BASE}/api/cameras")
                cameras = resp.json()
            camera_ids = [c["id"] for c in cameras[:num_streams]]
        except Exception as e:
            print(f"  Cannot reach API: {e}")
            return

    print(f"\n>> Starting simulation: {num_streams} streams, {interval}s interval")
    if duration:
        print(f"   Duration: {duration}s")
    print(f"   Camera IDs: {camera_ids}")
    print("-" * 60)
    print(f"  {'Camera':<10} {'Incident':<12} {'Severity':<10} {'Threat':<40} {'Time'}")
    print("-" * 60)

    stats = {"total": 0, "errors": 0}
    start = time.monotonic()

    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(simulate_camera(cam_id, interval, client, images, stats))
            for cam_id in camera_ids
        ]

        if duration:
            await asyncio.sleep(duration)
            for t in tasks:
                t.cancel()
        else:
            try:
                await asyncio.gather(*tasks)
            except KeyboardInterrupt:
                for t in tasks:
                    t.cancel()

    elapsed = time.monotonic() - start
    print(f"\n{'=' * 60}")
    print(f"  Simulation complete | {elapsed:.1f}s elapsed")
    print(f"  Incidents created: {stats['total']}")
    print(f"  Errors: {stats['errors']}")
    if stats.get("severities"):
        for sev, count in sorted(stats["severities"].items()):
            print(f"    {sev}: {count}")
    print(f"{'=' * 60}\n")


def main():
    parser = argparse.ArgumentParser(description="Raven AI CCTV — Camera Feed Simulator")
    parser.add_argument("--streams", type=int, default=4, help="Number of camera streams (default: 4)")
    parser.add_argument("--interval", type=float, default=10.0, help="Frame submission interval in seconds (default: 10)")
    parser.add_argument("--duration", type=float, default=None, help="Run duration in seconds (default: indefinite)")
    parser.add_argument("--mode", choices=["normal", "stress"], default="normal", help="Mode: normal or stress")
    args = parser.parse_args()

    if args.mode == "stress":
        args.interval = min(args.interval, 2.0)
        print(f"⚡ STRESS MODE: {args.streams} streams at {args.interval}s interval")

    asyncio.run(run_simulation(args.streams, args.interval, args.duration))


if __name__ == "__main__":
    main()
