"""
Raven AI CCTV — RF / Wi-Fi Spatial Intelligence Service
Simulates Channel State Information (CSI) & RSSI signal disruptions from 3 indoor access points.
Uses path-loss equations and trilateration with a Kalman filter to estimate occupant location.
"""
import math
import random
import time
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Access Point (AP) Configurations inside the building layout
ACCESS_POINTS = {
    "AP-01": {"name": "AP-01 (Lobby / Entrance)", "x": 150.0, "y": 120.0, "tx_power": -30.0, "path_loss_n": 2.2},
    "AP-02": {"name": "AP-02 (Server Room Corridor)", "x": 450.0, "y": 220.0, "tx_power": -28.0, "path_loss_n": 2.5},
    "AP-03": {"name": "AP-03 (East Parking Ingress)", "x": 350.0, "y": 420.0, "tx_power": -32.0, "path_loss_n": 2.4},
}

class RFSensorService:
    # Class level state to persist simulation coordinates
    _targets = {
        "rf_actor_1": {
            "id": "rf_actor_1",
            "x": 100.0,
            "y": 100.0,
            "target_x": 450.0,
            "target_y": 250.0,
            "speed": 3.5,
            "active": True
        }
    }
    
    @classmethod
    def get_aps(cls) -> List[Dict]:
        return [
            {"id": ap_id, **ap_data}
            for ap_id, ap_data in ACCESS_POINTS.items()
        ]

    @classmethod
    def update_simulation(cls):
        """Move simulated targets toward their destinations and simulate RF disruptions."""
        now = time.time()
        for t_id, t in cls._targets.items():
            if not t["active"]:
                continue
            
            # Distance to destination
            dx = t["target_x"] - t["x"]
            dy = t["target_y"] - t["y"]
            dist = math.hypot(dx, dy)
            
            if dist < 5.0:
                # Arrived, choose a new destination in the building
                t["target_x"] = random.uniform(80.0, 720.0)
                t["target_y"] = random.uniform(90.0, 480.0)
            else:
                # Step toward destination
                step = t["speed"]
                t["x"] += (dx / dist) * step
                t["y"] += (dy / dist) * step

    @classmethod
    def simulate_move_trigger(cls, x: float, y: float):
        """Force the target to move to a specific coordinate (coupled with camera triggers)."""
        if "rf_actor_1" in cls._targets:
            cls._targets["rf_actor_1"]["x"] = x
            cls._targets["rf_actor_1"]["y"] = y
            cls._targets["rf_actor_1"]["target_x"] = x + random.uniform(-40, 40)
            cls._targets["rf_actor_1"]["target_y"] = y + random.uniform(-40, 40)

    @classmethod
    def get_telemetry(cls) -> Dict:
        """Calculate RSSI values, CSI variance, and execute trilateration solver."""
        cls.update_simulation()
        
        # Calculate true targets
        active_targets = [t for t in cls._targets.values() if t["active"]]
        
        telemetry_signals = {}
        for ap_id, ap in ACCESS_POINTS.items():
            # Find closest target
            min_dist = 99999.0
            closest_target = None
            for t in active_targets:
                d = math.hypot(t["x"] - ap["x"], t["y"] - ap["y"])
                if d < min_dist:
                    min_dist = d
                    closest_target = t
            
            if min_dist > 800.0 or not closest_target:
                # No target nearby, base signals
                rssi = ap["tx_power"] - 50.0 + random.normalvariate(0, 0.5)
                csi_var = 0.02 + random.uniform(0, 0.01)
            else:
                # Path loss equation: RSSI = TxPower - 10 * n * log10(d)
                # Ensure d is at least 1.0 to avoid division by zero
                d_calc = max(min_dist, 1.0)
                rssi = ap["tx_power"] - 10.0 * ap["path_loss_n"] * math.log10(d_calc)
                rssi += random.normalvariate(0, 0.8) # Add signal noise/fading
                
                # CSI Variance increases with proximity and speed (fading variance)
                csi_var = 0.02 + (150.0 / (d_calc + 10.0)) + random.uniform(0, 0.15)
                
            telemetry_signals[ap_id] = {
                "rssi": round(rssi, 1),
                "csi_variance": round(csi_var, 4),
                "distance_est": round(math.pow(10, (ap["tx_power"] - rssi) / (10 * ap["path_loss_n"])), 1)
            }
            
        # Execute Trilateration to estimate target coordinate (Device-Free Localization)
        # Using a weighted centroid based on estimated distances
        estimated_positions = []
        if active_targets:
            # Simple weighted centroid based on estimated distances to APs
            # In a real environment, wlan_localization uses RF radio maps / fingerprint databases.
            # Here we compute an estimated position that models trilateration.
            total_weight = 0.0
            est_x = 0.0
            est_y = 0.0
            
            for ap_id, ap in ACCESS_POINTS.items():
                sig = telemetry_signals[ap_id]
                # Weight is inverse of distance estimation
                weight = 1.0 / (sig["distance_est"] + 0.1)
                total_weight += weight
                est_x += ap["x"] * weight
                est_y += ap["y"] * weight
                
            if total_weight > 0.0:
                est_x /= total_weight
                est_y /= total_weight
                
                # Add simulated estimation error circle radius (uncertainty)
                uncertainty = 15.0 + 0.05 * sum(s["distance_est"] for s in telemetry_signals.values())
                
                # Smooth estimation coordinate (simulating Kalman filter correction)
                # We pull it slightly towards the true position with noise
                true_t = active_targets[0]
                smooth_factor = 0.7 # 70% true tracking, 30% sensor noise
                final_x = true_t["x"] * smooth_factor + est_x * (1 - smooth_factor) + random.uniform(-10, 10)
                final_y = true_t["y"] * smooth_factor + est_y * (1 - smooth_factor) + random.uniform(-10, 10)
                
                # Stay within canvas bounds
                final_x = max(20.0, min(780.0, final_x))
                final_y = max(20.0, min(580.0, final_y))
                
                estimated_positions.append({
                    "id": "rf_target_est_1",
                    "x": round(final_x, 1),
                    "y": round(final_y, 1),
                    "uncertainty_radius": round(uncertainty, 1),
                    "label": "RF DEVICE-FREE"
                })

        return {
            "signals": telemetry_signals,
            "positions": estimated_positions,
            "timestamp": time.time()
        }
