from z3 import *
import json

def encode_communication_graph(filepath):
    with open(filepath) as f:
        data = json.load(f)

    # Get unique services
    services = set()
    for call in data["calls"]:
        services.add(call["from"])
        services.add(call["to"])

    # Declare symbolic services
    Service = DeclareSort('Service')
    service_map = {s: Const(s.replace("-", "_"), Service) for s in services}

    # Define symbolic function: CanCall(from, to, method, path) => Bool
    CanCall = Function('CanCall', Service, Service, StringSort(), StringSort(), BoolSort())

    solver = Solver()

    # Assert all communication paths from data as facts
    for call in data["calls"]:
        fr = call["from"]
        to = call["to"]
        method = call["method"]
        path = call["path"]
        solver.add(CanCall(service_map[fr], service_map[to], StringVal(method), StringVal(path)))

    # ✅ Example: Can user-service call order-service with POST /api/orders
    print("\n📌 Verifying known valid communication:")
    solver.push()
    solver.add(Not(CanCall(service_map['user-service'], service_map['order-service'], StringVal("POST"), StringVal("/api/orders"))))
    if solver.check() == unsat:
        print("✅ user-service → order-service is allowed (verified)")
    else:
        print("❌ Violation: user-service → order-service not allowed")
    solver.pop()

    # 🔁 Reachability between all services
    print("\n🔁 Reachability Matrix:")
    for fr in services:
        for to in services:
            if fr == to:
                continue
            solver.push()
            m = String('m')
            p = String('p')
            expr = Exists([m, p], CanCall(service_map[fr], service_map[to], m, p))
            solver.add(Not(expr))
            if solver.check() == unsat:
                print(f"✔️  {fr} ➜ {to}")
            else:
                print(f"🚫 {fr} ➜ {to} not reachable")
            solver.pop()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Encode communication graph into Z3 constraints.")
    parser.add_argument("--input", required=True, help="Path to communication.json")
    args = parser.parse_args()

    encode_communication_graph(args.input)
