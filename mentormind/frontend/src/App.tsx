import React, { useEffect, useState } from "react";
import { api } from "./api";
import { ReviewProfilesTab } from "./components/ReviewProfilesTab";
import { AssistantTab } from "./components/AssistantTab";
import { RcaTab } from "./components/RcaTab";
import {
  CheckSquare,
  Bot,
  Activity,
  Cpu,
  Database,
  Radio,
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
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo-badge">DENSO</div>
          <div className="brand-titles">
            <h1>MentorMind Know-How AI</h1>
            <p>Hệ Thống Trích Xuất & Thẩm Định Bí Quyết Chuyên Gia Sản Xuất</p>
          </div>
        </div>

        <div className="system-status">
          <div className="status-indicator">
            <span className={`status-dot ${apiError ? "error" : ""}`} />
            <span>API: {apiError ? "Mất kết nối" : "Sẵn sàng"}</span>
          </div>

          <div className="status-indicator">
            <Database size={14} color="#3b82f6" />
            <span>Neo4j: {healthStatus?.neo4j || "online"}</span>
          </div>

          <div className="status-indicator">
            <Radio size={14} color="#10b981" />
            <span>Postgres: {healthStatus?.postgres || "online"}</span>
          </div>
        </div>
      </header>

      {/* Main Tabs Navigation */}
      <nav className="tabs-nav">
        <button
          className={`tab-btn ${activeTab === "review" ? "active" : ""}`}
          onClick={() => setActiveTab("review")}
        >
          <CheckSquare size={20} />
          <span>1. Duyệt thao tác (Review Profiles)</span>
        </button>

        <button
          className={`tab-btn ${activeTab === "assistant" ? "active" : ""}`}
          onClick={() => setActiveTab("assistant")}
        >
          <Bot size={20} />
          <span>2. Hỏi trợ lý (Know-How Assistant)</span>
        </button>

        <button
          className={`tab-btn ${activeTab === "rca" ? "active" : ""}`}
          onClick={() => setActiveTab("rca")}
        >
          <Activity size={20} />
          <span>3. Truy nguyên lỗi (RCA & 5-Why)</span>
        </button>
      </nav>

      {/* Main Tab Content */}
      <main className="main-content">
        {activeTab === "review" && <ReviewProfilesTab />}
        {activeTab === "assistant" && <AssistantTab />}
        {activeTab === "rca" && <RcaTab />}
      </main>
    </div>
  );
}
