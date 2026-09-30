import React, { useEffect, useState } from "react";
import { api } from "./api";
import { ReviewProfilesTab } from "./components/ReviewProfilesTab";
import { AssistantTab } from "./components/AssistantTab";
import { RcaTab } from "./components/RcaTab";
import {
  CheckSquare,
  Bot,
  Activity,
  Database,
  Radio,
  Cpu,
  Layers,
} from "lucide-react";

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

  return (
    <div className="app-container">
      {/* Industrial Telemetry Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo-badge">DENSO</div>
          <div className="brand-titles">
            <h1>
              <span>MENTORMIND</span>
              <span className="factory-tag">FACTORY HACKS 2026</span>
            </h1>
            <p>Hệ Thống Trích Xuất & Thẩm Định Bí Quyết Chuyên Gia Sản Xuất (Know-How Engine)</p>
          </div>
        </div>

        <div className="system-status">
          <div className="status-indicator">
            <span className={`status-dot ${apiError ? "error" : ""}`} />
            <span>API: {apiError ? "MẤT KẾT NỐI" : "ONLINE"}</span>
          </div>

          <div className="status-indicator">
            <Database size={14} color="#06b6d4" />
            <span>GRAPH: {healthStatus?.neo4j?.toUpperCase() || "READY"}</span>
          </div>

          <div className="status-indicator">
            <Radio size={14} color="#10b981" />
            <span>VECTOR: {healthStatus?.postgres?.toUpperCase() || "READY"}</span>
          </div>

          <div className="status-indicator" style={{ borderLeft: "2px solid #e60012" }}>
            <Cpu size={14} color="#e60012" />
            <span>LINE: PACK01 // ST-04</span>
          </div>
        </div>
      </header>

      {/* Mechanical Tactical Navigation Tabs */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === "review" ? "active" : ""}`}
          onClick={() => setActiveTab("review")}
        >
          <CheckSquare size={19} />
          <span>01 // DUYỆT THAO TÁC (HUMAN-IN-THE-LOOP)</span>
        </button>

        <button
          className={`tab-btn ${activeTab === "assistant" ? "active" : ""}`}
          onClick={() => setActiveTab("assistant")}
        >
          <Bot size={19} />
          <span>02 // TRỢ LÝ TRUY VẤN (VERIFIED RAG)</span>
        </button>

        <button
          className={`tab-btn ${activeTab === "rca" ? "active" : ""}`}
          onClick={() => setActiveTab("rca")}
        >
          <Activity size={19} />
          <span>03 // TRUY NGUYÊN LỖI (5-WHY & RCA)</span>
        </button>
      </nav>

      {/* Main Content Workspace */}
      <main className="main-content">
        {activeTab === "review" && <ReviewProfilesTab />}
        {activeTab === "assistant" && <AssistantTab />}
        {activeTab === "rca" && <RcaTab />}
      </main>
    </div>
  );
}
