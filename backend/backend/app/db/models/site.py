"""
Canonical Site model.

Rule:
- Canonical "Site" is MDMOrgUnit with type="SITE" (ISA-95 style hierarchy).
- inv_site remains legacy execution storage and should NOT be treated as canonical.
"""

from __future__ import annotations

from app.db.models.mdm import MDMOrgUnit

# Canonical Site = org unit row where type == "SITE"
Site = MDMOrgUnit

SITE_TYPE = "SITE"
