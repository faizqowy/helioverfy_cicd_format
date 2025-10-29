import os
import json
import argparse
import yaml
from pathlib import Path


class ArchitectureExtractor:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)

    def extract(self):
        raise NotImplementedError("Subclasses must implement the extract method.")


class DockerExtractor(ArchitectureExtractor):
    def extract(self):
        structure = {
            "type": "docker",
            "services": {}
        }

        print(f"🔍 Searching for Docker Compose YAML files under: {self.root_dir}")
        yaml_files = list(self.root_dir.rglob("*.yml")) + list(self.root_dir.rglob("*.yaml"))
        yaml_files = [f for f in yaml_files if f.is_file()]
        print(f"📄 Found {len(yaml_files)} YAML files to check.")

        for yml_file in yaml_files:
            try:
                with open(yml_file, 'r') as file:
                    docs = list(yaml.safe_load_all(file))
            except Exception as e:
                print(f"⚠️  Skipped {yml_file}: {e}")
                continue

            for doc in docs:
                if not isinstance(doc, dict):
                    continue
                if "services" not in doc:
                    continue  # Not a Docker Compose file

                print(f"✅ Found Docker Compose services in: {yml_file}")
                services = doc.get('services', {})
                for name, config in services.items():
                    structure["services"].setdefault(name, {
                        "image": None,
                        "depends_on": [],
                        "exposes": [],
                        "environment": [],
                        "cmd": None
                    })
                    structure["services"][name].update({
                        "image": config.get("image"),
                        "depends_on": config.get("depends_on", []),
                        "exposes": config.get("ports", []),
                        "environment": config.get("environment", []),
                        "cmd": config.get("command")
                    })

        if not structure["services"]:
            print("⚠️  No Docker Compose services found.")
        return structure



class KubernetesExtractor(ArchitectureExtractor):
    def extract(self):
        structure = {
            "type": "kubernetes",
            "services": {}
        }

        for path in self.root_dir.rglob("*.yaml"):
            with open(path, 'r') as file:
                try:
                    docs = list(yaml.safe_load_all(file))
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")
                    continue

                for doc in docs:
                    if not isinstance(doc, dict):
                        continue
                    kind = doc.get("kind")
                    metadata = doc.get("metadata", {})
                    spec = doc.get("spec", {})
                    name = metadata.get("name")

                    if kind == "Deployment" and name:
                        containers = spec.get("template", {}).get("spec", {}).get("containers", [])
                        ports = []
                        env = []
                        for c in containers:
                            ports.extend([p.get("containerPort") for p in c.get("ports", []) if p])
                            env.extend([e.get("name") + '=' + e.get("value", "") for e in c.get("env", []) if e])
                        structure["services"][name] = {
                            "replicas": spec.get("replicas", 1),
                            "ports": ports,
                            "calls": [],
                            "config": env
                        }

                    elif kind == "Service" and name:
                        ports = [p.get("port") for p in spec.get("ports", []) if p]
                        structure["services"].setdefault(name, {})
                        structure["services"][name]["ports"] = ports

        return structure


class ServerlessExtractor(ArchitectureExtractor):
    def extract(self):
        structure = {
            "type": "serverless",
            "functions": {}
        }

        serverless_file = None
        for fname in ['serverless.yml', 'template.yaml']:
            path = self.root_dir / fname
            if path.exists():
                serverless_file = path
                break

        if not serverless_file:
            print("No serverless file found.")
            return structure

        with open(serverless_file, 'r') as file:
            try:
                config = yaml.safe_load(file)
            except Exception as e:
                print(f"Failed to parse {serverless_file}: {e}")
                return structure

        functions = config.get("functions", {})
        for name, fdef in functions.items():
            structure["functions"][name] = {
                "handler": fdef.get("handler"),
                "events": fdef.get("events", []),
                "environment": fdef.get("environment", {})
            }

        return structure


class EventDrivenExtractor(ArchitectureExtractor):
    def extract(self):
        structure = {
            "type": "event-driven",
            "services": {}
        }

        event_file = self.root_dir / "events.yml"
        if not event_file.exists():
            print("events.yml not found.")
            return structure

        with open(event_file, 'r') as file:
            try:
                config = yaml.safe_load(file)
            except Exception as e:
                print(f"Failed to parse {event_file}: {e}")
                return structure

        services = config.get("services", {})
        for name, svc in services.items():
            structure["services"][name] = {
                "produces": svc.get("produces", []),
                "consumes": svc.get("consumes", [])
            }

        return structure


class ServiceMeshExtractor(ArchitectureExtractor):
    def extract(self):
        structure = {
            "type": "service-mesh",
            "services": {},
            "traffic_policies": {},
            "auth_policies": {},
            "gateways": {}
        }

        for path in self.root_dir.rglob("*.yaml"):
            with open(path, 'r') as file:
                try:
                    docs = list(yaml.safe_load_all(file))
                except Exception as e:
                    print(f"Failed to parse {path}: {e}")
                    continue

                for doc in docs:
                    if not isinstance(doc, dict):
                        continue
                    kind = doc.get("kind")
                    metadata = doc.get("metadata", {})
                    spec = doc.get("spec", {})
                    name = metadata.get("name")

                    if kind == "VirtualService" and name:
                        routes = []
                        http_routes = spec.get("http", [])
                        for http in http_routes:
                            for route in http.get("route", []):
                                dst = route.get("destination", {}).get("host")
                                if dst:
                                    routes.append(dst)
                        structure["services"][name] = {
                            "routes_to": routes
                        }

                    elif kind == "DestinationRule" and name:
                        host = spec.get("host")
                        traffic_policy = spec.get("trafficPolicy", {})
                        structure["traffic_policies"][name] = {
                            "host": host,
                            "traffic_policy": traffic_policy
                        }

                    elif kind == "PeerAuthentication" and name:
                        structure["auth_policies"][name] = spec

                    elif kind == "Gateway" and name:
                        structure["gateways"][name] = spec

        return structure


EXTRACTOR_CLASSES = {
    "docker": DockerExtractor,
    "kubernetes": KubernetesExtractor,
    "serverless": ServerlessExtractor,
    "event-driven": EventDrivenExtractor,
    "service-mesh": ServiceMeshExtractor
}


def main():
    parser = argparse.ArgumentParser(description="Extract microservice architecture structure.")
    parser.add_argument("--type", choices=EXTRACTOR_CLASSES.keys(), required=True, help="Type of microservice architecture")
    parser.add_argument("--input", required=True, help="Root directory of the project")
    parser.add_argument("--output", default="architecture.json", help="Output file for structure")

    args = parser.parse_args()

    extractor_class = EXTRACTOR_CLASSES[args.type]
    extractor = extractor_class(args.input)
    structure = extractor.extract()

    folder_name = os.path.basename(args.input)
    output_dir = args.output + "/" + f"{folder_name}"

    os.makedirs(output_dir, exist_ok=True)
    args.output = os.path.join(output_dir, "architecture.json")

    with open(args.output, 'w') as out:
        json.dump(structure, out, indent=2)
    print(f"Architecture structure written to {args.output}")


if __name__ == "__main__":
    main()
