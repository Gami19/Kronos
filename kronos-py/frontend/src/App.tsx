import { useEffect, useState } from "react";
import "./App.css";

type HealthState =
  | { kind: "loading" }
  | { kind: "ok"; body: unknown }
  | { kind: "error"; message: string };

export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch("/api/health");
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const body = await res.json();
        if (!cancelled) {
          setHealth({ kind: "ok", body });
        }
      } catch (e) {
        const message =
          e instanceof Error ? e.message : "バックエンドに接続できませんでした";
        if (!cancelled) {
          setHealth({ kind: "error", message });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>kronos-py</h1>
        <p className="tagline">フェーズ0 — API ヘルス確認</p>
      </header>

      <main className="main">
        <section className="health-card" aria-live="polite">
          <h2>バックエンド状態</h2>
          {health.kind === "loading" && (
            <div className="skeleton-block" role="status">
              <span className="sr-only">読み込み中</span>
              <div className="skeleton-line wide" />
              <div className="skeleton-line narrow" />
            </div>
          )}
          {health.kind === "ok" && (
            <pre className="health-json">{JSON.stringify(health.body, null, 2)}</pre>
          )}
          {health.kind === "error" && (
            <p className="health-error">
              <strong>接続エラー:</strong> {health.message}
              <br />
              <span className="hint">
                先に backend を起動しているか確認してください（README の「フェーズ0の起動」）。
              </span>
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
