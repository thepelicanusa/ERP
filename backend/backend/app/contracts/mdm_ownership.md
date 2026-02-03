# MDM Ownership Rules

This module is the single source of identity used by every other module.

## Owns (authoritative)
- ISA-95 enterprise hierarchy: **Enterprise/Site/Area/Line/Cell** (`mdm_org_unit`)
- Units of measure (`mdm_uom`)
- Item master, classes, revision/effectivity (`mdm_item`, `mdm_item_class`)
- Parties (Customer/Vendor/Carrier/Other) (`mdm_party`)
- Personnel identity (`mdm_person`)
- Equipment registry (`mdm_equipment`)

## Other modules must only reference
Other modules must store references using these IDs, not duplicate masters:
- `mdm_item_id`
- `mdm_uom_id` (or the UoM code for display only)
- `mdm_party_id`
- `mdm_org_unit_id`
- `mdm_person_id`
- `mdm_equipment_id`

## Never owns (not authoritative)
- On-hand quantities, reservations, handling units (Inventory/WMS)
- Work orders, WIP, dispatch (MES)
- Planning signals and schedules (MRP/Planning)
- GL journals and postings (Accounting)
- Inspection results and CAPA workflows (QMS)

## Events
MDM publishes creation/update/deprecation events in the `mdm.*` domain.
Receivers must treat events as **facts** and should be idempotent.
