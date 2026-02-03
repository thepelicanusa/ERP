import React, { useEffect, useMemo, useState } from "react";

type ModRow = {
  module_key: string;
  name: string;
  version: string;
  dependencies: string[];
  installed: boolean;
  installed_version?: string | null;
  enabled: boolean;
  installable: boolean;
  seeders: any[];
};

export default function App() {
  const [health, setHealth] = useState<any>(null);
  const [mods, setMods] = useState<ModRow[] | null>(null);

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ ok: false }));
  }, []);

  useEffect(() => {
    fetch("/admin/modules", { headers: { "X-Tenant-Id": "default" } })
      .then((r) => r.json())
      .then(setMods)
      .catch(() => setMods([]));
  }, []);

  const primaryModules = useMemo(() => {
    const keys = [
      "ecommerce",
      "sales",
      "purchasing",
      "accounting",
      "planning",
      "mrp",
      "inventory",
      "wms",
      "mes",
      "qms",
      "crm",
      "employee",
    ];
    const map = new Map((mods || []).map((m) => [m.module_key, m]));
    return keys.map((k) => map.get(k)).filter(Boolean) as ModRow[];
  }, [mods]);

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16, maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ marginTop: 0 }}>ERP Web</h1>
      <p style={{ color: "#444" }}>
        Single pane of glass for modules (ERP + ISA-95 MOM). Modules stay separate services, but are discoverable and
        governed here.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
        <Card title="Module Installer" desc="Install/enable/upgrade modules" href="http://localhost:5174" />
        <Card title="Operator UI (WMS)" desc="Scanning, tasks, QC, handoff" href="http://localhost:5173" />
        <Card title="API Docs" desc="FastAPI Swagger" href="http://localhost:8000/docs" />
      </div>

      <h2 style={{ marginTop: 22 }}>Core modules</h2>
      <p style={{ color: "#555", marginTop: 6 }}>
        Status is per-tenant. Enable what you need; dependencies are enforced.
      </p>

      {primaryModules.length === 0 ? (
        <div style={{ border: "1px solid #eee", padding: 12, borderRadius: 10, color: "#666" }}>
          Could not load /admin/modules. Start the backend and ensure you are authenticated if required.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 12 }}>
          {primaryModules.map((m) => (
            <ModuleCard key={m.module_key} m={m} />
          ))}
        </div>
      )}

      <h3 style={{ marginTop: 22 }}>Backend status</h3>
      <pre style={{ background: "#f6f6f6", padding: 12, borderRadius: 8, overflow: "auto" }}>
        {JSON.stringify(health, null, 2)}
      </pre>

      <h3>Tenant header</h3>
      <p style={{ color: "#444" }}>
        For tenant isolation, send <code>X-Tenant-Id</code> header. Default is <code>default</code>.
      </p>
    </div>
  );
}

function ModuleCard({ m }: { m: ModRow }) {
  const color = m.enabled ? "#0a7a28" : "#b45309";
  const status = m.enabled ? "Enabled" : "Disabled";
  const apiBase = guessApiBase(m.module_key);

  return (
    <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontWeight: 800 }}>{m.name}</div>
        <span style={{ color, fontWeight: 700 }}>{status}</span>
      </div>
      <div style={{ color: "#666", marginTop: 6 }}>
        <div>
          <b>Key:</b> {m.module_key}
        </div>
        <div>
          <b>Version:</b> {m.version}
        </div>
        {m.dependencies?.length ? (
          <div>
            <b>Deps:</b> {m.dependencies.join(", ")}
          </div>
        ) : null}
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
        <a href="http://localhost:5174" style={linkBtn}>
          Manage →
        </a>
        {apiBase ? (
          <a href={`http://localhost:8000${apiBase}`} style={linkBtn}>
            Open API →
          </a>
        ) : null}
      </div>
    </div>
  );
}

function guessApiBase(key: string): string | null {
  // Keep this minimal and obvious; exact routes live in backend/main.py
  switch (key) {
    case "inventory":
      return "/erp/items"; // inventory ERP endpoints are under /erp
    case "wms":
      return "/wms/control/health";
    case "sales":
      return "/sales/health";
    case "purchasing":
      return "/purchasing/health";
    case "accounting":
      return "/accounting/health";
    case "mrp":
      return "/mrp/health";
    case "planning":
      return "/planning/health";
    case "qms":
      return "/qms/health";
    case "mes":
      return "/mes/health";
    case "crm":
      return "/crm/health";
    case "employee":
      return "/employee/health";
    case "ecommerce":
      return "/ecommerce/health";
    default:
      return null;
  }
}

const linkBtn: React.CSSProperties = {
  textDecoration: "none",
  color: "#0a58ca",
  fontWeight: 700,
};
function Card({ title, desc, href }: { title: string; desc: string; href: string }) {
  return (
    <a href={href} style={{ textDecoration: "none", color: "inherit" }}>
      <div style={{ border: "1px solid #e5e5e5", borderRadius: 12, padding: 14 }}>
        <div style={{ fontWeight: 700 }}>{title}</div>
        <div style={{ color: "#666", marginTop: 6 }}>{desc}</div>
        <div style={{ color: "#0a58ca", marginTop: 10, fontWeight: 700 }}>Open →</div>
      </div>
    </a>
  );
}
