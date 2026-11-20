# FR-008 Verify the running version

ECS "steady state" is not proof. A rolled-back deploy also reports stable.

After every deploy the pipeline asserts:

1. `GET /version` returns `image_digest` equal to the digest the pipeline deployed. The calc engine reads it from the ECS task metadata endpoint, so it reports what was actually pulled.
2. The ECS service's running task definition is the revision Harness registered for this execution.

Either check failing fails the stage and triggers rollback.
