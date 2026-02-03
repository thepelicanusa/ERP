# Core cross-module flows (MVP)

## E-commerce → Sales → MRP/Planning
1. `ecommerce.order.placed`
2. Sales service creates/Confirms Sales Order → publishes `sales.order.confirmed`
3. MRP/Planning subscribes → creates demand signals / planned orders

## Purchasing → Receiving → QMS Hold/Release
1. `purch.receipt.posted` (or Inventory emits `inventory.lot.received`)
2. QMS subscribes → emits `qms.inspection.required` and/or `qms.lot.held`
3. Inventory enforces holds; WMS/MES cannot consume held lots
4. After inspection, QMS emits `qms.lot.released`

## MES Actuals → Inventory → Accounting
1. MES emits `mes.material.consumed` and `mes.operation.completed`
2. Inventory emits stock issue/move facts (if Inventory is ledger-of-record)
3. Accounting subscribes → posts `acct.journal.posted` (WIP/COGS/inventory valuation)
