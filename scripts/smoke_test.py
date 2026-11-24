"""End-to-End Smoke Test for NOESIS.

Launches the FastAPI server on a test port, executes actual HTTP requests against:
- GET /api/v1/health
- GET /api/v1/graph
- POST /api/v1/query/structured (3-Hop Traversal)
- POST /api/v1/counterfactual (Evidence Ablation)
and prints verified actual results.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PORT = 8000
BASE_URL = f"http://127.0.0.1:{PORT}"


def wait_for_server(url: str, timeout: int = 15):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(f"{url}/api/v1/health") as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_smoke_test():
    print(f"[1/5] Launching NOESIS backend on port {PORT}...", flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(PORT),
        "--log-level",
        "warning",
    ]

    proc = subprocess.Popen(cmd, env=env)

    try:
        if not wait_for_server(BASE_URL):
            print("ERROR: Server failed to start within timeout.")
            sys.exit(1)

        print("[2/5] Server online! Verifying GET /api/v1/health...", flush=True)
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/health") as resp:
            health_data = json.loads(resp.read().decode())
            print(f"  Status: {health_data['status']}")
            print(f"  Storage Mode: {health_data['storage_mode']}")
            print(f"  Total Entities: {health_data['total_entities']}")
            print(f"  Total Claims: {health_data['total_claims']}")
            print(f"  Total Documents: {health_data['total_documents']}")

        print("[3/5] Verifying GET /api/v1/graph...", flush=True)
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/graph") as resp:
            graph_data = json.loads(resp.read().decode())
            nodes_count = len(graph_data["elements"]["nodes"])
            edges_count = len(graph_data["elements"]["edges"])
            print(f"  Cytoscape Nodes: {nodes_count}, Edges: {edges_count}")

        print("[4/5] Executing 3-Hop Traversal Query: Project Prometheus -> Tech...", flush=True)
        query_payload = {
            "start_entity": "ent_proj_prometheus",
            "steps": [
                {"predicate": "WORKED_ON", "direction": "incoming"},
                {"predicate": "FOUNDED", "direction": "outgoing"},
                {"predicate": "DEVELOPED", "direction": "outgoing"},
            ],
            "return_type": "TECHNOLOGY",
            "max_hops": 3,
        }
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/query/structured",
            data=json.dumps(query_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            query_res = json.loads(resp.read().decode())
            print(f"  Query Status: {query_res['status']}")
            print(f"  Hop Count: {query_res['hop_count']}")
            print(f"  Execution Time: {query_res['execution_time_ms']} ms")
            print(f"  Path Confidence: {query_res['confidence']}")
            print(f"  Matching Entities: {[m['canonical_name'] for m in query_res['matching_entities']]}")
            print(f"  Paths Established: {len(query_res['paths'])}")
            for idx, p in enumerate(query_res['paths']):
                path_str = " -> ".join([seg["from_entity"]["canonical_name"] for seg in p["segments"]] + [p["terminal_entity"]["canonical_name"]])
                print(f"    Path {idx + 1}: {path_str} (Confidence: {p['path_confidence']})")

        print("[5/5] Executing Counterfactual Evidence Ablation on Synaptic Core...", flush=True)
        ablation_payload = {
            "query_plan": query_payload,
            "target_entity_id": "ent_tech_synaptic_core",
        }
        ablation_req = urllib.request.Request(
            f"{BASE_URL}/api/v1/counterfactual",
            data=json.dumps(ablation_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(ablation_req) as resp:
            ablation_res = json.loads(resp.read().decode())
            print(f"  Ablation Summary: {ablation_res['summary']}")
            print(f"  Critical Sources: {ablation_res['critical_sources']}")
            print(f"  Redundant Sources: {ablation_res['redundant_sources']}")
            print(f"  Robustness Score R(a): {ablation_res['robustness_score']}")

        print("\nALL END-TO-END SMOKE TESTS PASSED CLEANLY!", flush=True)

    finally:
        print("Terminating server process...", flush=True)
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    run_smoke_test()
