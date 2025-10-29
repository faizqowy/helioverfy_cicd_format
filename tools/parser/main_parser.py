# main_parser.py - Parses docker-compose and multiple OpenAPI specs to generate a structured JSON file.
import yaml
import json
import re
from typing import Dict, List, Any
from pathlib import Path
import argparse

class MainParser:
    """
    Parses docker-compose.yml and multiple OpenAPI/Swagger files to generate a single,
    structured JSON file representing the microservices system specification.
    """

    def parse_docker_compose(self, compose_path: str) -> Dict[str, Any]:
        """Parse docker-compose.yml to extract service names and configurations."""
        with open(compose_path, 'r', encoding="utf-8") as file:
            compose_data = yaml.safe_load(file)
        
        services = {}
        if 'services' in compose_data:
            for service_name, service_config in compose_data['services'].items():
                services[service_name] = {
                    'ports': service_config.get('ports', []),
                    'environment': service_config.get('environment', {}),
                    'depends_on': service_config.get('depends_on', [])
                }
        return services

    def parse_openapi(self, openapi_path: str) -> Dict[str, Any]:
        """Parse OpenAPI specification to extract routes and operations."""
        with open(openapi_path, 'r', encoding="utf-8") as file:
            if openapi_path.endswith(('.yaml', '.yml')):
                openapi_data = yaml.safe_load(file)
            else:
                openapi_data = json.load(file)

        routes = {}
        base_service_name = Path(openapi_path).stem  # e.g., "auth", "event"
        paths = openapi_data.get('paths', {})

        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                    operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_').lstrip('_')}")
                    tags = operation.get('tags', [base_service_name])
                    routes[operation_id] = {
                        'method': method.upper(),
                        'path': path,
                        'summary': operation.get('summary', ''),
                        'tags': tags
                    }
        return routes

    


    def parse_multiple_openapi(self, openapi_paths: List[str]) -> Dict[str, Any]:
        """Parse multiple OpenAPI files and merge their routes."""
        combined_routes = {}
        for path in openapi_paths:
            try:
                routes = self.parse_openapi(path)
                # Merge routes; newer definitions override duplicates
                combined_routes.update(routes)
                print(f"✅ Parsed {len(routes)} routes from {path}")
            except Exception as e:
                print(f"⚠️  Failed to parse {path}: {e}")
        return combined_routes

    def infer_service_from_tags(self, tags: List[str]) -> str:
        """Infer service name from OpenAPI tags."""
        if tags:
            tag = tags[0]
            return "".join(word.capitalize() for word in re.split(r'[\s_-]', tag)) + "Service"
        return "UnknownService"

    def generate_communications(self, docker_services: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate communication patterns from service dependencies."""
        communications = []
        for service_name, config in docker_services.items():
            for dep in config.get('depends_on', []):
                communications.append({
                    "source": dep,
                    "target": service_name,
                    "type": "sync"
                })
        return communications

    def generate_policies(self, openapi_routes: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate policies based on OpenAPI security definitions or methods."""
        policies = {'authRequired': []}
        for route_name, route_info in openapi_routes.items():
            if route_info['method'] in ['POST', 'PUT', 'DELETE', 'PATCH']:
                policies['authRequired'].append(route_name)
        return policies
    
    def generate_properties(self, communications: List[Dict[str, str]]) -> List[str]:
        """Generate temporal logic properties from communication patterns."""
        properties = []
        for comm in communications:
            properties.append(f"always ({comm['source']} -> eventually {comm['target']})")
        return properties

    def parse_to_json(self, compose_path: str, openapi_paths: List[str], output_path: str):
        """Main method to parse inputs and generate a final JSON output file."""
        # 1. Parse input files
        docker_services = self.parse_docker_compose(compose_path)
        openapi_routes = self.parse_multiple_openapi(openapi_paths)

        # 2. Group routes by service
        services_dict = {}
        for route_name, route_info in openapi_routes.items():
            service_name = self.infer_service_from_tags(route_info['tags'])
            if service_name not in services_dict:
                services_dict[service_name] = {"routes": {}}
            services_dict[service_name]["routes"][route_name] = {
                "method": route_info['method'],
                "path": route_info['path']
            }

        # 3. Generate other sections
        communications = self.generate_communications(docker_services)
        policies = self.generate_policies(openapi_routes)
        properties = self.generate_properties(communications)

        # 4. Assemble final structure
        final_spec_dict = {
            "services": services_dict,
            "communications": communications,
            "policies": policies,
            "properties": properties
        }
        
        # 5. Save JSON
        with open(output_path, 'w', encoding="utf-8") as f:
            json.dump(final_spec_dict, f, indent=4)
        
        print(f"\n✅ Specification successfully written to {output_path}")
        print(f"   Parsed {len(services_dict)} services and {len(openapi_routes)} total routes.")

def main():
    parser = argparse.ArgumentParser(description="Generate system specification from Docker Compose and multiple OpenAPI files.")
    parser.add_argument("--compose", required=True, help="Path to docker-compose.yml")
    parser.add_argument("--openapi", required=True, nargs='+', help="Paths to one or more OpenAPI specs (JSON or YAML)")
    parser.add_argument("--output", default="system_spec.json", help="Output JSON file path")
    
    args = parser.parse_args()
    
    main_parser = MainParser()
    main_parser.parse_to_json(args.compose, args.openapi, args.output)

if __name__ == '__main__':
    main()
