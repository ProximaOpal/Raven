"""
NEXUS CCTV — Stdio-based Model Context Protocol (MCP) Server Helper
Implements JSON-RPC 2.0 protocol over stdin/stdout for seamless OpenClaw integration.
"""
import sys
import json
import traceback

class MCPServer:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools = {}

    def tool(self, name: str, description: str, input_schema: dict):
        def decorator(func):
            self.tools[name] = {
                "func": func,
                "description": description,
                "schema": input_schema
            }
            return func
        return decorator

    def run(self):
        # Configure output channel to handle UTF-8 without system-default limitations
        sys.stdout.reconfigure(encoding='utf-8')
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line)
                method = request.get("method")
                req_id = request.get("id")
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": self.name,
                                "version": self.version
                            }
                        }
                    }
                elif method == "notifications/initialized":
                    continue
                elif method == "tools/list":
                    tools_list = []
                    for t_name, t_info in self.tools.items():
                        tools_list.append({
                            "name": t_name,
                            "description": t_info["description"],
                            "inputSchema": t_info["schema"]
                        })
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": tools_list
                        }
                    }
                elif method == "tools/call":
                    params = request.get("params", {})
                    t_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if t_name in self.tools:
                        try:
                            # Run tool
                            res = self.tools[t_name]["func"](**arguments)
                            if not isinstance(res, str):
                                res = json.dumps(res)
                            response = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "result": {
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": res
                                        }
                                    ]
                                }
                            }
                        except Exception as ex:
                            err_msg = traceback.format_exc()
                            print(f"Error running tool {t_name}: {err_msg}", file=sys.stderr)
                            response = {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32603,
                                    "message": f"Error running tool: {str(ex)}"
                                }
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method/Tool not found: {t_name}"
                            }
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}"
                        }
                    }
                
                # Send response back to client (never use normal print/stdout logging)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
                
            except Exception as e:
                print(f"MCP Loop Exception: {traceback.format_exc()}", file=sys.stderr)
