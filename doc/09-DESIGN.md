# AI IDE Development and Execution Instructions

## 1. Role

You are the implementation agent for Aarogya Sahayak. Read all specification files `01` through `09` before editing code. Treat them as the source of truth. If specifications conflict, prioritize safety and ask for a documented decision rather than silently inventing behavior.

Your goal is to build a runnable, tested MVP, not to generate disconnected mock screens.

## 2. Non-negotiable rules

1. Inspect the existing repository before editing.
2. Preserve existing user changes.
3. Do not replace the fixed stack without approval.
4. Do not create separate ASHA, Doctor, and Admin portal projects.
5. Do not put external API keys in frontend code.
6. Do not fabricate successful external integrations.
7. Do not implement autonomous diagnosis or prescription.
8. Do not weaken RBAC to make the demo work.
9. Do not place API calls inside presentational components.
10. Do not rewrite unrelated feature folders.
11. Keep TypeScript strict and Python typed.
12. Run validation after every meaningful milestone.

## 3. Required implementation stack

```text
Citizen: React Native + Expo + TypeScript
Portal: React + Vite + TypeScript
Backend: FastAPI + Pydantic + SQLAlchemy + Alembic
Database: PostgreSQL
Portal server state: TanStack Query
Forms: React Hook Form + Zod
Citizen offline: Expo SQLite
ASHA offline: IndexedDB/Dexie
Containers: Docker Compose
Tests: pytest, Vitest/RTL, Playwright
```

## 4. First action: repository assessment

Before modifying files, report:

- existing directories and frameworks;
- package managers and lock files;
- lint/type-check/test/build commands;
- existing authentication and routing;
- existing design tokens/components;
- database and migration state;
- current environment-variable references;
- dirty/uncommitted changes;
- exact files proposed for phase 1.

Do not code until this assessment is complete.

## 5. Execution plan

### Phase 1 - Scaffold and health checks

- Create missing monorepo directories without deleting existing work.
- Add `.env.example`, Docker Compose, service health endpoints, README commands.
- Make portal, backend, and database start.
- Add CI lint/type-check/test/build.

### Phase 2 - Shared contracts

- Implement canonical enums and Pydantic schemas.
- Implement PostgreSQL models and Alembic migrations.
- Seed demo accounts, facility, users, and canonical case.
- Generate/maintain OpenAPI.

### Phase 3 - Auth/RBAC

- Common login.
- JWT/refresh implementation.
- Role guards in portal.
- Server-side role and resource-scope dependencies.
- Permission tests.

### Phase 4 - Vertical slice

Implement the canonical scenario end-to-end with mock AI:

```text
Citizen case -> ASHA -> referral -> Doctor -> follow-up -> Admin aggregate
```

Do not begin advanced AI until this passes.

### Phase 5 - Offline and resilience

- Citizen SQLite queue.
- ASHA Dexie queue.
- Idempotency and conflict responses.
- Safe provider failure fallbacks.

### Phase 6 - Integrations

Add one adapter at a time behind feature flags:

```text
BHASHINI
Lyzr/Gemini
Milvus
Neo4j
Tavily
n8n
ABDM Sandbox
```

Each adapter requires a mock implementation so the demo remains runnable without credentials.

## 6. Feature flags

Use environment-driven flags:

```text
ENABLE_BHASHINI=false
ENABLE_LYZR=false
ENABLE_TAVILY=false
ENABLE_ABDM=false
ENABLE_N8N=false
USE_MOCK_EXTERNAL_SERVICES=true
```

The application must boot and complete the canonical demo with mock external services.

## 7. Commands to provide

Create a root README with actual repository-specific commands equivalent to:

```bash
cp .env.example .env
docker compose up -d
cd backend && <install> && <migrate> && <seed> && <run>
cd apps/healthcare-portal && <install> && <run>
cd apps/citizen-mobile && <install> && <run>
```

Also provide:

```text
lint
type-check
unit tests
integration tests
end-to-end tests
production builds
database reset for development only
seed demo data
```

Never invent commands without checking package files.

## 8. AI coding workflow

For each task:

1. State the bounded goal.
2. Inspect relevant code.
3. List files to change.
4. Implement minimal coherent changes.
5. Add tests.
6. Run formatter/lint/type-check/tests/build.
7. Fix failures within scope.
8. Report changed files, commands, results, and remaining blockers.

## 9. Code quality

- Prefer small reusable components and services.
- Keep business rules in backend domain services.
- Keep provider logic inside adapters.
- Use transactions for multi-record workflow changes.
- Use parameterized SQL/Cypher.
- Add indexes for query patterns.
- Use structured, redacted logging.
- Include docstrings/comments for safety-critical logic, not obvious code.

## 10. Testing requirements

Mandatory backend tests:

- role permissions;
- valid/invalid state transitions;
- deterministic urgent rule;
- duplicate offline sync;
- ASHA assignment scope;
- doctor facility scope;
- prescription authorization;
- admin de-identification;
- AI failure fallback.

Mandatory frontend tests:

- protected redirects;
- urgent badge uses icon/text;
- loading/empty/error states;
- field-visit validation;
- doctor explicit issue confirmation;
- offline queue status.

Mandatory Playwright flow:

```text
create case -> acknowledge ASHA -> vitals -> refer -> doctor acknowledge
-> complete consultation -> ASHA follow-up -> admin aggregate
```

## 11. Safety gates

Before release, verify:

- no LLM can prescribe;
- no AI output bypasses deterministic urgent rules;
- no admin endpoint exposes names/phone/ABHA;
- no patient data enters Milvus;
- no secret is shipped to frontend;
- all external provider failures are explicit;
- mock/sandbox states are labelled;
- audit logs exist for clinical writes.

## 12. Team merge rules

Branches:

```text
feature/citizen-app
feature/asha-portal
feature/doctor-portal
feature/admin-portal
feature/backend-core
```

- Pull latest develop before starting.
- Commit small vertical changes.
- Do not mix formatting of unrelated files.
- Pull requests must include screenshots, API changes, tests, and migration notes.
- API/data-model changes require integration-owner approval.

## 13. Initial implementation prompt

Use this prompt after placing these specifications in the repository:

```text
Read every Markdown file in the project specification directory from
01-PROJECT-CONTEXT.md through 09-DESIGN.md.

First inspect the existing repository and produce a gap analysis against the
specifications. Do not edit files during the inspection.

Then propose a phased implementation plan that preserves existing work. Begin
only with Phase 1: runnable scaffold, Docker services, environment template,
backend health check, portal health screen, database migration, seed data, and
test commands.

Do not build all features in one pass. Do not replace the specified stack.
Do not expose secrets or weaken clinical safety/RBAC. After implementing Phase
1, run all available checks and report exact commands and results before asking
to continue.
```

## 14. Completion report

At the end, the AI IDE must provide:

- architecture actually implemented;
- exact run commands;
- demo credentials marked development-only;
- migrations applied;
- tests and results;
- external integrations real vs mocked;
- security limitations;
- incomplete requirements;
- step-by-step canonical demo.

