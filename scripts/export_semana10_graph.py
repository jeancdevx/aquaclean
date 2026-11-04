"""Export the compiled topology, never a hand-copied diagram or degree count."""

import csv
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

from langgraph.checkpoint.memory import InMemorySaver

from aquaclean.graphs.main import build_graph


def export(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    runtime = SimpleNamespace(repo=None, actor=None)
    compiled = build_graph(runtime, InMemorySaver())
    for label, xray in [("principal", False), ("subgrafos", True)]:
        topology = compiled.get_graph(xray=xray)
        edges = [
            {"source": e.source, "target": e.target, "conditional": e.conditional}
            for e in topology.edges
        ]
        incoming, outgoing = (
            Counter(e["target"] for e in edges),
            Counter(e["source"] for e in edges),
        )
        nodes = [
            {"id": key, "in_degree": incoming[key], "out_degree": outgoing[key]}
            for key in topology.nodes
        ]
        (destination / f"{label}.json").write_text(
            json.dumps(
                {
                    "origin": "CompiledStateGraph.get_graph",
                    "xray": xray,
                    "nodes": nodes,
                    "edges": edges,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                },
                indent=2,
            )
        )
        (destination / f"{label}.mmd").write_text(topology.draw_mermaid())
        with (destination / f"{label}-grados.csv").open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=["id", "in_degree", "out_degree"])
            writer.writeheader()
            writer.writerows(nodes)
        assert sum(incoming.values()) == sum(outgoing.values()) == len(edges)
        if not xray:
            selected = {"stage", "review", "execute", "respond"}
            subset = [e for e in edges if e["source"] in selected and e["target"] in selected]
            (destination / "hitl-acercamiento.json").write_text(
                json.dumps(
                    {
                        "kind": "induced_subgraph",
                        "selected_nodes": sorted(selected),
                        "edges": subset,
                    },
                    indent=2,
                )
            )
            mermaid = "flowchart TB\n" + "\n".join(
                f"  {e['source']} {'-.->' if e['conditional'] else '-->'} {e['target']}"
                for e in subset
            )
            (destination / "hitl-acercamiento.mmd").write_text(
                mermaid + "\nstyle review fill:#fef3c7,stroke:#92400e\n"
            )


if __name__ == "__main__":
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    export(root / "02-langgraph")
