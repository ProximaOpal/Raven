import os
import shutil
import argparse

def main():
    parser = argparse.ArgumentParser(description="Copy demo images to destination paths.")
    parser.add_argument(
        "--src-dir",
        type=str,
        default=os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "brain", "c20edf62-5435-40a0-95db-89b5ad9bd232"),
        help="Path to source directory containing the raw demo images."
    )
    args = parser.parse_args()

    # Determine destination paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dst_dir1 = os.path.join(script_dir, "sample_incidents")
    dst_dir2 = os.path.join(script_dir, "..", "frontend", "images")

    os.makedirs(dst_dir1, exist_ok=True)
    os.makedirs(dst_dir2, exist_ok=True)

    mapping = {
        "fence_intrusion_1781546565533.png": "fence_intrusion.jpg",
        "parking_vehicle_1781546576156.png": "parking_vehicle.jpg",
        "crowd_gathering_1781546587356.png": "crowd_gathering.jpg",
        "normal_lobby_1781546598225.png": "normal_lobby.jpg"
    }

    for src_name, dst_name in mapping.items():
        src_path = os.path.join(args.src_dir, src_name)
        if os.path.exists(src_path):
            shutil.copy2(src_path, os.path.join(dst_dir1, dst_name))
            shutil.copy2(src_path, os.path.join(dst_dir2, dst_name))
            print(f"Copied {src_name} to {dst_name} in both locations")
        else:
            # Check locally in script dir if source not found in the target directory
            fallback_src = os.path.join(script_dir, src_name)
            if os.path.exists(fallback_src):
                shutil.copy2(fallback_src, os.path.join(dst_dir1, dst_name))
                shutil.copy2(fallback_src, os.path.join(dst_dir2, dst_name))
                print(f"Copied fallback {src_name} to {dst_name} in both locations")
            else:
                print(f"Source not found: {src_path} (Fallback not found at {fallback_src})")

if __name__ == "__main__":
    main()

