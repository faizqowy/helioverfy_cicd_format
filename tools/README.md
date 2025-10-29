# Microservices Formal Verification Tool

A comprehensive formal verification tool for microservices architectures using Z3 SMT solver. This tool validates that your microservices implementation complies with architectural specifications and behavioral contracts.

## Features

🔍 **Multi-Format Input Support**
- Docker Compose files for service topology
- OpenAPI specifications for API contracts
- Express.js routes files (extensible to other frameworks)

🔬 **Formal Verification**
- Z3 SMT solver-based constraint checking
- Temporal logic property verification
- Sequence and ordering constraints
- Communication pattern validation

🛡️ **Advanced Analysis**
- Security vulnerability detection
- Performance bottleneck analysis
- Circular dependency detection
- Policy compliance checking

📊 **Flexible Output**
- JSON and text output formats
- Detailed error reporting
- Model generation for satisfiable cases
- Integration-ready results

## Installation

```bash
pip install z3-solver pyyaml
```

## Quick Start

```bash
python cli.py \\
  --docker-compose ./docker-compose.yml \\
  --openapi ./api-spec.yml \\
  --routes ./routes.js \\
  --output-dir ./verification-results \\
  --verbose
```

## Usage

### Basic Verification
```bash
python cli.py --docker-compose compose.yml --openapi api.yml --routes routes.js
```

### Generate Files Only
```bash
python cli.py --docker-compose compose.yml --openapi api.yml --routes routes.js --generate-only
```

### Use Existing Specs File
```bash
python cli.py --specs-file existing.specs --routes routes.js
```

### JSON Output
```bash
python cli.py --docker-compose compose.yml --openapi api.yml --routes routes.js --format json
```

## Specification Format (.specs)

The tool generates or accepts `.specs` files with the following sections:

### Services and Routes
```
services:
    OrderService {
        routes:
            createOrder = POST /order;
            getOrder = GET /order/:id;
    }
```

### Sequence Constraints
```
seq:
    createOrder -> payOrder -> (sendNotif | claimBonus);
```

### Behavioral Constraints
```
constraints:
    require createOrder before payOrder;
    forbid payOrder before createOrder;
```

### Communication Patterns
```
comm:
    OrderService -> PaymentService : sync;
    PaymentService -> NotificationService : async;
```

### Policies
```
policies:
    authRequired: [payOrder, refundOrder];
    rateLimit: [sendNotif: 100/minute];
    timeout: [PaymentService: 5s];
```

### Temporal Properties
```
properties:
    always (createOrder -> payOrder);
    eventually (createOrder -> sendNotif);
```

## Example Files

Run `python test_example.py` to generate example files:
- `example_docker-compose.yml`
- `example_openapi.yml`  
- `example_routes.js`

## Architecture

### Components

1. **MainParser**: Converts Docker Compose + OpenAPI → .specs file
2. **ExpressRouteParser**: Parses Express.js routes → JSON format
3. **Z3MicroservicesSolver**: Performs formal verification using Z3
4. **CLI**: Command-line interface with comprehensive options

### Verification Process

1. Parse input files (Docker Compose, OpenAPI, routes)
2. Generate or load .specs file
3. Convert routes to JSON representation
4. Create Z3 variables and constraints
5. Add temporal, security, and behavioral constraints
6. Solve and report results

## Advanced Features

### Security Analysis
- Missing authentication detection
- Parameter validation checking
- Injection vulnerability analysis

### Performance Analysis
- Synchronous call chain detection
- Timeout policy validation
- Bottleneck identification

### Dependency Analysis
- Circular dependency detection
- Service topology validation
- Communication pattern analysis

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Extending the Tool

### Adding New Route Parsers

```python
class CustomFrameworkParser:
    def parse_route_file(self, file_path: str) -> Dict[str, Any]:
        # Implement parsing logic for your framework
        pass
```

### Adding New Constraint Types

```python
def add_custom_constraints(self):
    # Implement custom Z3 constraints
    pass
```

## License

MIT License - see LICENSE file for details.

## Support

- 📧 Email: support@example.com
- 🐛 Issues: GitHub Issues
- 📖 Documentation: Wiki

---
    