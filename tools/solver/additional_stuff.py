import argparse
import sys
import json
from pathlib import Path

class AdvancedFeatures:
    
    def __init__(self):
        self.security_analyzer = SecurityAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.dependency_analyzer = DependencyAnalyzer()
    
    def analyze_security_vulnerabilities(self, routes_data: Dict) -> List[str]:
        """Analyze potential security vulnerabilities"""
        return self.security_analyzer.analyze(routes_data)
    
    def analyze_performance_bottlenecks(self, specs_data: Dict) -> List[str]:
        """Analyze potential performance bottlenecks"""
        return self.performance_analyzer.analyze(specs_data)
    
    def analyze_circular_dependencies(self, specs_data: Dict) -> List[str]:
        """Analyze circular dependencies in service communications"""
        return self.dependency_analyzer.find_cycles(specs_data)

class SecurityAnalyzer:
    """Security vulnerability analyzer"""
    
    def analyze(self, routes_data: Dict) -> List[str]:
        vulnerabilities = []
        
        for route in routes_data.get('routes', []):
            # Check for missing auth on sensitive operations
            if route['method'] in ['POST', 'PUT', 'DELETE']:
                if not self.has_auth_middleware(route):
                    vulnerabilities.append(
                        f"Missing authentication on {route['method']} {route['path']}"
                    )
            
            # Check for potential injection vulnerabilities
            if ':' in route['path'] and not self.has_validation_middleware(route):
                vulnerabilities.append(
                    f"Missing validation on parameterized route {route['path']}"
                )
        
        return vulnerabilities
    
    def has_auth_middleware(self, route: Dict) -> bool:
        middleware = route.get('middleware', [])
        auth_keywords = ['auth', 'authenticate', 'verify', 'protect', 'jwt']
        return any(any(keyword in mw.lower() for keyword in auth_keywords) 
                  for mw in middleware)
    
    def has_validation_middleware(self, route: Dict) -> bool:
        middleware = route.get('middleware', [])
        validation_keywords = ['validate', 'sanitize', 'check']
        return any(any(keyword in mw.lower() for keyword in validation_keywords) 
                  for mw in middleware)

class PerformanceAnalyzer:
    """Performance bottleneck analyzer"""
    
    def analyze(self, specs_data: Dict) -> List[str]:
        bottlenecks = []
        
        # Analyze communication patterns
        sync_chains = self.find_synchronous_chains(specs_data)
        for chain in sync_chains:
            if len(chain) > 3:
                bottlenecks.append(
                    f"Long synchronous call chain detected: {' -> '.join(chain)}"
                )
        
        # Analyze timeout configurations
        policies = specs_data.get('policies', {})
        timeout_policies = policies.get('timeout', [])
        
        if not timeout_policies:
            bottlenecks.append("No timeout policies defined - potential for hanging requests")
        
        return bottlenecks
    
    def find_synchronous_chains(self, specs_data: Dict) -> List[List[str]]:
        communications = specs_data.get('communications', [])
        sync_communications = [
            comm for comm in communications if 'sync' in comm.lower()
        ]
        
        # Build chains (simplified implementation)
        chains = []
        for comm in sync_communications:
            if '->' in comm:
                parts = comm.split('->')
                if len(parts) == 2:
                    source = parts[0].strip().split()[0]  # Extract service name
                    target = parts[1].strip().split(':')[0].strip()  # Extract service name
                    chains.append([source, target])
        
        return chains

class DependencyAnalyzer:
    """Circular dependency analyzer"""
    
    def find_cycles(self, specs_data: Dict) -> List[str]:
        """Find circular dependencies in service communications"""
        graph = self.build_dependency_graph(specs_data)
        cycles = self.detect_cycles(graph)
        
        cycle_descriptions = []
        for cycle in cycles:
            cycle_descriptions.append(f"Circular dependency: {' -> '.join(cycle + [cycle[0]])}")
        
        return cycle_descriptions
    
    def build_dependency_graph(self, specs_data: Dict) -> Dict[str, List[str]]:
        graph = {}
        communications = specs_data.get('communications', [])
        
        for comm in communications:
            if '->' in comm:
                parts = comm.split('->')
                if len(parts) == 2:
                    source = parts[0].strip().split()[0]
                    target = parts[1].strip().split(':')[0].strip()
                    
                    if source not in graph:
                        graph[source] = []
                    graph[source].append(target)
        
        return graph
    
    def detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect cycles using DFS"""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles