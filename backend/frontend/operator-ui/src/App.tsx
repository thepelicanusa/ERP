import React, { useState } from "react"

function TabButton({ active, onClick, children }: any) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "10px 12px",
        borderRadius: 10,
        border: "1px solid #ddd",
        background: active ? "#111" : "#fff",
        color: active ? "#fff" : "#111",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  )
}

// TODO: re-import your real screens once it compiles.
// For now this gets the dev server running.
function Placeholder({ name }: { name: string }) {
  return <div style={{ padding: 16 }}>TODO: {name}</div>
}

export default function App() {
  const [tab, setTab] = useState("operate")

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ margin: 0 }}>Operator UI</h1>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 16 }}>
        <TabButton active={tab === "operate"} onClick={() => setTab("operate")}>Operate</TabButton>
        <TabButton active={tab === "setup"} onClick={() => setTab("setup")}>Setup</TabButton>
        <TabButton active={tab === "docs"} onClick={() => setTab("docs")}>Docs</TabButton>
        <TabButton active={tab === "inventory"} onClick={() => setTab("inventory")}>Inventory</TabButton>
        <TabButton active={tab === "countReview"} onClick={() => setTab("countReview")}>Count Review</TabButton>
        <TabButton active={tab === "waves"} onClick={() => setTab("waves")}>Waves</TabButton>
        <TabButton active={tab === "backorders"} onClick={() => setTab("backorders")}>Backorders</TabButton>
        <TabButton active={tab === "shortPick"} onClick={() => setTab("shortPick")}>Short Picks</TabButton>
        <TabButton active={tab === "shipping"} onClick={() => setTab("shipping")}>Shipping</TabButton>
        <TabButton active={tab === "mes"} onClick={() => setTab("mes")}>MES</TabButton>
      </div>

      <div style={{ marginTop: 16 }}>
        <Placeholder name={tab} />
      </div>
    </div>
  )
}
