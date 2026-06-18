# API & Interface Design Checklist

## [P1] List Endpoint OOM Protection

Every list/query endpoint must enforce pagination limits — unbounded queries can crash the service:

- Backend must set a hard `MaxPageSize` ceiling (e.g., 100 records per page)
- Even if the frontend doesn't pass `pageSize`, the backend must default to a safe limit
- Export endpoints need streaming or chunked approaches for large datasets

### Patterns to Flag
```java
// Dangerous: no page size limit
public List<Order> listOrders(OrderQuery query) {
    return orderDao.selectList(query);  // Could return millions of rows
}

// Safe: enforce ceiling
public Page<Order> listOrders(OrderQuery query) {
    if (query.getPageSize() == null || query.getPageSize() > 100) {
        query.setPageSize(100);
    }
    return orderDao.selectPage(query);
}
```

## [P1] Incremental Updates with Optimistic Locking

Update endpoints should NOT accept full-object payloads and blindly overwrite:

- Accept only the changed fields + a `version` field for optimistic lock validation
- Full overwrites cause data loss when two users edit different fields concurrently
- Use `UPDATE ... SET field1 = ?, version = version + 1 WHERE id = ? AND version = ?`

### Patterns to Flag
```java
// Dangerous: full overwrite
public void updateOrder(Order order) {
    orderDao.updateById(order);  // Overwrites ALL fields, last-write-wins
}

// Safe: partial update with version check
public void updateOrder(OrderUpdateDTO dto) {
    int rows = orderDao.updateSelectiveWithVersion(
        dto.getId(), dto.getChangedFields(), dto.getVersion()
    );
    if (rows == 0) {
        throw new OptimisticLockException("Data has been modified by another user");
    }
}
```

## [P1/P2] N+1 Query Prevention

SQL or RPC calls inside loops are a performance anti-pattern that degrades linearly with data size. P1 on hot paths (high-frequency endpoints), P2 on low-frequency paths.

### The Pattern
```java
// BAD: N+1 queries
List<Order> orders = orderDao.list(query);
for (Order order : orders) {
    Customer customer = customerDao.getById(order.getCustomerId());  // N queries!
    order.setCustomerName(customer.getName());
}

// GOOD: batch query + in-memory Map join
List<Order> orders = orderDao.list(query);
Set<Long> customerIds = orders.stream().map(Order::getCustomerId).collect(toSet());
Map<Long, Customer> customerMap = customerDao.listByIds(customerIds)
    .stream().collect(toMap(Customer::getId, Function.identity()));
for (Order order : orders) {
    Customer customer = customerMap.get(order.getCustomerId());
    order.setCustomerName(customer != null ? customer.getName() : null);
}
```

### Questions to Ask
- "Is there a query/RPC call inside this for-loop?"
- "How many iterations could this loop have in production?"

## [P2] Batch Operations

Multi-record insert/update must use batch APIs, not single-record loops:

- `insertBatchSomeColumn` / `saveBatch` instead of looped `insert`
- `updateBatchById` instead of looped `updateById`
- For very large batches (>1000 records), chunk into sub-batches to avoid oversized SQL statements

### Patterns to Flag
```java
// BAD: loop insert
for (OrderLine line : lines) {
    orderLineDao.insert(line);  // N round-trips to DB
}

// GOOD: batch insert
orderLineDao.insertBatchSomeColumn(lines);

// GOOD: chunked batch for large datasets
Lists.partition(lines, 500).forEach(chunk -> {
    orderLineDao.insertBatchSomeColumn(chunk);
});
```

## [P1] Scheduled Task Design

### Skip-if-Running (Concurrency Guard)
- Scheduled tasks must configure "disallow concurrent execution"
- If a previous run hasn't finished, the current trigger must SKIP (not queue)
- Queuing causes task pile-up and potential cascade failure — P1 because it can crash the service

### Distributed Environment
- Multiple service instances must use distributed locks (Redis / ShedLock) so only one node executes
- Lock TTL must exceed the maximum expected task duration

### Patterns to Flag
```java
// Dangerous: no concurrent execution guard
@Scheduled(cron = "0 0/5 * * * ?")
public void syncJob() {
    // What if this takes >5 minutes? Next trigger starts overlapping execution
}

// Safe: AtomicBoolean guard (single-instance)
private final AtomicBoolean running = new AtomicBoolean(false);

@Scheduled(cron = "0 0/5 * * * ?")
public void syncJob() {
    if (!running.compareAndSet(false, true)) {
        log.warn("Previous run still active, skipping");
        return;
    }
    try {
        // business logic
    } finally {
        running.set(false);
    }
}
```

---

## [P3] Lazy Loading (Detail Page Splitting)

Detail/info endpoints should not load everything in one call. Split by response-time characteristics:

- **Core data** (fast): Returns immediately — header fields, status, key attributes
- **Expensive data** (slow): Loaded on-demand via separate endpoint — BOM trees, audit logs, large text fields, attachment lists, history records

### Questions to Ask
- "Does this detail endpoint load data the user won't see until they click a tab?"
- "Is there a sub-query here that could take >200ms and delay the entire response?"
