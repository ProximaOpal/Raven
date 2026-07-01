import os
import shutil

src_dir = r"C:\Users\grvns\.gemini\antigravity\brain\c20edf62-5435-40a0-95db-89b5ad9bd232"
dst_dir1 = r"C:\Users\grvns\.gemini\antigravity\scratch\nexus-cctv\demo\sample_incidents"
dst_dir2 = r"C:\Users\grvns\.gemini\antigravity\scratch\nexus-cctv\frontend\images"

os.makedirs(dst_dir1, exist_ok=True)
os.makedirs(dst_dir2, exist_ok=True)

mapping = {
    "fence_intrusion_1781546565533.png": "fence_intrusion.jpg",
    "parking_vehicle_1781546576156.png": "parking_vehicle.jpg",
    "crowd_gathering_1781546587356.png": "crowd_gathering.jpg",
    "normal_lobby_1781546598225.png": "normal_lobby.jpg"
}

for src_name, dst_name in mapping.items():
    src_path = os.path.join(src_dir, src_name)
    if os.path.exists(src_path):
        shutil.copy2(src_path, os.path.join(dst_dir1, dst_name))
        shutil.copy2(src_path, os.path.join(dst_dir2, dst_name))
        print(f"Copied {src_name} to {dst_name} in both locations")
    else:
        print(f"Source not found: {src_path}")

