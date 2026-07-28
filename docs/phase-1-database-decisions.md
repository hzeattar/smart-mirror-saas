# Phase 1 Database Decisions

## 1. Shared-database tenancy

The first version uses a shared database and shared tables with `tenant_id` ownership columns. This is operationally simpler for a SaaS MVP and still supports strong isolation when Phase 2 adds tenant middleware, policies, and scoped repositories.

## 2. Stable internal IDs and safe public IDs

Tables use numeric primary keys for efficient joins. Orders also expose a UUID `public_id`, preventing predictable order URLs and avoiding leakage of internal sequence values.

## 3. Strings plus PHP enums

Status and type columns are stored as indexed strings rather than database-native enums. PHP backed enums provide type safety while string columns remain easier to evolve across MySQL, PostgreSQL, and SQLite.

## 4. Catalog deletion behavior

Tenant deletion cascades through its owned data. Category deletion sets `products.category_id` to null, preserving products. Product and size deletion set item references to null, while snapshots in `order_items` preserve historical order details.

## 5. Monetary snapshots

`products.unit_price` is the current catalog price. `order_items.unit_price` and `line_total` are immutable order-time values. The default currency is EGP and can be explicitly changed per product and order.

## 6. Measurement precision

Garment measurements use `DECIMAL(6,2)` rather than floating-point values to store exact centimeter values without binary rounding drift.

## 7. Device lifecycle

Mirrors include pairing, last-seen, and status fields needed for the next phase. Credentials or long-lived device tokens are deliberately not stored yet; their hashing and rotation model belongs in Phase 2.

## 8. Tenant isolation boundary

No automatic global scope is enabled in Phase 1. A global scope before authentication and CLI/system-job rules are designed can cause accidental data hiding and unsafe bypasses. Phase 2 should establish a tenant context service first, then apply scopes and policies consistently.
