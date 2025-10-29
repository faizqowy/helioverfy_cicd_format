import os
import re
import json
from pathlib import Path

SUPPORTED_LANGUAGES = ['.js', '.ts', '.java']

class RouteExtractor:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.routes = {}

    def extract(self):
        for path in self.root_dir.rglob("*"):
            if path.suffix not in SUPPORTED_LANGUAGES:
                continue
            if any(part in {'.git', 'build', 'node_modules', 'target'} for part in path.parts):
                continue

            with open(path, 'r', errors='ignore', encoding="utf-8") as file:
                try:
                    content = file.read()
                except:
                    continue

                if path.suffix in ['.js', '.ts']:
                    self._extract_express_routes(content, path)
                elif path.suffix == '.java':
                    self._extract_spring_routes(content, path)

        return {
            "type": "routes",
            "services": self.routes
        }

    def _extract_express_routes(self, content, path):
        service = self._infer_service_name(path)
        route_pattern = re.compile(r"\b(app|router)\.(get|post|put|delete|patch|all)\s*\(\s*['\"](.*?)['\"]")
        for match in route_pattern.findall(content):
            method = match[1].upper()
            route = match[2]
            self.routes.setdefault(service, {"routes": []})["routes"].append({
                "method": method,
                "path": route
            })

    def _extract_spring_routes(self, content, path):
        service = self._infer_service_name(path)
        base_path_match = re.search(r'@RequestMapping\("([^"]+)"\)', content)
        base_path = base_path_match.group(1) if base_path_match else ""

        route_pattern = re.compile(r'@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\("([^"]+)"\)')
        for match in route_pattern.findall(content):
            method = match[0].replace("Mapping", "").upper()
            sub_path = match[1]
            full_path = base_path + sub_path
            self.routes.setdefault(service, {"routes": []})["routes"].append({
                "method": method,
                "path": full_path
            })

    def _infer_service_name(self, path):
        for part in path.parts:
            if "service" in part.lower():
                return part
        return "unknown"

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract routes from source code")
    parser.add_argument("--input", required=True, help="Root directory of the project")
    parser.add_argument("--output", default="routes.json", help="Output JSON file")
    args = parser.parse_args()

    extractor = RouteExtractor(args.input)
    routes = extractor.extract()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(routes, out, indent=2)

    print(f"✅ Routes written to {args.output}")
