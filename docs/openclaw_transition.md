# OpenClaw Agentic Runtime & MCP Transition Specification

This document details the architectural blueprint for transitioning the NEXUS CCTV project from a Celery-based task queue to a multi-layered OpenClaw agentic runtime.

---

## 1. Architectural Architecture Overview

```
 [ Channels (Dashboard / CLI) ] <== WebSocket (18789) ==> [ OpenClaw Gateway ]
                                                                 |
                                                     +-----------+-----------+
                                                     |           |           |
                                                     v           v           v
                                                 [Supervisor] [Planner] [Executor]
                                                                             |
                                                                             v
                                                                    [ MCP Servers ]
                                                                    (YOLO, Bio, Sign)
```

The runtime decouples logic across the three core OpenClaw layers:
1. **Channel Layer**: Handles frontend SOC WebSocket updates (`ws://127.0.0.1:18789`).
2. **Brain Layer**: Runs the hierarchical AgentX planning nodes (Supervisor, Planner, Executor).
3. **Body Layer**: Invokes domain-specific actions exposed through Model Context Protocol (MCP) servers.

---

## 2. Refactoring Heavy-Lifting to MCP Servers

To allow dynamic discovery of local tools by LLM agents, we refactor python services into three separate MCP Servers:

### A. YOLO Filter MCP (`yolo-filter-mcp`)
* **Tool Name**: `detect_objects`
* **Inputs**: `image_b64: str`
* **Output**: `{"has_targets": bool, "detections": [{"label": str, "box": [int]}]}`
* **Role**: Prevents LLM context bloat by pre-filtering raw frames before executing Qwen-VL.

### B. Biometric Matcher MCP (`biometric-matcher-mcp`)
* **Tool Name**: `match_biometric_face`
* **Inputs**: `image_b64: str`
* **Output**: `{"matched": bool, "name": str, "role": str, "confidence": float}`
* **Role**: Identifies operators, authorized staff, or blacklisted actors.

### C. Forensics Signer MCP (`forensics-signer-mcp`)
* **Tool Name**: `seal_evidence_package`
* **Inputs**: `incident_id: int`
* **Output**: `{"pdf_path": str, "sha256_hash": str, "signed": bool}`
* **Role**: Generates the SHA-256 signed evidence report and adds the tamper-evident signature.

---

## 3. WebSocket Connection & AgentX Loop

Upon connecting to `ws://127.0.0.1:18789`, the OpenClaw Supervisor agent orchestrates the lifecycle:

```python
import asyncio
import websockets
import json

async def start_openclaw_bridge():
    uri = "ws://127.0.0.1:18789"
    async with websockets.connect(uri) as websocket:
        print("Connected to OpenClaw Agentic Runtime.")
        
        # Listen for security events or ingest streams
        async for message in websocket:
            event = json.loads(message)
            if event.get("event") == "camera_trigger":
                # Start AgentX loop
                await run_agentx_pipeline(event["data"])

async def run_agentx_pipeline(data):
    # 1. Supervisor decomposes task
    subtasks = await supervisor_decompose(data)
    
    # 2. Planner arranges tools sequence
    plan = await planner_sequence(subtasks)
    
    # 3. Executor runs the tools (via MCP)
    results = await executor_run(plan)
    
    # 4. Supervisor verifies outcomes against .antigravity/rules.md
    await supervisor_verify(results)
```
