# Agent Behavior

## Existing Patterns

- Use FastAPI routes, Pydantic schemas, service modules, and core utilities.
- Use `asyncpg` and explicit parameterized SQL (`$1`, `$2`, ...) for database access. Do not introduce an ORM.
- Send access tokens as Bearer credentials. Store opaque refresh tokens only as hashes.
- Normalize and validate request data in Pydantic schemas. Keep data serialization close to its schema/entity representation.

## Code Style

- Prefer direct, local code over abstractions created for hypothetical reuse.
- Do not add redundant code, thin wrappers, tiny helpers, or one-use functions that only forward arguments or return a simple value.
- Avoid coupling layers or modules to implementation details they do not own. Depend on the smallest stable contract available.
- Extract a function, class, or module only when it has a clear domain name, real reuse, isolates a side effect, or makes the current code substantially easier to understand or test.
- Keep cohesive code close together. Before creating another file, verify that separation represents a real boundary rather than moving a short, local flow away from its data and behavior.
- Preserve layer boundaries: routes handle HTTP concerns, schemas validate and serialize input/output data, services contain business rules and database orchestration, and `core` contains shared infrastructure and cross-cutting utilities.
- Choose precise domain names for modules, functions, variables, and models. Names must describe the value or behavior without relying on implementation details or vague terms such as `data`, `utils`, or `manager` when a specific name is available.
- Do not use defensive `isinstance` checks or fallback behavior without a concrete contract requirement.
- Use `async` only for code that awaits I/O. Services that access PostgreSQL must be async.
- Preserve explicit error handling and log unexpected failures at the boundary where they are handled.
- Add tests for every behavior change, with coverage proportional to its risk. Prioritize service rules, authentication, authorization, and HTTP error responses.
- Type public interfaces and service return values. Use a schema or model when it describes a response contract more clearly than a generic `dict`.
- Keep secrets in environment variables. Never commit real secrets or include them in logs or API responses.
- The application must reject development-only security defaults and JWT HMAC keys shorter than 32 characters outside the development environment.
- Select only the database columns needed by the use case. Always use parameterized queries and never use `SELECT *`.
- Use an `asyncpg` transaction when one operation performs multiple dependent database writes.
- Use Alembic for versioned PostgreSQL migrations. Alembic may use SQLAlchemy only as migration infrastructure; application queries must continue using `asyncpg` and explicit SQL.
- Keep authentication and authorization in FastAPI dependencies instead of repeating checks in route handlers.
- Version database schema changes through migrations. Do not modify migrations that may already have been applied.
- Do not add dependencies when the existing FastAPI, Pydantic, standard library, or `asyncpg` tools solve the requirement cleanly.

## Do Not

- Do not introduce ORMs, repositories genéricos, query builders, or database abstractions over `asyncpg` without an explicit requirement.
- Do not put SQL, business rules, authentication decisions, or response formatting in route handlers.
- Do not put HTTP request/response concerns in services, schemas, or database utilities.
- Do not add catch-all `try/except`, broad fallback values, silent error handling, or defensive type checks just to make code appear safer.
- Do not duplicate validation in routes, services, and schemas. Put input validation in the schema and add service validation only for business rules or database state.
- Do not create `utils`, `helpers`, `common`, or `manager` modules as catch-all locations for unrelated code.
- Do not split a small cohesive flow across multiple files, or create a file for a single trivial function.
- Do not expose tokens, passwords, database rows, internal metadata, stack traces, or `status_code` in JSON response bodies.
- Do not return raw service dictionaries from routes. Use `default_response` for service calls.
- Do not change a public response shape, cookie attributes, authentication behavior, or database schema without a concrete requirement and affected validation.
- Do not return internal exception details to clients. Log them and return a safe, consistent API error message.
- Do not alter an API contract, database migration, cookie, or authorization rule without reviewing affected consumers and tests.

## Service And Route Contract

- Services called by routes return `{"status": bool, "status_code": int, "message": str, "data": dict}`.
- `status_code` is an HTTP status code: use `200` for successful reads/updates, `201` for creation, `204` for successful empty responses, `400` for invalid requests, `401` for invalid authentication, `403` for forbidden actions, `404` for missing resources, and `500` for unexpected server failures.
- Route handlers must use `core.responses.default_response` for service calls. It accepts synchronous or asynchronous callables, awaits only when needed, serializes response data with `jsonable_encoder`, and returns a JSON response with `message` and `data`, except for `204`, which has no body.
- Keep transport-specific work in routes. When a successful service result must set a cookie or header, use `default_response`'s `on_success` callback and exclude secret fields from `data`.
- Access tokens are short-lived JWTs sent as Bearer credentials. Refresh tokens are opaque, returned only in the auth exchange and refresh JSON responses, and persisted only as hashes. Rotate refresh tokens in a transaction and revoke their whole family when a rotated token is reused.
- Do not expose internal fields such as access tokens or `status_code` in response bodies.
