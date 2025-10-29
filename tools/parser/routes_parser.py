import ast
import re
import json
from typing import Dict, List, Any, Tuple, Optional
import argparse
from pathlib import Path

def _const_value(node: ast.AST) -> Optional[Any]:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return None

def _iter_sequence_values(node: ast.AST) -> List[Any]:
    vals = []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            v = _const_value(elt)
            if v is not None:
                vals.append(v)
    return vals

def _normalize_path(path: str) -> str:
    if path is None:
        return ""
    return str(path).strip()

def _generate_route_name(method: str, path: str) -> str:
    clean_path = re.sub(r'[\W_]+', '_', path).strip('_')
    return f"{method.lower()}_{clean_path or 'root'}"


class FastAPIParser:
    class RouteVisitor(ast.NodeVisitor):
        def __init__(self):
            self.routes: List[Dict] = []
            self.port: Optional[int] = None
            self.app_instance_names = set(['app', 'router', 'api'])

        def visit_Assign(self, node: ast.Assign):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                fname = node.value.func.id.lower()
                if fname in ('fastapi', 'fastapiclient', 'fastapirouter', 'apirouter', 'fastapiapp', 'fastapiapplication'):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.app_instance_names.add(t.id)
                if fname == 'fastapi' or getattr(node.value.func, 'id', '').lower() == 'fastapi':
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.app_instance_names.add(t.id)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._process_decorators(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self._process_decorators(node)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == 'uvicorn' and func.attr == 'run':
                for kw in node.keywords:
                    if kw.arg == 'port':
                        v = _const_value(kw.value)
                        if isinstance(v, int):
                            self.port = v
            self.generic_visit(node)

        def _process_decorators(self, node: ast.FunctionDef):
            http_methods = {'get', 'post', 'put', 'delete', 'patch', 'options', 'head'}
            middlewares: List[str] = []
            found_routes: List[Dict] = []

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    func = decorator.func
                    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                        objname = func.value.id
                        attr = func.attr.lower()
                        if objname in self.app_instance_names and attr in http_methods:
                            method = attr.upper()
                            path = ""
                            if decorator.args:
                                v = _const_value(decorator.args[0])
                                if v is not None:
                                    path = _normalize_path(v)
                            found_routes.append({"method": method, "path": path})
                        else:
                            if isinstance(func, ast.Attribute) and isinstance(func.attr, str):
                                middlewares.append(func.attr)
                    elif isinstance(func, ast.Name):
                        middlewares.append(func.id)
                else:
                    if isinstance(decorator, ast.Attribute):
                        middlewares.append(decorator.attr)
                    elif isinstance(decorator, ast.Name):
                        middlewares.append(decorator.id)

            for r in found_routes:
                self.routes.append({
                    "name": _generate_route_name(r["method"], r["path"]),
                    "method": r["method"],
                    "path": r["path"],
                    "middleware": middlewares.copy(),
                    "handler": node.name
                })

    def parse(self, file_path: str) -> Tuple[List[Dict], Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            visitor = self.RouteVisitor()
            visitor.visit(tree)
            return visitor.routes, visitor.port
        except Exception as e:
            print(f"Error parsing FastAPI file {file_path}: {e}")
            return [], None

class FlaskParser:
    class RouteVisitor(ast.NodeVisitor):
        def __init__(self):
            self.routes: List[Dict] = []
            self.port: Optional[int] = None
            self.app_like_names = set(['app'])
            self.blueprints = set()

        def visit_Assign(self, node: ast.Assign):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Name) and func.id == "Blueprint":
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.blueprints.add(t.id)
                            self.app_like_names.add(t.id)
                if isinstance(func, ast.Name) and func.id == "Flask":
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            self.app_like_names.add(t.id)
            self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self._process_decorators(node)
            self.generic_visit(node)

        def _process_decorators(self, node: ast.FunctionDef):
            route_calls: List[Dict] = []
            middlewares: List[str] = []

            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    func = decorator.func
                    if isinstance(func.value, ast.Name) and func.value.id in self.app_like_names and func.attr == 'route':
                        path = ""
                        methods = ["GET"]
                        if decorator.args:
                            val = _const_value(decorator.args[0])
                            if val is not None:
                                path = _normalize_path(val)
                        for kw in decorator.keywords:
                            if kw.arg == 'methods':
                                methods = _iter_sequence_values(kw.value)
                                methods = [str(m).upper() for m in methods if isinstance(m, (str, int))]
                        route_calls.append({"path": path, "methods": methods})
                    else:
                        if isinstance(decorator.func, ast.Attribute):
                            middlewares.append(decorator.func.attr)
                        elif isinstance(decorator.func, ast.Name):
                            middlewares.append(decorator.func.id)
                else:
                    if isinstance(decorator, ast.Name):
                        middlewares.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        middlewares.append(decorator.attr)

            for rc in route_calls:
                for method in rc["methods"]:
                    self.routes.append({
                        "name": _generate_route_name(method, rc["path"]),
                        "method": method,
                        "path": rc["path"],
                        "middleware": middlewares.copy(),
                        "handler": node.name
                    })

        def visit_Call(self, node: ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in self.app_like_names and func.attr == 'run':
                for kw in node.keywords:
                    if kw.arg == 'port':
                        v = _const_value(kw.value)
                        if isinstance(v, int):
                            self.port = v
            self.generic_visit(node)

    def parse(self, file_path: str) -> Tuple[List[Dict], Any]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
            visitor = self.RouteVisitor()
            visitor.visit(tree)
            return visitor.routes, visitor.port
        except Exception as e:
            print(f"Error parsing Flask file {file_path}: {e}")
            return [], None

class ExpressParser:
    def __init__(self):
        self.route_patterns = [
            r'(?:(?:const|let|var)\s+\w+\s*=\s*)?(app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*([\'"`][^\'"`]*[\'"`])\s*,\s*([\s\S]*?)\)\s*;'
        ]
        self.listen_patterns = [
            r'\.listen\s*\(\s*(\d+)\s*,',
            r'\.listen\s*\(\s*(\d+)\s*\)' 
        ]

    @staticmethod
    def _strip_comments(s: str) -> str:
        s = re.sub(r'//.*', '', s)
        s = re.sub(r'/\*[\s\S]*?\*/', '', s)
        return s

    def _extract_middleware_and_handler(self, handler_part: str) -> Tuple[List[str], str]:
        handler_part = handler_part.strip()
        handler_idx = None
        m = re.search(r'((?:async\s+)?function\s*\(|\([^\)]*\)\s*=>|\w+\s*=>)', handler_part)
        if m:
            handler_idx = m.start()
        if handler_idx is None:
            parts = [p.strip() for p in handler_part.split(',') if p.strip()]
            if not parts:
                return [], ""
            return parts[:-1], parts[-1]
        middleware_str = handler_part[:handler_idx]
        handler_str = handler_part[handler_idx:].strip()
        middleware = [x.strip() for x in middleware_str.split(',') if x.strip()]
        return middleware, handler_str

    def parse(self, file_path: str) -> Tuple[List[Dict], Any]:
        routes: List[Dict] = []
        port: Optional[int] = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            clean = self._strip_comments(content)

            for pat in self.route_patterns:
                for m in re.finditer(pat, clean, flags=re.IGNORECASE):
                    app_or_router = m.group(1)
                    method = m.group(2).upper()
                    raw_path = m.group(3).strip('\'"`')
                    handler_part = m.group(4)
                    middleware, handler = self._extract_middleware_and_handler(handler_part)
                    routes.append({
                        "name": _generate_route_name(method, raw_path),
                        "method": method,
                        "path": raw_path,
                        "middleware": middleware,
                        "handler": handler.replace('\n', ' ').strip()
                    })

            for lp in self.listen_patterns:
                pm = re.search(lp, clean)
                if pm:
                    try:
                        port = int(pm.group(1))
                        break
                    except Exception:
                        port = pm.group(1)
                        break

            return routes, port
        except Exception as e:
            print(f"Error parsing Express file {file_path}: {e}")
            return [], None

class GoParser:
    def __init__(self):
        self.patterns = [
            (r'http\.HandleFunc\s*\(\s*"([^"]*)"\s*,\s*([A-Za-z0-9_\.]+)\s*\)', 'ANY'),
            (r'([A-Za-z0-9_]+)\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|HEAD)\s*\(\s*"([^"]*)"\s*,\s*([A-Za-z0-9_\.]+)\s*\)', None),
            (r'([A-Za-z0-9_]+)\.(Get|Post|Put|Delete|Patch|Options|Head)\s*\(\s*"([^"]*)"\s*,\s*([A-Za-z0-9_\.]+)\s*\)', None),
        ]
        self.listen_pattern = r'ListenAndServe\s*\(\s*[:"]?(\d+)'

    def parse(self, file_path: str) -> Tuple[List[Dict], Any]:
        routes: List[Dict] = []
        port: Optional[int] = None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for pat, default_method in self.patterns:
                for m in re.finditer(pat, content):
                    groups = m.groups()
                    if default_method == 'ANY' and len(groups) >= 2:
                        path, handler = groups[0], groups[1]
                        method = 'ANY'
                    elif len(groups) >= 4:
                        obj, meth, path, handler = groups[0], groups[1], groups[2], groups[3]
                        method = meth.upper()
                    else:
                        continue
                    routes.append({
                        "name": _generate_route_name(method, path),
                        "method": method,
                        "path": path,
                        "middleware": [],
                        "handler": handler
                    })

            lm = re.search(self.listen_pattern, content)
            if lm:
                try:
                    port = int(lm.group(1))
                except Exception:
                    port = lm.group(1)

            return routes, port
        except Exception as e:
            print(f"Error parsing Go file {file_path}: {e}")
            return [], None

class RouteParser:
    def __init__(self):
        self.express_parser = ExpressParser()
        self.fastapi_parser = FastAPIParser()
        self.flask_parser = FlaskParser()
        self.go_parser = GoParser()

    def _detect_python_framework(self, content: str, tree: ast.AST) -> str:
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.lower())
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").lower()
                imported.add(module)
                for alias in node.names:
                    imported.add(alias.name.lower())

        if any('fastapi' in name for name in imported) or re.search(r'\bFastAPI\b', content):
            return "FastAPI"
        if any('flask' in name for name in imported) or re.search(r'\bflask\b', content, re.IGNORECASE):
            return "Flask"
        if re.search(r'\bBlueprint\s*\(', content) or re.search(r'\bFlask\s*\(', content):
            return "Flask"
        return "Unknown"

    def parse_files(self, file_paths: List[str]) -> Dict[str, Any]:
        final_spec: Dict[str, Any] = {"services": {}}
        services_count = 0

        for file_path in file_paths:
            file = Path(file_path)
            routes: List[Dict] = []
            port: Optional[int] = None
            framework = "Unknown"

            try:
                if file.suffix == '.js':
                    routes, port = self.express_parser.parse(file_path)
                    framework = "Express.js"
                elif file.suffix == '.py':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    try:
                        tree = ast.parse(content)
                    except Exception:
                        tree = None
                    if tree is not None:
                        framework = self._detect_python_framework(content, tree)
                    else:
                        if re.search(r'\bflask\b', content, re.IGNORECASE):
                            framework = "Flask"
                        elif re.search(r'\bFastAPI\b', content):
                            framework = "FastAPI"
                        else:
                            framework = "Unknown"

                    if framework == "Flask":
                        routes, port = self.flask_parser.parse(file_path)
                    elif framework == "FastAPI":
                        routes, port = self.fastapi_parser.parse(file_path)
                    else:
                        f_routes, f_port = self.flask_parser.parse(file_path)
                        fa_routes, fa_port = self.fastapi_parser.parse(file_path)
                        if f_routes and not fa_routes:
                            routes, port, framework = f_routes, f_port, "Flask"
                        elif fa_routes and not f_routes:
                            routes, port, framework = fa_routes, fa_port, "FastAPI"
                        else:
                            routes = f_routes + fa_routes
                            port = f_port or fa_port
                            if routes:
                                framework = "Mixed"
                elif file.suffix in ('.go', '.golang'):
                    routes, port = self.go_parser.parse(file_path)
                    framework = "Go"
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'express' in content and '.get(' in content:
                        routes, port = self.express_parser.parse(file_path)
                        framework = "Express.js"

            except Exception as e:
                print(f"Error processing {file_path}: {e}")

            base_name = "".join(word.capitalize() for word in file.stem.split('-')) or "Routes"
            service_name = base_name + "Service"
            i = 1
            while service_name in final_spec["services"]:
                i += 1
                service_name = f"{base_name}Service{i}"

            seen = set()
            unique_routes: List[Dict] = []
            for r in routes:
                key = (r.get('method'), r.get('path'), r.get('handler'))
                if key not in seen:
                    unique_routes.append(r)
                    seen.add(key)

            final_spec["services"][service_name] = {
                'port': port,
                'file_path': str(file_path),
                'framework': framework,
                'routes': unique_routes
            }
            services_count += 1

        total_routes = sum(len(s['routes']) for s in final_spec["services"].values())
        final_spec["metadata"] = {
            "total_services": services_count,
            "total_routes": total_routes
        }
        return final_spec

def main():
    parser = argparse.ArgumentParser(description="Parse routes from multiple FastAPI, Flask, Express.js, or Go files.")
    parser.add_argument("--files", required=True, nargs='+', help="List of source files to parse.")
    parser.add_argument("--output", default="routes.json", help="Path to save JSON output.")
    args = parser.parse_args()

    universal_parser = RouteParser()
    parsed_data = universal_parser.parse_files(args.files)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(parsed_data, f, indent=4)

    print(f" Parsed {parsed_data['metadata']['total_routes']} routes from {parsed_data['metadata']['total_services']} service(s).")
    print(f"   Output saved to: {args.output}")


if __name__ == "__main__":
    main()
