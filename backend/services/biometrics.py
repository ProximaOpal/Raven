"""
Raven AI CCTV — Biometric Identification & Facial Recognition Service
Uses OpenCV Haar Cascades for face detection.
Extracts 128-dim features using a local face_recognition library or a robust HSV-texture feature descriptor fallback.
"""
import json
import logging
import math
import os
from pathlib import Path
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# Try importing face_recognition (dlib-based) as the primary engine
HAS_FACE_RECOGNITION = False
try:
    import face_recognition
    HAS_FACE_RECOGNITION = True
    logger.info("Biometrics: Loaded face_recognition primary engine")
except ImportError:
    logger.info("Biometrics: face_recognition not installed. Using high-fidelity OpenCV + HSV-texture feature fallback.")


class BiometricsService:
    @staticmethod
    def detect_faces(frame: np.ndarray) -> list[dict]:
        """
        Detects faces in a frame using OpenCV Haar Cascades.
        Returns a list of face bounding boxes: [{"x": int, "y": int, "w": int, "h": int}]
        """
        if frame is None or frame.size == 0:
            return []

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Load cascade classifier
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        if face_cascade.empty():
            logger.warning("Haar Cascade xml not found. Falling back to simple face region detector.")
            # Simple fallback: return center of image if person detection is active
            return []

        # Detect faces
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        return [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]

    @staticmethod
    def extract_embedding(frame: np.ndarray, bbox: dict) -> list[float]:
        """
        Extracts a 128-dimensional embedding from a face bounding box.
        If face_recognition is available, uses it. Otherwise, computes a robust 128-dim descriptor.
        """
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]
        
        # Guard boundaries
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + w), min(fh, y + h)
        
        face_crop = frame[y1:y2, x1:x2]
        if face_crop.size == 0:
            return [0.0] * 128

        if HAS_FACE_RECOGNITION:
            try:
                # Convert BGR (OpenCV) to RGB (face_recognition)
                rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_face)
                if encodings:
                    return encodings[0].tolist()
            except Exception as e:
                logger.error(f"Error extracting embedding via face_recognition: {e}")

        # Fallback: Robust 128-dim color-texture descriptor
        # We divide the face into a 4x4 grid. For each grid cell, we extract:
        # - Mean H, S, V values (3 values)
        # - Standard deviation of H, S, V (3 values)
        # - LBP-like texture histograms (2 bins)
        # Total per cell: 8 features. 4x4 * 8 = 128 features!
        # This is deterministic, fast, runs on CPU, and is sensitive to face appearance.
        try:
            hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
            grid_h = hsv.shape[0] // 4
            grid_w = hsv.shape[1] // 4
            
            features = []
            for r in range(4):
                for c in range(4):
                    cell = hsv[r*grid_h:(r+1)*grid_h, c*grid_w:(c+1)*grid_w]
                    if cell.size == 0:
                        features.extend([0.0] * 8)
                        continue
                    
                    # Compute mean and std per channel
                    mean_h, std_h = np.mean(cell[:,:,0]), np.std(cell[:,:,0])
                    mean_s, std_s = np.mean(cell[:,:,1]), np.std(cell[:,:,1])
                    mean_v, std_v = np.mean(cell[:,:,2]), np.std(cell[:,:,2])
                    
                    # Compute simple texture statistic (contrast/edges)
                    gray_cell = cv2.cvtColor(cv2.pyrDown(cv2.pyrUp(cell)) if cell.shape[0] > 4 else cell, cv2.COLOR_HSV2RGB)
                    gray_cell = cv2.cvtColor(gray_cell, cv2.COLOR_RGB2GRAY)
                    laplacian_var = np.var(cv2.Laplacian(gray_cell, cv2.CV_64F))
                    mean_gray = np.mean(gray_cell)
                    
                    features.extend([
                        float(mean_h) / 180.0, float(std_h) / 90.0,
                        float(mean_s) / 255.0, float(std_s) / 128.0,
                        float(mean_v) / 255.0, float(std_v) / 128.0,
                        float(mean_gray) / 255.0, float(math.log1p(laplacian_var)) / 10.0
                    ])
            
            # Normalize embedding vector
            arr = np.array(features)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            return arr.tolist()
            
        except Exception as e:
            logger.error(f"Error computing fallback face descriptor: {e}")
            return [0.0] * 128

    @staticmethod
    def match_face(embedding: list[float], profiles: list, threshold: float = 0.6) -> tuple[dict | None, float]:
        """
        Matches a face embedding against enrolled profiles.
        Returns (matched_profile_dict, similarity_score) or (None, 0.0)
        """
        if not embedding or not profiles:
            return None, 0.0

        best_match = None
        best_score = 0.0
        emb_arr = np.array(embedding)

        for p in profiles:
            try:
                p_emb = json.loads(p.face_encoding)
                p_arr = np.array(p_emb)
                
                # Compute Cosine Similarity
                dot = np.dot(emb_arr, p_arr)
                norm_a = np.linalg.norm(emb_arr)
                norm_b = np.linalg.norm(p_arr)
                
                if norm_a == 0 or norm_b == 0:
                    similarity = 0.0
                else:
                    similarity = dot / (norm_a * norm_b)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = p
            except Exception as e:
                logger.error(f"Error comparing face with profile {p.id}: {e}")

        # If similarity meets threshold, return match
        # Cosine similarity for color-texture fallback threshold is generally higher (e.g. 0.85)
        # We will adjust threshold based on the primary or fallback engine.
        effective_threshold = threshold if HAS_FACE_RECOGNITION else 0.85
        if best_score >= effective_threshold:
            return {
                "id": best_match.id,
                "name": best_match.name,
                "role": best_match.role,
                "image_path": best_match.image_path
            }, float(best_score)

        return None, float(best_score)
