# Code Review Expert

A comprehensive code review skill for AI agents. Performs structured reviews with a senior engineer lens, covering architecture, security, database migrations, business logic patterns, messaging reliability, API design, and code quality.

## Features

- **Database & Flyway** - Script immutability, SQL idempotency, large table DDL strategy
- **Core Business Logic** - Transaction safety, concurrency control, idempotency, state machines
- **Messaging** - Send timing (after commit), consumer idempotency, ordering guarantees
- **API Design** - OOM protection, N+1 prevention, optimistic locking, batch operations
- **Scheduled Tasks** - Skip-if-running guards, distributed lock enforcement
- **SOLID Principles** - Detect SRP, OCP, LSP, ISP, DIP violations
- **Security Scan** - XSS, injection, SSRF, race conditions, auth gaps, secrets leakage
- **Performance** - N+1 queries, CPU hotspots, missing cache, memory issues
- **Error Handling** - Swallowed exceptions, async errors, missing boundaries
- **Boundary Conditions** - Null handling, empty collections, off-by-one, numeric limits
- **Removal Planning** - Identify dead code with safe deletion plans

## Usage

After installation, simply run:

```
/code-review-expert
```

The skill will automatically review your current git changes.

## Workflow

1. **Preflight** - Scope changes via `git diff`, classify change type
2. **Database & Flyway** - Migration safety, SQL idempotency, large table DDL
3. **Core Business Logic** - Transaction rollback, concurrency, idempotency, state machines
4. **Messaging** - Send timing, consumer idempotency, ordering
5. **API & Interface** - Pagination limits, N+1, optimistic locking, batch ops
6. **Scheduled Tasks** - Concurrency guards, distributed locks
7. **SOLID + Architecture** - Design principles and code smells
8. **Removal Candidates** - Find dead/unused code
9. **Security Scan** - Vulnerability detection
10. **Code Quality** - Error handling, performance, boundaries
11. **Output** - Findings by severity (P0-P3)
12. **Confirmation** - Ask user before implementing fixes

## Severity Levels

| Level | Name | Criteria | Action |
|-------|------|----------|--------|
| P0 | Critical | Breaks startup, data loss/corruption, security hole, full-business lock | Must block merge |
| P1 | High | Runtime blocker: concurrency corruption, OOM, workflow deadlock, duplicates | Should fix before merge |
| P2 | Medium | Quality concern: performance, maintainability, non-critical design flaw | Fix or create follow-up |
| P3 | Low | Suggestion: naming, structure tweaks, minor optimization | Optional improvement |

## Structure

```
code-review-expert/
├── SKILL.md                          # Main skill definition
├── README.md                         # This file
├── agents/
│   └── agent.yaml                    # Agent interface config
└── references/
    ├── database-checklist.md         # Flyway, SQL idempotency, large table DDL
    ├── business-checklist.md         # Concurrency, idempotency, state machines, transactions
    ├── messaging-checklist.md        # MQ send timing, consumer idempotency, ordering
    ├── api-design-checklist.md       # Pagination, N+1, batch ops, scheduled tasks
    ├── solid-checklist.md            # SOLID smell prompts
    ├── security-checklist.md         # Security & reliability
    ├── code-quality-checklist.md     # Error, perf, boundaries
    └── removal-plan.md              # Deletion planning template
```

## References

Each checklist provides detailed prompts, anti-patterns, and code examples:

- **database-checklist.md** - Flyway script immutability, SQL idempotency (DDL/DML guard patterns), large table DDL lock-avoidance strategy
- **business-checklist.md** - Transaction safety (@Transactional exception handling), distributed/optimistic locking, idempotency patterns, snapshot vs reference field design, state machine completeness
- **messaging-checklist.md** - Message send timing (afterCommit / @TransactionalEventListener), consumer duplicate handling, Partition Key ordering
- **api-design-checklist.md** - List endpoint OOM protection, N+1 query prevention, incremental updates with version check, batch operations, scheduled task concurrency guards
- **solid-checklist.md** - SOLID violations + common code smells
- **security-checklist.md** - OWASP risks, race conditions, crypto, supply chain
- **code-quality-checklist.md** - Error handling, caching, N+1, null safety
- **removal-plan.md** - Safe vs deferred deletion with rollback plans

## License

MIT
