# ilmp-calc-engine

Python calc engine for the ILMP Index Studio demo (Harness for S&P DJI). It runs on ECS Fargate behind the `ilmp-demo-alb` load balancer.

| Endpoint | Purpose |
|---|---|
| `GET /health` | ALB health check |
| `GET /version` | Build identity. `image_digest` comes from ECS task metadata (FR-008) |
| `POST /backtest` | Queue a backtest, returns `job_id` |
| `GET /backtest/{id}` | `QUEUED -> RUNNING -> COMPLETED` (or `FAILED`) after about 5 s (FR-009) |

```bash
pip install -r requirements-dev.txt
pytest --cov=app
docker build --build-arg IMAGE_TAG=dev -t calc-engine .
```

Delivery is in [ilmp-delivery](https://github.com/alexsoto-harness/ilmp-delivery): Harness builds once on merge to `release/*`, pushes one digest to HAR and ECR, and promotes it through Dev, QA, QADR, UAT and Prod.

- `deploy/ecs/`: task and service definitions, owned by Harness CD.
- `specs/`: functional requirements referenced by tests and the Eval stand-in.
- `dictionary.yaml`: data dictionary for schema-conformance checks.

Demo branches: `feature/analytics-endpoint` (happy path), `feature/vulnerable-dep` (critical CVE, blocked on the PR), `feature/eval-arch-fault` (writes outside the calc schema, Eval FAIL), `hotfix/bad-backtest` (backtests end FAILED, Prod rolls back).
