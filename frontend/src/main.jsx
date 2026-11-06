import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";


const API = "/api/v1";

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      body.detail || body.error?.message || "Request failed (" + response.status + ")"
    );
  }

  return response.status === 204 ? null : response.json();
}

function App() {
  const [device, setDevice] = useState(null);
  const [commands, setCommands] = useState([]);
  const [pairingCode, setPairingCode] = useState("");
  const [deviceName, setDeviceName] = useState("My phone");
  const [buffer, setBuffer] = useState("");
  const [runs, setRuns] = useState([]);
  const [activeRun, setActiveRun] = useState(null);
  const [connection, setConnection] = useState("connecting");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("dashboard");
  const socketRef = useRef(null);
  const reconnectRef = useRef(0);
  const activeRunRef = useRef(null);
  activeRunRef.current = activeRun;

  const refreshRuns = useCallback(async () => {
    try {
      const data = await api("/runs?limit=12");
      setRuns(data.runs || []);
      const current = activeRunRef.current;
      if (current) {
        const latest = await api("/runs/" + current.id);
        setActiveRun(latest.run);
      }
    } catch { /* the connection state reports network failures */ }
  }, []);

  const load = useCallback(async () => {
    try {
      const pair = await Promise.all([api("/device"), api("/commands")]);
      setDevice(pair[0].device);
      setCommands(pair[1].commands);
      setConnection("connected");
      setError("");
      await refreshRuns();
    } catch (e) {
      if (/Pair this device|Session expired|401/i.test(e.message)) setDevice(null);
      else setError(e.message);
      setConnection("disconnected");
    }
  }, [refreshRuns]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!device) return undefined;
    let stopped = false;
    let socket;
    let timer;
    const connect = () => {
      if (stopped) return;
      setConnection(reconnectRef.current ? "reconnecting" : "connecting");
      const scheme = location.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(scheme + "//" + location.host + API + "/ws");
      socketRef.current = socket;
      socket.onopen = () => { reconnectRef.current = 0; setConnection("connected"); };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.run) {
          setActiveRun((current) => current && current.id === message.run.id ? { ...current, ...message.run } : current);
        }
        if (message.type === "run.completed") refreshRuns();
      };
      socket.onclose = (event) => {
        if (stopped) return;
        if (event.code === 4401) { load(); return; }
        reconnectRef.current += 1;
        setConnection("reconnecting");
        timer = setTimeout(connect, Math.min(10000, 500 * (2 ** Math.min(reconnectRef.current, 5))));
      };
      socket.onerror = () => socket.close();
    };
    connect();
    return () => { stopped = true; clearTimeout(timer); socket?.close(); };
  }, [device, refreshRuns, load]);

  useEffect(() => {
    if (!activeRun || !["queued", "running"].includes(activeRun.status)) return undefined;
    const timer = setInterval(refreshRuns, 2000);
    return () => clearInterval(timer);
  }, [activeRun?.id, activeRun?.status, refreshRuns]);

  const byKey = useMemo(() => Object.fromEntries(commands.map((c) => [c.key, c])), [commands]);
  const busy = activeRun && ["queued", "running"].includes(activeRun.status);

  const execute = async (command, source) => {
    if (!command || busy || connection !== "connected") return;
    setError("");
    try {
      const result = await api("/commands/" + command.id + "/runs", {
        method: "POST",
        headers: { "Idempotency-Key": Date.now().toString(36) + Math.random().toString(36).slice(2) },
        body: JSON.stringify({ source }),
      });
      setActiveRun(result.run);
      setTab("dashboard");
      refreshRuns();
    } catch (e) { setError(e.message); }
  };

  const press = (key) => {
    if (key === "*") { setBuffer(""); return; }
    if (key === "#") {
      if (buffer.length !== 2) { setError("Enter a two-digit command code."); return; }
      const command = byKey[buffer];
      setBuffer("");
      if (!command) { setError("Unknown command code."); return; }
      execute(command, "keypad");
      return;
    }
    if (buffer.length < 2) setBuffer((value) => value + key);
  };

  const pair = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await api("/pairing/claim", { method: "POST", body: JSON.stringify({
        pairing_code: pairingCode.trim(), device_name: deviceName.trim() || "Phone",
      }) });
      setPairingCode("");
      await load();
    } catch (e) { setError(e.message); }
  };

  const logout = async () => {
    try { await api("/auth/logout", { method: "POST", body: "{}" }); } catch { /* revoke locally */ }
    setDevice(null); setRuns([]); setActiveRun(null);
  };

  if (!device) return <main className="shell auth-shell">
    <header className="topbar"><div className="brand-mark">P</div><div className="brand-copy"><strong>P2C</strong><small>LOCAL MAC REMOTE</small></div><span className="status-dot offline" /></header>
    <section className="pair-card">
      <div className="eyebrow">DEVICE PAIRING</div><h1>Connect to your Mac.</h1>
      <p>Generate a one-time pairing code on your Mac with <code>make pair</code>, then enter it here. Both devices must be on the same trusted network.</p>
      <form onSubmit={pair}>
        <label>Pairing code<input autoComplete="one-time-code" value={pairingCode} onChange={(e) => setPairingCode(e.target.value.toUpperCase())} placeholder="ENTER CODE" maxLength={32} required /></label>
        <label>Device name<input value={deviceName} onChange={(e) => setDeviceName(e.target.value)} maxLength={40} /></label>
        <button className="primary" type="submit">Pair this device <span>↗</span></button>
      </form>
      {error && <div className="error">{error}</div>}
      <div className="security-note">◆ Pairing code expires quickly and can only be used once.</div>
    </section>
    <footer>SELF-HOSTED · NO CLOUD · NO SUBSCRIPTIONS</footer>
  </main>;

  return <main className="shell">
    <header className="topbar">
      <div className="brand-mark">P</div><div className="brand-copy"><strong>P2C</strong><small>MAC CONTROL PANEL</small></div>
      <div className="connection"><span className={"status-dot " + connection} />{connection}</div>
      <button className="icon-button" title="Disconnect device" onClick={logout}>↗</button>
    </header>
    <section className="welcome">
      <div><div className="eyebrow">LOCAL SESSION</div><h1>Hey, {device.name}.</h1><p>Your Mac is ready when you are.</p></div>
      <div className="mac-icon">⌘</div>
    </section>
    <nav className="tabs">
      <button className={tab === "dashboard" ? "selected" : ""} onClick={() => setTab("dashboard")}>Dashboard</button>
      <button className={tab === "keypad" ? "selected" : ""} onClick={() => setTab("keypad")}>Keypad</button>
    </nav>
    {tab === "dashboard" ? <section className="section">
      <div className="section-heading"><div><div className="eyebrow">COMMAND CENTRE</div><h2>Quick actions</h2></div><span className="count">{commands.length} COMMANDS</span></div>
      <div className="command-grid">
        {commands.map((command) => <button className="command-card" key={command.id} disabled={busy || connection !== "connected"} onClick={() => execute(command, "dashboard")}>
          <div className="card-top"><span className="command-icon">{command.id === "system.status" ? "◉" : command.id === "system.disk" ? "▤" : "⌁"}</span><span className="command-key">{command.key}</span></div>
          <strong>{command.label}</strong><small>{command.description}</small><span className="card-action">Run task <span>↗</span></span>
        </button>)}
      </div>
      <div className="section-heading activity-heading"><div><div className="eyebrow">LIVE FEEDBACK</div><h2>Execution</h2></div>{busy && <span className="running-pill">● RUNNING</span>}</div>
      {activeRun ? <div className="result-card">
        <div className="result-head"><div><strong>{commands.find((c) => c.id === activeRun.command_id)?.label || activeRun.command_id}</strong><small>{activeRun.id}</small></div><span className={"run-status " + activeRun.status}>{activeRun.status.replace("_", " ")}</span></div>
        {busy && <div className="progress"><span /></div>}
        {activeRun.output && <pre>{activeRun.output}</pre>}
        {activeRun.duration_ms != null && <small className="duration">Completed in {activeRun.duration_ms} ms</small>}
        {activeRun.output_truncated && <small className="duration">Output truncated for safety.</small>}
      </div> : <div className="empty-state"><span>⌁</span><p>Choose a command to see its output here.</p></div>}
      <div className="section-heading activity-heading"><div><div className="eyebrow">HISTORY</div><h2>Recent activity</h2></div></div>
      <div className="history">{runs.map((run) => <div className="history-row" key={run.id}><span className="history-mark">↳</span><div><strong>{commands.find((c) => c.id === run.command_id)?.label || run.command_id}</strong><small>{new Date(run.created_at * 1000).toLocaleString()}</small></div><span className={"run-status " + run.status}>{run.status}</span></div>)}{!runs.length && <p className="muted">No commands have run yet.</p>}</div>
    </section> : <section className="section keypad-section">
      <div className="eyebrow">DIRECT COMMAND INPUT</div><h2>Enter a code.</h2><p className="muted">Type a two-digit code, then press # to execute.</p>
      <div className="display"><span>{buffer || "— —"}</span><small>{buffer.length}/2</small></div>
      <div className="keypad">{["1","2","3","4","5","6","7","8","9","*","0","#"].map((key) => <button key={key} className={key === "#" ? "hash-key" : key === "*" ? "clear-key" : ""} onClick={() => press(key)} disabled={busy || connection !== "connected"}>{key}</button>)}</div>
      <div className="key-hint"><span><b>01</b> System status</span><span><b>02</b> Disk usage</span><span><b>03</b> Network status</span></div>
    </section>}
    {error && <div className="toast" role="alert">{error}<button onClick={() => setError("")}>×</button></div>}
    <footer>LOCAL NETWORK ONLY <span>·</span> NO CLOUD DEPENDENCIES</footer>
  </main>;
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
