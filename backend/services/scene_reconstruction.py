"""
Raven AI CCTV — Multi-Camera 3D Scene Reconstruction & Trajectory Tracking Service
Computes Bird's Eye View (BEV) projections using Homography matrices.
Implements a Multi-Target Multi-Camera (MTMC) Tracker with appearance-based ReID.
"""
import time
import logging
from datetime import datetime, timezone
import numpy as np
import cv2
import json

from backend.database import AsyncSessionLocal
from backend.models import TrajectoryPoint, Camera

logger = logging.getLogger(__name__)


class SceneReconstructionService:
    # ── Homography Matrices Setup ─────────────────────────────────────────────
    # We define calibration points mapping 2D frames (640x480) to a global BEV map (800x800)
    # Each camera monitors a specific sector of the compound
    
    # 4 calibration points: [bottom-left, bottom-right, top-left, top-right]
    CALIBRATION_POINTS = {
        1: { # Camera 1: North Gate / Perimeter
            "src": np.float32([[0, 480], [640, 480], [100, 100], [540, 100]]),
            "dst": np.float32([[100, 380], [300, 380], [150, 150], [250, 150]])
        },
        2: { # Camera 2: South Gate / Parking
            "src": np.float32([[0, 480], [640, 480], [100, 100], [540, 100]]),
            "dst": np.float32([[500, 680], [700, 680], [550, 480], [650, 480]])
        },
        3: { # Camera 3: Entrance Lobby
            "src": np.float32([[0, 480], [640, 480], [120, 120], [520, 120]]),
            "dst": np.float32([[300, 480], [500, 480], [350, 300], [450, 300]])
        },
        4: { # Camera 4: Restricted Corridor
            "src": np.float32([[0, 480], [640, 480], [100, 100], [540, 100]]),
            "dst": np.float32([[100, 680], [300, 680], [150, 450], [250, 450]])
        }
    }

    _homographies = {}

    @classmethod
    def get_homography(cls, camera_id: int) -> np.ndarray:
        """Computes or retrieves the homography matrix for a camera."""
        if camera_id in cls._homographies:
            return cls._homographies[camera_id]

        points = cls.CALIBRATION_POINTS.get(camera_id)
        if not points:
            # Fallback to identity matrix if camera not calibrated
            cls._homographies[camera_id] = np.eye(3, dtype=np.float32)
            return cls._homographies[camera_id]

        H = cv2.getPerspectiveTransform(points["src"], points["dst"])
        cls._homographies[camera_id] = H
        return H

    @classmethod
    def project_to_world(cls, camera_id: int, image_x: float, image_y: float) -> tuple[float, float]:
        """
        Projects a 2D image coordinate (typically bottom-center of bounding box)
        to the shared 3D/BEV ground plane coordinate.
        """
        H = cls.get_homography(camera_id)
        point = np.array([[[image_x, image_y]]], dtype=np.float32)
        projected = cv2.perspectiveTransform(point, H)
        world_x, world_y = projected[0][0][0], projected[0][0][1]
        return float(world_x), float(world_y)

    # ── Multi-Target Multi-Camera (MTMC) Tracker ──────────────────────────────
    # Stores active tracks across all cameras in memory to associate targets.
    # Structure: {global_track_id: {"last_seen": float, "world_x": float, "world_y": float, "color_histogram": np.ndarray}}
    ACTIVE_TRACKS = {}
    NEXT_TRACK_ID = 1

    @classmethod
    def extract_color_histogram(cls, frame: np.ndarray, bbox: dict) -> np.ndarray:
        """
        Extracts a color histogram (in HSV space) from the cropped bounding box
        to represent visual appearance (Person ReID).
        """
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(fw, int(x + w)), min(fh, int(y + h))
        
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros((32,), dtype=np.float32)
            
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        # Calculate 1D histogram of Hue channel
        hist = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        cv2.normalize(hist, hist)
        return hist.flatten()

    @classmethod
    def match_and_track(
        cls,
        camera_id: int,
        frame: np.ndarray,
        bbox: dict,
    ) -> tuple[str, float, float]:
        """
        Matches a detected object (YOLO bbox) to existing global trajectories
        using spatial proximity on the BEV map and appearance ReID.
        Returns (global_track_id, world_x, world_y).
        """
        # Calculate bottom-center coordinate of YOLO bounding box (ground footpoint)
        img_x = bbox["x"] + bbox["w"] / 2
        img_y = bbox["y"] + bbox["h"]
        
        # Project to world BEV
        world_x, world_y = cls.project_to_world(camera_id, img_x, img_y)
        
        # Extract visual feature vector
        hist = cls.extract_color_histogram(frame, bbox)
        
        best_match_id = None
        min_cost = 9999.0
        now = time.time()
        
        # Cleanup expired tracks (older than 30 seconds)
        expired = [tid for tid, track in cls.ACTIVE_TRACKS.items() if now - track["last_seen"] > 30.0]
        for tid in expired:
            cls.ACTIVE_TRACKS.pop(tid)

        # Match with active tracks
        for tid, track in cls.ACTIVE_TRACKS.items():
            # Spatial distance on BEV map
            dist = math_distance(world_x, world_y, track["world_x"], track["world_y"])
            
            # Appearance distance (1 - Histogram Intersection)
            hist_dist = 1.0 - cv2.compareHist(hist, track["color_histogram"], cv2.HISTCMP_INTERSECT)
            
            # Combined cost: weight spatial proximity (0.6) and appearance similarity (0.4)
            # Spatial distance is normalized: 100 pixels is roughly max distance to associate
            norm_dist = min(1.0, dist / 150.0)
            cost = 0.6 * norm_dist + 0.4 * hist_dist
            
            # Only match if they are relatively close or look identical
            if cost < 0.45 and cost < min_cost:
                min_cost = cost
                best_match_id = tid

        # If matched, update the track. Otherwise, start a new trajectory.
        if best_match_id:
            cls.ACTIVE_TRACKS[best_match_id].update({
                "last_seen": now,
                "world_x": world_x,
                "world_y": world_y,
                "color_histogram": hist
            })
            track_id_str = f"actor_{best_match_id}"
        else:
            new_id = cls.NEXT_TRACK_ID
            cls.NEXT_TRACK_ID += 1
            cls.ACTIVE_TRACKS[new_id] = {
                "last_seen": now,
                "world_x": world_x,
                "world_y": world_y,
                "color_histogram": hist
            }
            track_id_str = f"actor_{new_id}"
            
        logger.info(f"ReID: Associated bbox on Camera #{camera_id} to global ID: {track_id_str} at BEV ({world_x:.1f}, {world_y:.1f})")
        return track_id_str, world_x, world_y


def math_distance(x1, y1, x2, y2) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
import math
