"""
Educational Mobile Computing Assignment 3 simulator.
Pure Python standard library; no external packages required.

Models:
- wireless connectivity as a geometric graph
- mobile-node random-walk movement and handoff events
- Mobile IP home-address -> care-of-address registration and tunnel overhead
- DSDV-style periodic route-table refresh
- AODV-style on-demand route discovery and route caching
- packet delivery, end-to-end delay and routing-control overhead

This is a teaching simulator, not a standards-compliant implementation of
RFC Mobile IPv4, DSDV, or AODV, and not a substitute for ns-3/OMNeT++.
"""
from __future__ import annotations
import argparse
import csv
import math
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

@dataclass
class Metrics:
    sent: int = 0
    delivered: int = 0
    lost: int = 0
    delay_total_ms: float = 0.0
    routing_control_messages: int = 0
    handoffs: int = 0
    mobile_ip_registrations: int = 0
    tunnel_bytes: int = 0

    @property
    def pdr(self) -> float:
        return (100.0 * self.delivered / self.sent) if self.sent else 0.0

    @property
    def avg_delay_ms(self) -> float:
        return (self.delay_total_ms / self.delivered) if self.delivered else 0.0

@dataclass
class Node:
    node_id: int
    x: float
    y: float
    home_network: int = 0
    current_network: int = 0
    care_of_address: str = ""
    home_address: str = ""

def distance(a: Node, b: Node) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)

def build_graph(nodes: List[Node], radio_range: float) -> Dict[int, List[int]]:
    graph = {n.node_id: [] for n in nodes}
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if distance(a, b) <= radio_range:
                graph[a.node_id].append(b.node_id)
                graph[b.node_id].append(a.node_id)
    return graph

def shortest_path(graph: Dict[int, List[int]], source: int, destination: int) -> Optional[List[int]]:
    if source == destination:
        return [source]
    queue = deque([source])
    parent = {source: None}
    while queue:
        u = queue.popleft()
        for v in graph.get(u, []):
            if v not in parent:
                parent[v] = u
                if v == destination:
                    path = [destination]
                    while parent[path[-1]] is not None:
                        path.append(parent[path[-1]])
                    return list(reversed(path))
                queue.append(v)
    return None

def make_nodes(count: int, rng: random.Random) -> List[Node]:
    nodes = []
    side = 100.0
    for i in range(count):
        x, y = rng.uniform(5, side-5), rng.uniform(5, side-5)
        network = int(x // 25)  # four conceptual visited-network zones
        nodes.append(Node(i, x, y, 0, network,
                          f"10.0.{network}. {i+10}".replace(" ", ""),
                          f"192.0.2.{i+1}"))
    return nodes

def move_nodes(nodes: List[Node], mobility: str, rng: random.Random) -> int:
    # Mobility is represented by per-round random-walk distance.
    step = {"low": 1.0, "medium": 4.0, "high": 9.0}[mobility]
    changes = 0
    for n in nodes:
        old_network = n.current_network
        angle = rng.uniform(0, 2 * math.pi)
        n.x = min(99.0, max(1.0, n.x + math.cos(angle) * step))
        n.y = min(99.0, max(1.0, n.y + math.sin(angle) * step))
        n.current_network = int(n.x // 25)
        if n.current_network != old_network:
            changes += 1
            n.care_of_address = f"10.0.{n.current_network}.{n.node_id+10}"
    return changes

def run_case(protocol: str, node_count: int, mobility: str, seed: int,
             rounds: int = 30, radio_range: float = 32.0,
             packets_per_round: int = 5, dsdv_update_interval: int = 3) -> Metrics:
    rng = random.Random(seed)
    nodes = make_nodes(node_count, rng)
    metrics = Metrics()
    dsdv_tables: Dict[Tuple[int, int], Optional[List[int]]] = {}
    aodv_cache: Dict[Tuple[int, int], Tuple[Optional[List[int]], int]] = {}
    aodv_cache_lifetime = 3

    for tick in range(rounds):
        handoffs = move_nodes(nodes, mobility, rng)
        metrics.handoffs += handoffs
        # Mobile IP registration is modelled whenever a node changes visited zone.
        metrics.mobile_ip_registrations += handoffs

        graph = build_graph(nodes, radio_range)

        if protocol.upper() == "DSDV" and (tick % dsdv_update_interval == 0):
            # Simplified network-wide periodic table exchange cost.
            metrics.routing_control_messages += node_count * max(0, node_count - 1)
            dsdv_tables.clear()
            for s in range(node_count):
                for d in range(node_count):
                    if s != d:
                        dsdv_tables[(s, d)] = shortest_path(graph, s, d)

        for _ in range(packets_per_round):
            source, destination = rng.sample(range(node_count), 2)
            metrics.sent += 1
            key = (source, destination)
            route = None
            discovery_delay = 0.0

            if protocol.upper() == "DSDV":
                route = dsdv_tables.get(key)
                # Before the first periodic update, use no route.
                if route is None:
                    metrics.lost += 1
                    continue
                # Validate cached route links against the current graph.
                valid = all(route[i+1] in graph.get(route[i], []) for i in range(len(route)-1))
                if not valid:
                    metrics.lost += 1
                    continue
            else:  # AODV-style on-demand discovery/cache
                cached = aodv_cache.get(key)
                if cached and cached[1] >= tick:
                    route = cached[0]
                    if route is not None:
                        valid = all(route[i+1] in graph.get(route[i], []) for i in range(len(route)-1))
                        if not valid:
                            route = None
                if route is None:
                    route = shortest_path(graph, source, destination)
                    # Flood request + reply cost, approximated using reachable nodes.
                    reachable = set()
                    q = deque([source])
                    reachable.add(source)
                    while q:
                        u = q.popleft()
                        for v in graph.get(u, []):
                            if v not in reachable:
                                reachable.add(v); q.append(v)
                    metrics.routing_control_messages += len(reachable) + (len(route)-1 if route else 0)
                    discovery_delay = 12.0
                    aodv_cache[key] = (route, tick + aodv_cache_lifetime)

            if route is None:
                metrics.lost += 1
                continue

            hops = max(0, len(route) - 1)
            # 2 ms per wireless hop; AODV discovery cost applies on cache miss.
            delay = hops * 2.0 + discovery_delay
            # Mobile IP tunnel is used for remote/home-agent delivery when node is
            # in a visited zone. Count one 20-byte outer header per delivered packet.
            if nodes[destination].current_network != nodes[destination].home_network:
                delay += 5.0
                metrics.tunnel_bytes += 20
            metrics.delivered += 1
            metrics.delay_total_ms += delay

    return metrics

def run_experiments(output_dir: Path, seeds: int = 5) -> List[dict]:
    rows = []
    for node_count in (8, 12, 16):
        for mobility in ("low", "medium", "high"):
            for protocol in ("DSDV", "AODV"):
                trials = [run_case(protocol, node_count, mobility, 1000+i)
                          for i in range(seeds)]
                sent = sum(t.sent for t in trials)
                delivered = sum(t.delivered for t in trials)
                row = {
                    "protocol": protocol,
                    "nodes": node_count,
                    "mobility": mobility,
                    "trials": seeds,
                    "packets_sent": sent,
                    "packets_delivered": delivered,
                    "packet_delivery_ratio_percent": round(100*delivered/sent if sent else 0, 2),
                    "average_delay_ms": round(
                        sum(t.delay_total_ms for t in trials)/delivered if delivered else 0, 2),
                    "routing_control_messages": sum(t.routing_control_messages for t in trials),
                    "handoffs": sum(t.handoffs for t in trials),
                    "mobile_ip_registrations": sum(t.mobile_ip_registrations for t in trials),
                    "tunnel_bytes": sum(t.tunnel_bytes for t in trials),
                }
                rows.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "experiment_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
    return rows

def run_demo() -> None:
    print("MOBILE COMPUTING ASSIGNMENT 3 - DEMO")
    for protocol in ("DSDV", "AODV"):
        m = run_case(protocol, 12, "medium", 42)
        print(f"{protocol}: sent={m.sent}, delivered={m.delivered}, "
              f"PDR={m.pdr:.2f}%, avg_delay={m.avg_delay_ms:.2f} ms, "
              f"control_messages={m.routing_control_messages}, "
              f"handoffs={m.handoffs}, registrations={m.mobile_ip_registrations}, "
              f"tunnel_bytes={m.tunnel_bytes}")

def main():
    parser = argparse.ArgumentParser(description="Mobile Computing Assignment 3 simulator")
    parser.add_argument("--mode", choices=("demo", "experiment"), default="demo")
    parser.add_argument("--output", default="results")
    parser.add_argument("--seeds", type=int, default=5)
    args = parser.parse_args()
    out = Path(args.output)
    if args.mode == "demo":
        run_demo()
    else:
        rows = run_experiments(out, args.seeds)
        print(f"Saved {len(rows)} experiment rows to {out / 'experiment_results.csv'}")
        print("protocol nodes mobility PDR(%) delay(ms) control_msgs handoffs")
        for r in rows:
            print(r["protocol"], r["nodes"], r["mobility"],
                  r["packet_delivery_ratio_percent"], r["average_delay_ms"],
                  r["routing_control_messages"], r["handoffs"])

if __name__ == "__main__":
    main()
