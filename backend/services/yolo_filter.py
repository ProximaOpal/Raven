"""
Raven AI CCTV — YOLOv8-nano Pre-filter
Detects persons/vehicles in frames before sending to Qwen-VL-Max.
Reduces API costs by ~85% by skipping empty frames.
"""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Target classes for security monitoring
SECURITY_CLASSES = {
    0: "person",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    # 24: backpack, 26: handbag — can add for contraband detection
}

CONFIDENCE_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45


@dataclass
class Detection:
    label: str
    x: int
    y: int
    w: int
    h: int
    confidence: float


@dataclass
class FilterResult:
    has_targets: bool
    detections: list[Detection]
    frame_width: int
    frame_height: int


_model = None  # Lazy-loaded


def _get_model():
    """Lazy-load YOLOv8-nano (downloads weights on first call ~6MB)."""
    global _model
    if _model is None:
        try:
            from ultralytics import YOLO
            _model = YOLO("yolov8n.pt")
            logger.info("YOLOv8-nano loaded successfully")
        except Exception as e:
            logger.warning(f"YOLOv8 load failed (will pass all frames): {e}")
            _model = None
    return _model


def detect_targets(frame) -> FilterResult:
    """
    Run YOLOv8-nano on a frame (numpy array BGR).
    Returns FilterResult with detection boxes.
    If YOLO unavailable, passes frame through (has_targets=True).
    """
    model = _get_model()

    h, w = frame.shape[:2] if hasattr(frame, "shape") else (480, 640)

    if model is None:
        # Graceful degradation: pass all frames through
        return FilterResult(has_targets=True, detections=[], frame_width=w, frame_height=h)

    try:
        results = model(
            frame,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            classes=list(SECURITY_CLASSES.keys()),
            verbose=False,
        )

        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in SECURITY_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                detections.append(Detection(
                    label=SECURITY_CLASSES[cls_id],
                    x=x1,
                    y=y1,
                    w=x2 - x1,
                    h=y2 - y1,
                    confidence=float(box.conf[0]),
                ))

        return FilterResult(
            has_targets=len(detections) > 0,
            detections=detections,
            frame_width=w,
            frame_height=h,
        )

    except Exception as e:
        logger.error(f"YOLOv8 inference error: {e}")
        return FilterResult(has_targets=True, detections=[], frame_width=w, frame_height=h)


def detections_to_boxes(result: FilterResult) -> list[dict]:
    """Convert FilterResult detections to JSON-serialisable bounding boxes."""
    return [
        {
            "label": d.label,
            "x": d.x,
            "y": d.y,
            "w": d.w,
            "h": d.h,
            "conf": round(d.confidence, 3),
        }
        for d in result.detections
    ]
