import React, { useEffect, useMemo, useState } from "react";

type Mod = {
      installed_version?: string | null;
  module_key: string;
  name: string;
  version: string;
  dependencies: string[];
  installed: boolean;
  enabled: boolean;
  installable: boolean;
  seeders: string[];
};

async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export default function App() {
  const [mods, setMods] = useState<Mod[]>([]);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setError(null);
    const data = await api<Mod[]>("/admin/modules");
    setMods(data);
  };

  useEffect(() => {
    refresh().catch((e) => setError(String(e)));
  }, []);

  const byKey = useMemo(() => {
    const m = new Map<string, Mod>();
    mods.forEach((x) => m.set(x.module_key, x));
    return m;
  }, [mods]);

  const canInstall = (m: Mod) =>
    m.installable && !m.installed && m.dependencies.every((d) => byKey.get(d)?.installed);

  const canEnable = (m: Mod) =>
    m.installed && !m.enabled && m.dependencies.every((d) => byKey.get(d)?.enabled);

  const install = async (key: string) => {
    setBusyKey(key);
    setError(null);
    try {
      await api(`/admin/modules/${key}/install`, { method: "POST", body: JSON.stringify({}) });
      await refresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusyKey(null);
    }
  };

  const enable = async (key: string) => {
    setBusyKey(key);
    setError(null);
    try {
      await api(`/admin/modules/${key}/enable`, { method: "POST", body: JSON.stringify({}) });
      await refresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusyKey(null);
    }
  };

  const disable = async (key: string) => {
    setBusyKey(key);
    setError(null);
    try {
      await api(`/admin/modules/${key}/disable`, { method: "POST", body: JSON.stringify({}) });
      await refresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusyKey(null);
    }
  };

  const upgrade = async (key: string) => {
        setBusyKey(`upgrade:${key}`);
        setError(null);
        try {
          await api(`/admin/modules/${key}/upgrade`, { method: "POST", body: JSON.stringify({}) });
          await refresh();
        } catch (e: any) {
          setError(e.message || String(e));
        } finally {
          setBusyKey(null);
        }
      };

      const seed = async (key: string, seedKey: string) => {
    setBusyKey(`${key}:${seedKey}`);
    setError(null);
    try {
      await api(`/admin/modules/${key}/seed/${seedKey}`, { method: "POST", body: JSON.stringify({}) });
      await refresh();
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 16, maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ margin: "0 0 8px" }}>Module Installer</h1>
      <p style={{ marginTop: 0, color: "#444" }}>
        Install = mark module installed (migrations hook point). Enable/Disable = tenant toggle.
      </p>

      {error && (
        <div style={{ background: "#fee", border: "1px solid #f99", padding: 12, borderRadius: 8, marginBottom: 12 }}>
          <b>Error:</b> <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{error}</pre>
        </div>
      )}

      <button onClick={() => refresh()} disabled={!!busyKey} style={{ marginBottom: 12 }}>
        Refresh
      </button>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left" style={{ borderBottom: "1px solid #ddd", padding: "8px 6px" }}>Module</th>
            <th align="left" style={{ borderBottom: "1px solid #ddd", padding: "8px 6px" }}>Version</th>
            <th align="left" style={{ borderBottom: "1px solid #ddd", padding: "8px 6px" }}>Dependencies</th>
            <th align="left" style={{ borderBottom: "1px solid #ddd", padding: "8px 6px" }}>Status</th>
            <th align="left" style={{ borderBottom: "1px solid #ddd", padding: "8px 6px" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {mods.map((m) => (
            <tr key={m.module_key}>
              <td style={{ borderBottom: "1px solid #eee", padding: "10px 6px" }}>
                <div style={{ fontWeight: 600 }}>{m.name}</div>
                <div style={{ color: "#666", fontSize: 12 }}>{m.module_key}</div>
              </td>
              <td style={{ borderBottom: "1px solid #eee", padding: "10px 6px" }}>{m.version}</td>
              <td style={{ borderBottom: "1px solid #eee", padding: "10px 6px" }}>
                {m.dependencies.length ? m.dependencies.join(", ") : <span style={{ color: "#777" }}>—</span>}
              </td>
              <td style={{ borderBottom: "1px solid #eee", padding: "10px 6px" }}>
                <div>Installed: {m.installed ? "✅" : "❌"}</div>
                    <div style={{ color: "#666", fontSize: 12 }}>
                      Installed version: {m.installed_version || "—"}
                    </div>
                <div>Enabled: {m.enabled ? "✅" : "❌"}</div>
              </td>
              <td style={{ borderBottom: "1px solid #eee", padding: "10px 6px" }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    disabled={!!busyKey || !canInstall(m)}
                    onClick={() => install(m.module_key)}
                    title={!canInstall(m) ? "Install requires dependencies installed first" : ""}
                  >
                    {busyKey === m.module_key ? "Installing..." : "Install"}
                  </button>
                  <button
                    disabled={!!busyKey || !canEnable(m)}
                    onClick={() => enable(m.module_key)}
                    title={!canEnable(m) ? "Enable requires dependencies enabled first" : ""}
                  >
                    Enable
                  </button>
                  <button disabled={!!busyKey || !m.enabled} onClick={() => disable(m.module_key)}>
                    Disable
                  </button>
                  {(m.seeders || []).map((s) => (
                    <button
                      key={s}
                      disabled={!!busyKey || !m.enabled || !m.installed}
                      onClick={() => seed(m.module_key, s)}
                    >
                      Seed: {s}
                    </button>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 18, color: "#666", fontSize: 12 }}>
        Notes: this build runs as a single-tenant ("default") demo. In SaaS, enable/disable is per-tenant.
      </div>
    </div>
  );
}
