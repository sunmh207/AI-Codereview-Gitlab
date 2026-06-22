# Message-Driven Architecture Checklist

## [P0] Message Send Timing — AFTER Transaction Commit

This is a critical correctness rule: **never send MQ messages inside a `@Transactional` method's execution scope.**

### Why This Is P0
If a message is sent before the local transaction commits:
1. Consumer receives the message and queries the database
2. The producer's transaction hasn't committed yet → consumer sees stale/missing data
3. If the producer's transaction rolls back, the message is already sent → permanent inconsistency with no automatic recovery

### Correct Patterns

**Pattern 1: @TransactionalEventListener (Recommended)**
```java
// In the service
@Transactional
public void createOrder(OrderDTO dto) {
    Order order = orderDao.insert(dto);
    applicationEventPublisher.publishEvent(new OrderCreatedEvent(order.getId()));
}

// In the event listener
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void handleOrderCreated(OrderCreatedEvent event) {
    mqProducer.send("order.created", event.getOrderId());
}
```

**Pattern 2: TransactionSynchronizationManager**
```java
@Transactional
public void createOrder(OrderDTO dto) {
    Order order = orderDao.insert(dto);
    
    TransactionSynchronizationManager.registerSynchronization(
        new TransactionSynchronization() {
            @Override
            public void afterCommit() {
                mqProducer.send("order.created", order.getId());
            }
        }
    );
}
```

**Pattern 3: Local Message Table (Outbox Pattern)**
- Write message to a local `outbox` table within the same transaction
- A separate scheduler polls the outbox and sends to MQ
- Most reliable but adds infrastructure complexity

### Patterns to Flag
```java
// CRITICAL BUG (P0): MQ send inside transaction
@Transactional
public void createOrder(OrderDTO dto) {
    orderDao.insert(dto);
    mqProducer.send("order.created", dto.getOrderId());  // Sent before commit!
}
```

### Questions to Ask
- "Is this message send guaranteed to happen only after the local transaction commits?"
- "What happens if the transaction rolls back after the message was sent?"

---

## [P1] Consumer Idempotency

Message consumers **will** receive duplicate messages (network retries, rebalancing, at-least-once delivery). Every consumer must handle this safely.

### Strategies
- **Deduplication table**: Store `messageId` in a unique-key table; reject if exists
- **Business idempotency**: Design the operation so that re-execution produces the same result (e.g., `UPDATE SET status = 'DONE' WHERE status = 'PROCESSING'` is naturally idempotent)
- **State pre-check**: Verify current state before processing; skip if already in target state

### Patterns to Flag
```java
// Dangerous (P1): no duplicate protection
@RabbitListener(queues = "order.paid")
public void onOrderPaid(OrderPaidEvent event) {
    orderService.ship(event.getOrderId());  // Ships twice if message redelivered!
}

// Safe: idempotent check
@RabbitListener(queues = "order.paid")
public void onOrderPaid(OrderPaidEvent event) {
    Order order = orderDao.getById(event.getOrderId());
    if (order.getStatus() != OrderStatus.PAID) {
        return;  // Already processed or in wrong state
    }
    orderService.ship(event.getOrderId());
}
```

---

## [P2] Cross-Service Decoupling (Eventual Consistency)

- Cross-database or cross-service operations should NOT rely on synchronous calls for data consistency
- Use MQ to decouple with retry + compensation for eventual consistency
- Synchronous calls are acceptable for read-only queries or non-critical side effects, but writes across service boundaries belong in async flows

### Questions to Ask
- "If the downstream service is unavailable for 5 minutes, does this operation fail or degrade gracefully?"
- "Is there a compensation mechanism if the async operation fails after retries?"

---

## [P2] Message Ordering (Partition Key)

For order-sensitive business flows (e.g., create -> pay -> ship -> complete), messages must be delivered in sequence.

- Producer must use the same routing/partition key (e.g., OrderID) for all events of the same entity
- Without consistent keys, messages may arrive out of order across different queue partitions/consumers
- RocketMQ: use `orderly` consumer; Kafka: same key = same partition = ordered delivery

### Questions to Ask
- "Does this business flow depend on message ordering?"
- "Are all messages for the same entity routed to the same queue/partition?"
