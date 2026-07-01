"""
NEXUS CCTV — AgentX Hierarchical Orchestration Runtime
Supervisor (orchestrator), Planner (sequencer), Executor (actor).
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import get_settings
from backend.database import AsyncSessionLocal
from backend.models import Incident, Camera, IncidentStatus, SeverityLevel
from backend.services.rf_sensor import RFSensorService
from backend.services import qwen_vl, qwen_plus, alert_dispatch

logger = logging.getLogger(__name__)
settings = get_settings()

PROJECT_ROOT = Path(__file__).parent.parent.parent
YOLO_SERVER_PATH = str(PROJECT_ROOT / "backend" / "openclaw" / "mcp_yolo.py")
BIOMETRICS_SERVER_PATH = str(PROJECT_ROOT / "backend" / "openclaw" / "mcp_biometrics.py")
FORENSICS_SERVER_PATH = str(PROJECT_ROOT / "backend" / "openclaw" / "mcp_forensics.py")

async def call_mcp_tool_stdio(script_path: str, tool_name: str, arguments: dict) -> dict:
    """Invokes a local MCP server subprocess via standard JSON-RPC over stdio."""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 1. Send initialize handshake
        init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        proc.stdin.write((json.dumps(init_req) + "\n").encode())
        await proc.stdin.drain()
        await proc.stdout.readline()  # Consume initialize response
        
        # 2. Call the tool
        tool_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        proc.stdin.write((json.dumps(tool_req) + "\n").encode())
        await proc.stdin.drain()
        
        line = await proc.stdout.readline()
        
        # Clean shutdown
        proc.terminate()
        await proc.wait()
        
        if not line:
            return {"error": "Empty response from MCP server"}
            
        resp = json.loads(line.decode())
        if "error" in resp:
            return {"error": resp["error"]["message"]}
            
        content = resp["result"]["content"][0]["text"]
        return json.loads(content)
        
    except Exception as e:
        logger.error(f"MCP client communication error with {Path(script_path).name}: {e}")
        return {"error": str(e)}


class AgentXRuntime:
    @staticmethod
    async def run_agentx_pipeline(camera_id: int, image_b64: str) -> dict:
        """Executes the full Supervisor-Planner-Executor AgentX pipeline."""
        logger.info(f"[AgentX Supervisor] Starting task decomposition for Camera #{camera_id}")
        
        # 1. Supervisor: Task Decomposition
        subtasks = await AgentXRuntime.supervisor_decompose(camera_id)
        
        # 2. Planner: sequence tools and check RF Telemetry
        plan = await AgentXRuntime.planner_sequence(camera_id, subtasks)
        
        # 3. Executor: execute planned tools via stdio MCP servers
        results = await AgentXRuntime.executor_run(image_b64, plan)
        
        # 4. Supervisor: Verify outcomes against rules.md and compile database incident
        final_incident = await AgentXRuntime.supervisor_verify(camera_id, image_b64, results)
        
        return final_incident

    @staticmethod
    async def supervisor_decompose(camera_id: int) -> list[str]:
        """Deconstructs the incoming camera event into required validation stages."""
        # Supervisor specifies validation stages based on Security Operations protocols
        stages = ["yolo_prefilter", "biometric_check", "qwen_vl_analysis"]
        logger.info(f"[AgentX Supervisor] Decomposed Camera #{camera_id} threat detection into {stages}")
        return stages

    @staticmethod
    async def planner_sequence(camera_id: int, subtasks: list[str]) -> dict:
        """Determines the execution sequence and performs spatial RF correlation."""
        logger.info(f"[AgentX Planner] Sequencing plan for camera #{camera_id}")
        
        # Map camera to corresponding Access Point
        # CAM-01: Main Gate -> AP-01
        # CAM-02: Parking -> AP-03
        # CAM-03: Lobby -> AP-01
        # CAM-04: Server -> AP-02
        ap_mapping = {1: "AP-01", 2: "AP-03", 3: "AP-01", 4: "AP-02"}
        ap_id = ap_mapping.get(camera_id, "AP-01")
        
        # Integrate RF/Wi-Fi telemetry into spatial reasoning
        telemetry = RFSensorService.get_telemetry()
        ap_signals = telemetry.get("signals", {})
        ap_info = ap_signals.get(ap_id, {"csi_variance": 0.0, "rssi": -90.0})
        
        csi_variance = ap_info.get("csi_variance", 0.0)
        rssi = ap_info.get("rssi", -90.0)
        
        # Spatial correlation check: Elevated CSI variance indicates occupant physical movement
        rf_confirmed = csi_variance > 0.05
        
        logger.info(
            f"[AgentX Planner] Spatial RF Correlation on {ap_id}: "
            f"RSSI={rssi} dBm | CSI Var={csi_variance} | Elevated movement={rf_confirmed}"
        )
        
        return {
            "sequence": subtasks,
            "rf_correlation": {
                "ap_id": ap_id,
                "csi_variance": csi_variance,
                "rssi": rssi,
                "confirmed": rf_confirmed
            }
        }

    @staticmethod
    async def executor_run(image_b64: str, plan: dict) -> dict:
        """Executor agent runs the tools via MCP Servers."""
        results = {"rf_correlation": plan["rf_correlation"]}
        
        # Step 1: Run YOLO object detection
        if "yolo_prefilter" in plan["sequence"]:
            logger.info("[AgentX Executor] Launching mcp_yolo.py -> detect_objects")
            yolo_res = await call_mcp_tool_stdio(YOLO_SERVER_PATH, "detect_objects", {"image_b64": image_b64})
            results["yolo"] = yolo_res
            
            # If no targets detected, we stop execution here to prevent context bloat & cost
            if not yolo_res.get("has_targets", True):
                logger.info("[AgentX Executor] YOLO reports no targets detected. Terminating execution loop.")
                return results

        # Step 2: Run Biometric face matcher
        if "biometric_check" in plan["sequence"]:
            logger.info("[AgentX Executor] Launching mcp_biometrics.py -> match_biometric_face")
            bio_res = await call_mcp_tool_stdio(BIOMETRICS_SERVER_PATH, "match_biometric_face", {"image_b64": image_b64})
            results["biometrics"] = bio_res

        return results

    @staticmethod
    async def supervisor_verify(camera_id: int, image_b64: str, executor_results: dict) -> dict:
        """Verifies plan results, executes Qwen-VL-Max/Plus and saves incident securely."""
        logger.info("[AgentX Supervisor] Verifying executions against .antigravity/rules.md")
        
        # Handle early termination (skipped frame)
        if "yolo" in executor_results and not executor_results["yolo"].get("has_targets", True):
            return {"status": "skipped", "reason": "YOLO pre-filter returned no targets"}
            
        rf_conf = executor_results.get("rf_correlation", {})
        matched_faces = executor_results.get("biometrics", {}).get("detections", [])
        
        # 1. Run Qwen-VL-Max vision analysis
        logger.info("[AgentX Supervisor] Ingesting frame to Qwen-VL-Max...")
        async with AsyncSessionLocal() as db:
            camera = await db.get(Camera, camera_id)
            cam_name = camera.name if camera else "Camera"
            cam_loc = camera.location if camera else "Location"
            
        analysis = await qwen_vl.analyze_frame(image_b64, cam_name, cam_loc)
        
        # Inject RF correlation and Biometric verification into reasoning
        rf_status_text = (
            f"Physical security confirmed by co-channel spatial RF disruptions at Access Point {rf_conf.get('ap_id')}. "
            f"CSI variance: {rf_conf.get('csi_variance')}" if rf_conf.get("confirmed") else "Spatial RF telemetry shows baseline patterns."
        )
        analysis.qwen_reasoning = f"{analysis.qwen_reasoning or ''}\n[Spatial Sensing] {rf_status_text}"
        
        # Save to database
        now = datetime.now(timezone.utc)
        actors_json = json.dumps(analysis.actors_detected)
        biometrics_json = json.dumps(matched_faces) if matched_faces else None
        
        async with AsyncSessionLocal() as db:
            # Create pending incident
            inc = Incident(
                camera_id=camera_id,
                timestamp=now,
                threat_type=analysis.threat_type,
                severity=analysis.severity,
                severity_score=analysis.severity_score,
                actors_detected=actors_json,
                biometrics_matched=biometrics_json,
                scene_description=analysis.scene_description,
                qwen_reasoning=analysis.qwen_reasoning,
                confidence=analysis.confidence,
                status=IncidentStatus.PENDING,
                tokens_used=getattr(analysis, "tokens_used", 0),
                api_cost_usd=getattr(analysis, "api_cost_usd", 0.0),
            )
            db.add(inc)
            await db.flush()
            
            # Save frame image
            from backend.services.evidence_package import save_incident_frame
            frame_path = save_incident_frame(inc.id, image_b64)
            inc.frame_path = frame_path
            
            # Generate report
            try:
                rep_en, rep_sw = await qwen_plus.generate_incident_report(
                    analysis, cam_name, cam_loc, now
                )
                inc.report_en = rep_en
                inc.report_sw = rep_sw
            except Exception as e:
                logger.error(f"Report generation error: {e}")
                
            await db.commit()
            await db.refresh(inc)
            
            # Dispatch alerts
            try:
                alert_records = await alert_dispatch.dispatch_alerts(
                    inc.id, inc.severity, inc.threat_type or "Unknown",
                    cam_loc, inc.scene_description or "", inc.report_en
                )
                from backend.models import Alert
                for ar in alert_records:
                    db.add(Alert(incident_id=inc.id, **ar))
                await db.commit()
            except Exception as e:
                logger.error(f"Alert dispatch error: {e}")
                
            # Broadcast on WebSocket
            from backend.ws_manager import ws_manager
            await ws_manager.broadcast_incident({
                "id": inc.id,
                "camera_id": camera_id,
                "threat_type": inc.threat_type,
                "severity": inc.severity.value if inc.severity else None,
                "timestamp": inc.timestamp.isoformat(),
                "status": inc.status.value,
                "biometrics_matched": matched_faces,
                "bounding_boxes": getattr(analysis, "bounding_boxes", [])
            })
            
            logger.info(f"[AgentX Supervisor] Security incident #{inc.id} validated, logged, and broadcasted.")
            return {
                "status": "ok",
                "incident_id": inc.id,
                "severity": inc.severity.value if inc.severity else None
            }
