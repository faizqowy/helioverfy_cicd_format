from z3 import *
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import argparse
from pathlib import Path
import re 

class MicroservicesAnalyzer:
    def __init__(self):
        self.security_analyzer = SecurityAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()

    def analyze_security_vulnerabilities(self, routes_data: Dict) -> List[str]:
        return self.security_analyzer.analyze(routes_data)

    def analyze_performance_bottlenecks(self, specs_data: Dict) -> List[str]:
        return self.performance_analyzer.analyze(specs_data)

    def analyze_circular_dependencies(self, specs_data: Dict) -> List[str]:
        return self.dependency_analyzer.find_cycles(specs_data)


class SecurityAnalyzer:
    def analyze(self, routes_data: Dict) -> List[str]:
        vulnerabilities = []

        for route in routes_data.get('routes', []):
            if route['method'] in ['POST', 'PUT', 'DELETE'] and not self._has_auth_middleware(route):
                vulnerabilities.append(f"Security Warning: Missing authentication on sensitive route {route['method']} {route['path']}")
            if (':' in route['path'] or '{' in route['path']) and not self._has_validation_middleware(route):
                vulnerabilities.append(f"Security Warning: Missing input validation on parameterized route {route['path']}")
        return vulnerabilities

    def _has_auth_middleware(self, route: Dict) -> bool:
        middleware = route.get('middleware', [])
        auth_keywords = ['auth', 'authenticate', 'verify', 'protect', 'jwt']
        return any(any(keyword in mw.lower() for keyword in auth_keywords) for mw in middleware)

    def _has_validation_middleware(self, route: Dict) -> bool:
        middleware = route.get('middleware', [])
        validation_keywords = ['validate', 'sanitize', 'check']
        return any(any(keyword in mw.lower() for keyword in validation_keywords) for mw in middleware)


class PerformanceAnalyzer:
    def analyze(self, specs_data: Dict) -> List[str]:
        bottlenecks = []
        sync_chains = self._find_synchronous_chains(specs_data)
        for chain in sync_chains:
            if len(chain) > 3:
                bottlenecks.append(f"Performance Warning: Long synchronous call chain detected: {' -> '.join(chain)}")
        
        timeout_policies = specs_data.get('policies', {}).get('timeout', [])
        if not timeout_policies:
            bottlenecks.append("Performance Warning: No global timeout policies defined, which could lead to hanging requests.")
        return bottlenecks

    def _find_synchronous_chains(self, specs_data: Dict) -> List[List[str]]:
        communications = specs_data.get('communications', [])
        adj_list = self.build_dependency_graph(specs_data)
        
        chains = []
        for node in adj_list:
            path = [node]
            stack = [(node, path)]
            while stack:
                curr, p = stack.pop()
                is_leaf = True
                for neighbor in adj_list.get(curr, []):
                    if neighbor not in p:
                        is_leaf = False
                        stack.append((neighbor, p + [neighbor]))
                if is_leaf and len(p) > 1:
                    chains.append(p)
        return chains

    def build_dependency_graph(self, specs_data: Dict) -> Dict[str, List[str]]:
        graph = {}
        for comm in specs_data.get('communications', []):
            if isinstance(comm, dict):
                source = comm.get("source")
                target = comm.get("target")
                comm_type = comm.get("type")
                if source and target and comm_type == 'sync':
                     graph.setdefault(source, []).append(target)
            elif '->' in comm and 'sync' in comm.lower():
                parts = comm.split('->')
                if len(parts) == 2:
                    source = parts[0].strip().split()[0]
                    target = parts[1].strip().split(':')[0].strip()
                    graph.setdefault(source, []).append(target)
        return graph


class DependencyAnalyzer:
    def find_cycles(self, specs_data: Dict) -> List[str]:
        graph = self._build_dependency_graph(specs_data)
        cycles = self._detect_cycles(graph)
        return [f"Architectural Error: Circular dependency detected: {' -> '.join(cycle + [cycle[0]])}" for cycle in cycles]

    def _build_dependency_graph(self, specs_data: Dict) -> Dict[str, List[str]]:
        graph = {}
        for comm in specs_data.get('communications', []):
            if isinstance(comm, dict):
                source = comm.get("source")
                target = comm.get("target")
                if source and target:
                    graph.setdefault(source, []).append(target)
            elif '->' in comm:
                parts = comm.split('->')
                if len(parts) == 2:
                    source = parts[0].strip().split()[0]
                    target = parts[1].strip().split(':')[0].strip()
                    graph.setdefault(source, []).append(target)
        return graph

    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        path, visited, cycles = [], set(), []

        def dfs(node):
            path.append(node)
            visited.add(node)
            for neighbour in graph.get(node, []):
                if neighbour in path:
                    cycles.append(path[path.index(neighbour):] + [neighbour])
                    continue
                if neighbour not in visited:
                    dfs(neighbour)
            path.pop()

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)
        
        unique_cycles = []
        seen = set()
        for cycle in cycles:
            sorted_cycle = tuple(sorted(cycle))
            if sorted_cycle not in seen:
                unique_cycles.append(cycle[:-1])
                seen.add(sorted_cycle)
        return unique_cycles

@dataclass
class VerificationResult:
    is_sat: bool
    model: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class Z3MicroservicesSolver:
    def __init__(self):
        self.solver = Solver()
        self.route_vars = {}
        self.service_vars = {}
        self.specs_data = {}
        self.routes_data = {}
        self.analyzer = MicroservicesAnalyzer()

    def parse_specs_file(self, specs_path: str) -> Dict[str, Any]:
        with open(specs_path, 'r') as f:
            specs_data = json.load(f)

        internal_specs = {
            'services': {},
            'communications': specs_data.get('communications', []),
            'policies': specs_data.get('policies', {}),
            'properties': specs_data.get('properties', [])
        }

        for service_name, service_data in specs_data.get('services', {}).items():
            internal_specs['services'][service_name] = {'routes': {}}
            for route_name, route_details in service_data.get('routes', {}).items():
                method = route_details.get('method')
                path = route_details.get('path')
                if method and path:
                    internal_specs['services'][service_name]['routes'][route_name] = f"{method} {path}"
        return internal_specs

    def _create_z3_variables(self):
        for service_name, service_data in self.specs_data.get('services', {}).items():
            self.service_vars[service_name] = Bool(f"service_{service_name}")
            for route_name in service_data['routes']:
                self.route_vars[f"{service_name}_{route_name}"] = Bool(f"{service_name}_{route_name}")

    def _normalize_path(self, path: str) -> str:
        path = re.sub(r':(\w+)', r'{\1}', path)
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]
        return path

    def _check_spec_implementation_consistency(self) -> List[str]:
        suggestions = []
        defined_routes = self.routes_data.get('routes', [])
        
        for service_name, service_data in self.specs_data.get('services', {}).items():
            for route_name, route_spec in service_data['routes'].items():
                parts = route_spec.split()
                if len(parts) >= 2:
                    method, path = parts[0], parts[1]
                    
                    normalized_spec_path = self._normalize_path(path)
                    route_found = any(r['method'] == method and self._normalize_path(r['path']) == normalized_spec_path for r in defined_routes)
                    
                    if not route_found:
                        suggestion_msg = (
                            f"Missing Implementation: Route '{route_name}' ({method} {path}) "
                            f"is defined in the spec for service '{service_name}' but is not found in routes.json. "
                            "Consider implementing it."
                        )
                        suggestions.append(suggestion_msg)
        return suggestions

    def _add_policy_constraints(self):
        defined_routes = self.routes_data.get('routes', [])
        
        for route_name_in_policy in self.specs_data.get('policies', {}).get('authRequired', []):
            found_spec = False
            for service_name, service_data in self.specs_data.get('services', {}).items():
                for route_name_in_spec, route_spec_str in service_data['routes'].items():
                    if route_name_in_spec == route_name_in_policy:
                        found_spec = True
                        method, path = route_spec_str.split()[:2]
                        
                        normalized_spec_path = self._normalize_path(path)
                        route_impl = next((r for r in defined_routes if r['method'] == method and self._normalize_path(r['path']) == normalized_spec_path), None)
                        
                        z3_var_name = f"{service_name}_{route_name_in_spec}"
                        z3_var = self.route_vars.get(z3_var_name)
                        
                        if z3_var is None: continue

                        if route_impl:
                            has_auth = self.analyzer.security_analyzer._has_auth_middleware(route_impl)
                            if not has_auth:
                                self.solver.assert_and_track(
                                    BoolVal(False), f"policy_violation:auth_missing_on_{z3_var_name}"
                                )
                        else:
                            self.solver.assert_and_track(
                                BoolVal(False), f"policy_violation:required_route_missing_{z3_var_name}"
                            )
                        break
                if found_spec: break

    def _z3_model_to_dict(self, z3_model) -> Dict[str, Any]:
        result_dict = {}
        for d in z3_model.decls():
            val = z3_model[d]
            if is_bool(val):
                result_dict[d.name()] = is_true(val)
            elif is_int_value(val):
                result_dict[d.name()] = val.as_long()
            else:
                result_dict[d.name()] = str(val)
        return result_dict

    def _interpret_unsat_core(self) -> List[str]:
        errors = []
        try:
            unsat_core = self.solver.unsat_core()
        except Z3Exception:
            return ["Could not determine the unsatisfiable core. The constraints may have a fundamental conflict."]

        for core_item in unsat_core:
            core_str = str(core_item)
            if "policy_violation:auth_missing_on_" in core_str:
                route_name = core_str.replace("policy_violation:auth_missing_on_", "")
                errors.append(f"Policy Violation: Authentication is required for route '{route_name}' but is not implemented in its middleware.")
            elif "policy_violation:required_route_missing_" in core_str:
                route_name = core_str.replace("policy_violation:required_route_missing_", "")
                errors.append(f"Policy Violation: The route '{route_name}', which requires authentication, is not implemented.")
            else:
                errors.append(f"Unsatisfiable Constraint: {core_str}")
        return errors

    def verify(self, specs_path: str, routes_json_path: str) -> VerificationResult:
        try:
            self.specs_data = self.parse_specs_file(specs_path)
            with open(routes_json_path, 'r') as f:
                self.routes_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return VerificationResult(is_sat=False, errors=[f"Failed to load input files: {e}"])

        all_routes = []
        for service_info in self.routes_data.get('services', {}).values():
            all_routes.extend(service_info.get('routes', []))
        self.routes_data['routes'] = all_routes

        circular_deps = self.analyzer.analyze_circular_dependencies(self.specs_data)
        if circular_deps:
            return VerificationResult(is_sat=False, errors=circular_deps)

        self._create_z3_variables()
        self._add_policy_constraints()

        result = self.solver.check()
        is_sat_result = (result == sat)
        
        verification_result = VerificationResult(is_sat=is_sat_result)

        if is_sat_result:
            verification_result.model = self._z3_model_to_dict(self.solver.model())
        else:
            verification_result.errors.extend(self._interpret_unsat_core())
        
        verification_result.suggestions.extend(self._check_spec_implementation_consistency())
        verification_result.warnings.extend(self.analyzer.analyze_security_vulnerabilities(self.routes_data))
        verification_result.warnings.extend(self.analyzer.analyze_performance_bottlenecks(self.specs_data))

        return verification_result

def main():
    parser = argparse.ArgumentParser(
        description="HelioVerify: Verify microservice choreographies using Z3 and static analysis.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--specs", required=True, help="Path to the .specs architecture definition file (JSON format).")
    parser.add_argument("--routes", required=True, help="Path to the parsed routes implementation JSON file.")
    parser.add_argument("--output", default="verification_result.json", help="Path for the output JSON result file.")
    args = parser.parse_args()

    solver = Z3MicroservicesSolver()
    result = solver.verify(args.specs, args.routes)

    result_dict = {
        "is_satisfiable": result.is_sat,
        "errors": result.errors,
        "warnings": result.warnings,
        "suggestions": result.suggestions,
        "model": result.model if result.model else {}
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=4)

    print("\n" + "="*50)
    print("      HelioVerify Verification Report")
    print("="*50)

    if not result.errors and not result.warnings and not result.suggestions:
        print("\n✓ SUCCESS: The implementation perfectly matches the specification!")
    
    if result.is_sat:
        print(f"\n[STATUS] SATISFIABLE (✓)")
        print("  The implemented architecture is consistent with the formal policies.")
    else:
        print("\n[STATUS] UNSATISFIABLE (X)")
        print("  The implemented architecture VIOLATES the formal policies or is architecturally unsound.")

    if result.errors:
        print("\n--- ERRORS (Must Fix) ---")
        for error in result.errors:
            print(f"  - {error}")

    if result.suggestions:
        print("\n--- SUGGESTIONS (To match spec) ---")
        for suggestion in result.suggestions:
            print(f"  - {suggestion}")

    if result.warnings:
        print("\n--- WARNINGS (Best Practices) ---")
        for warning in result.warnings:
            print(f"  - {warning}")

    print(f"\n Full JSON report saved to {args.output}\n")


if __name__ == "__main__":
    main()

