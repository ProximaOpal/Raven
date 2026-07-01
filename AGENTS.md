# AgentX Orchestration Pattern & HITL Guardrails

This document establishes the AgentX hierarchical orchestration pattern and defines the strict Human-in-the-Loop (HITL) safety boundaries for the NEXUS CCTV system.

---

## 1. AgentX Hierarchical Planning

The agentic workspace is divided into three specialized nodes:

```
         [ Supervisor Agent ] (Task Decomposition & Validation)
                  |
                  v
          [ Planner Agent ]    (Tool-Step Sequencing & Dependency Checks)
                  |
                  v
         [ Executor Agent ]   (Tool Invocation & System Execution)
```

### Supervisor Agent (Orchestrator)
* Deconstructs incoming security incidents and alerts.
* Assigns sub-tasks to the Planner.
* Validates final output reports against `.antigravity/rules.md` (Forensic Standards).

### Planner Agent (Sequencer)
* Determines the exact sequence of tool executions required (e.g., YOLO filter -> Biometric check -> Trajectory projection).
* Checks requirements and handles data pipelines between tools.

### Executor Agent (Actor)
* Communicates directly with the OpenClaw Body and MCP Servers.
* Runs local commands, accesses the sqlite database, and handles raw file uploads.

---

## 2. Human-in-the-Loop (HITL) Guardrails

To prevent unauthorized actions, the system enforces **Zero-Autonomy** (requiring explicit human confirmation via the SOC Review Panel) for the following trigger operations:

### A. Law Enforcement Escalation
* **Trigger**: Any workflow attempting to dispatch an SMS/Email alert to external security responders or local emergency authorities.
* **Requirement**: The Supervisor agent must pause execution, generate a draft incident package, and wait for an operator to click **APPROVE** or **ESCALATE**.

### B. Destructive File/Data Actions
* **Trigger**: Any command attempting to delete, reset, or overwrite:
  * The database (`nexus.db` or PostgreSQL relations).
  * Enrolled biometrics profiles or face embeddings.
  * Audit logs (`audit_log` tables).
* **Requirement**: A CLI or Web UI prompt must block execution until a super-operator enters credentials and approves the request.
