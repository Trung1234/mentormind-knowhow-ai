import React, { useEffect, useState } from "react";
import { api } from "./api";
import { ReviewProfilesTab } from "./components/ReviewProfilesTab";
import { AssistantTab } from "./components/AssistantTab";
import { RcaTab } from "./components/RcaTab";
import { CheckSquare, Bot, Activity, Database, Radio, Cpu, Wifi, WifiOff } from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState<"review" | "assistant" | "rca">("review");
  const [healthStatus, setHealthStatus] = useState<{ status: string; neo4j: string; postgres: string } | null>(null);
  const [apiError, setApiError] = useState(false);

  useEffect(() => {
    const checkHealth = () => {
      api
        .getHealth()
        .then((res) => {
          setHealthStatus(res);
          setApiError(false);
        })
        .catch(() => {
          setApiError(true);
        });
    };
    checkHealth();
    const timer = setInterval(checkHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  const neo4jStatus  = healthStatus?.neo4j?.toLowerCase() || "ready";
  const pgStatus     = healthStatus?.postgres?.toLowerCase() || "ready";

  return (
    <div className="app-container">
      {/* ── Animated Background Layer ── */}
      <div className="animated-bg" aria-hidden="true">
        <div className="orb-1" />
        <div className="orb-2" />
        <div className="orb-3" />
        <div className="orb-4" />
        <div className="dot-grid" />
        <div className="scanline" />
      </div>

      {/* ── Premium HUD Header ── */}
      <header className="app-header">
        <div className="header-left">
          {/* DENSO red emblem */}
          <div className="denso-badge">DENSO</div>

          <div className="header-brand">
            <h1 className="header-title">
              MentorMind
              <span className="header-event-tag">FACTORY HACKS 2026</span>
            </h1>
            <p className="header-subtitle">
              Know-How Extraction &amp; Validation Engine // Industrial AI
            </p>
          </div>
        </div>

        {/* System telemetry pills */}
        <div className="header-status">
          <div className="status-pill">
            <span className={`status-dot ${apiError ? "offline" : ""}`} />
            {apiError
              ? <><WifiOff size={11} /><span>API OFFLINE</span></>
              : <><Wifi size={11} /><span>API ONLINE</span></>
            }
          </div>

          <div className="status-pill">
            <Database size={11} color="#00d4ff" />
            <span>GRAPH: {neo4jStatus.toUpperCase()}</span>
          </div>

          <div className="status-pill">
            <Radio size={11} color="#10b981" />
            <span>VECTOR: {pgStatus.toUpperCase()}</span>
          </div>

          <div className="status-pill" style={{ borderColor: "rgba(230,0,18,0.28)", color: "rgba(255,80,90,0.9)" }}>
            <Cpu size={11} color="#e60012" />
            <span>LINE: PACK01 // ST-04</span>
          </div>
        </div>
      </header>

      {/* ── Navigation Tabs ── */}
      <nav className="tabs-nav">
        <button
          id="tab-review"
          className={`tab-btn ${activeTab === "review" ? "active" : ""}`}
          onClick={() => setActiveTab("review")}
        >
          <CheckSquare size={15} />
          <span className="tab-num">01 //</span>
          <span>Human-in-the-Loop Review</span>
        </button>

        <button
          id="tab-assistant"
          className={`tab-btn ${activeTab === "assistant" ? "active" : ""}`}
          onClick={() => setActiveTab("assistant")}
        >
          <Bot size={15} />
          <span className="tab-num">02 //</span>
          <span>Verified RAG Assistant</span>
        </button>

        <button
          id="tab-rca"
          className={`tab-btn ${activeTab === "rca" ? "active" : ""}`}
          onClick={() => setActiveTab("rca")}
        >
          <Activity size={15} />
          <span className="tab-num">03 //</span>
          <span>5-Why &amp; RCA Engine</span>
        </button>
      </nav>

      {/* ── Main Content ── */}
      <main className="main-content">
        {activeTab === "review"    && <ReviewProfilesTab />}
        {activeTab === "assistant" && <AssistantTab />}
        {activeTab === "rca"       && <RcaTab />}
      </main>
    </div>
  );
}
