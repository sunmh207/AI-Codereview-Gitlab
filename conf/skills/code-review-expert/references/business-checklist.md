# Core Business Logic (TP) Checklist

## [P0] Transaction Safety

### Exception Handling in @Transactional Methods
- try-catch blocks inside `@Transactional` methods **must re-throw** the exception (or a RuntimeException) — otherwise Spring considers the method successful and commits
- Catching and logging without re-throwing is the #1 cause of silent data corruption
- This is P0 because it causes invisible data corruption that's extremely difficult to detect and diagnose after the fact

### Patterns to Flag
```java
// CRITICAL BUG (P0): transaction will commit despite the error!
@Transactional
public void createOrder(OrderDTO dto) {
    try {
        // business logic
    } catch (Exception e) {
        log.error("Error", e);
        // Missing throw → silent commit of partial/corrupt data
    }
}

// Fix: re-throw
@Transactional
public void createOrder(OrderDTO dto) {
    try {
        // business logic
    } catch (Exception e) {
        log.error("Error", e);
        throw new BusinessException("Order creation failed", e);
    }
}
```

### Questions to Ask
- "If this operation fails halfway, will partial data be committed?"
- "Does every catch block in a @Transactional method re-throw or explicitly trigger rollback?"

---

## [P1] Concurrency Control

### Distributed Locking
- Hot resources (inventory deduction, order placement, balance operations) must use distributed locks (Redis `SET NX EX`) or database-level optimistic locking
- Redis lock must have a reasonable TTL and use owner-based release (Lua script to check-then-delete)
- Optimistic locking: use `version` column with CAS update (`UPDATE ... SET version = version + 1 WHERE version = ?`)

### Patterns to Flag
```java
// Dangerous: read-modify-write without lock
Stock stock = stockDao.getById(id);
stock.setQuantity(stock.getQuantity() - qty);
stockDao.update(stock);  // Lost update under concurrency

// Safe: CAS with version
int rows = stockDao.deductWithVersion(id, qty, currentVersion);
if (rows == 0) throw new OptimisticLockException();
```

## [P1] Idempotency

Critical save/update interfaces must tolerate duplicate calls safely:

- **Token mechanism**: Frontend obtains a one-time token; backend validates and invalidates on first use
- **Unique business key**: Use database unique constraint on business-meaningful fields (e.g., order number + line number)
- **State pre-check**: Before state transitions, verify current state matches expected pre-condition

### Questions to Ask
- "What happens if this endpoint is called twice with the same payload?"
- "Is there a unique constraint that prevents duplicate records?"

## [P2] Field Attribute Design: Snapshot vs Reference

Not all fields should be live-lookup references — some must be frozen at transaction time.

### Must Snapshot (Store Redundantly)
- **Price/cost at order time**: Product price may change; the order must record the price as-of-order
- **Customer/supplier name at transaction time**: Name changes shouldn't alter historical documents
- **Unit conversion rates**: Converting between measurement units uses a rate that must be fixed at transaction time
- **Batch/serial number control flags**: Whether a material requires batch tracking — this flag must be snapshotted because master data changes shouldn't retroactively alter inventory logic

### Use Reference (Store ID Only)
- Data that must reflect current state (e.g., current inventory level)
- Configuration that applies universally and doesn't affect historical correctness

### Questions to Ask
- "If the master data changes tomorrow, should this historical record change too?"
- "Is this field recording a fact-at-time-of-event, or a live pointer?"

## [P1] State Machine Completeness

Business workflows (approval flows, order lifecycle, production processes) must form a closed-loop state machine:

- Every state must have at least one outgoing transition (no dead-end states)
- Terminal states (Completed, Cancelled, Rejected) must be explicitly defined
- Rejection/cancellation paths must exist for every non-terminal state
- State transitions must be guarded: validate current state before allowing transition

### Patterns to Flag
```java
// Dangerous: no current-state validation
order.setStatus(OrderStatus.APPROVED);

// Safe: validate transition
if (order.getStatus() != OrderStatus.PENDING_APPROVAL) {
    throw new IllegalStateException("Cannot approve from state: " + order.getStatus());
}
order.setStatus(OrderStatus.APPROVED);
```

