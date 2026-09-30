import React, { useState } from "react";
import { api } from "../api";
import { AssistantAnswer, Citation } from "../types";
import {
  MessageSquare,
  Send,
  HelpCircle,
  FileText,
  Video,
  AlertCircle,
  Sparkles,
  Terminal,
  ShieldAlert,
  Bot,
  ExternalLink,
} from "lucide-react";

export function AssistantTab() {
  const [processId,        setProcessId]        = useState("PACK01");
  const [question,         setQuestion]         = useState("");
  const [loading,          setLoading]          = useState(false);
  const [answer,           setAnswer]           = useState<AssistantAnswer | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [errorMsg,         setErrorMsg]         = useState<string | null>(null);

  const sampleQuestions = [
    "How to properly open the bottom of a carton box?",
    "What to do when the carton lid is misaligned by >2mm?",
    "What is the acceptance standard after stapling the box bottom?",
  ];

  const handleAsk = async (qText?: string) => {
    const q = qText || question;
    if (!q.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    setSelectedCitation(null);
    try {
      const res = await api.askAssistant(processId, q);
      setAnswer(res);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

      {/* ── Query Terminal Card ── */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon ci-cyan">
              <Terminal size={14} color="var(--cyan)" />
            </div>
            Verified Know-How Assistant
          </div>
          <span className="badge badge-green">RAG Verified</span>
        </div>

        <div className="card-body">
        {/* Process selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.1rem" }}>
          <label className="form-label" style={{ whiteSpace: "nowrap", marginBottom: 0 }}>
            Process Line:
          </label>
          <select
            id="select-process-assistant"
            className="form-select"
            style={{ width: 280, fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
            value={processId}
            onChange={(e) => setProcessId(e.target.value)}
          >
            <option value="PACK01">PACK01 - Packaging Line</option>
            <option value="ASSY02">ASSY02 - Assembly Line</option>
          </select>
        </div>

        {/* Quick question chips */}
        <div style={{ marginBottom: "1.1rem" }}>
          <div className="section-label">
            <span className="section-label-text">Quick query templates</span>
          </div>
          <div className="chip-list">
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                className="chip"
                onClick={() => { setQuestion(q); handleAsk(q); }}
              >
                <HelpCircle size={12} />
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Input + Send */}
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Your technical query</label>
            <textarea
              id="input-question"
              className="form-textarea"
              style={{ minHeight: 72, fontSize: "0.95rem" }}
              placeholder="Ask about operations, defects, or process standards… (Shift+Enter for newline)"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); }
              }}
            />
          </div>
          <button
            id="btn-ask"
            className="btn btn-primary btn-lg"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            style={{ flexShrink: 0, marginBottom: 2 }}
          >
            {loading ? <div className="spinner" /> : <Send size={16} />}
            {loading ? "Analyzing…" : "Ask Copilot"}
          </button>
        </div>
        </div>
      </div>

      {/* ── Error ── */}
      {errorMsg && (
        <div className="alert alert-error">
          <AlertCircle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="card">
          <div className="loading-center">
            <div className="spinner spinner-lg" />
            <span>Searching GraphRAG knowledge base &amp; verifying evidence…</span>
          </div>
        </div>
      )}

      {/* ── Answer ── */}
      {!loading && answer && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

          {answer.refused ? (
            /* Refusal Panel */
            <div className="alert alert-warning" style={{ flexDirection: "column", alignItems: "flex-start", gap: "0.65rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", fontWeight: 700, fontFamily: "var(--font-body)", fontSize: "1rem" }}>
                <ShieldAlert size={18} color="var(--warning)" />
                Insufficient Evidence — Response Refused (Constitution Article 4)
              </div>
              <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>{answer.answer}</p>
              {answer.suggested_expert && (
                <div style={{ padding: "0.55rem 0.9rem", background: "var(--bg-subtle)", borderRadius: "var(--r-sm)", border: "1px solid var(--border-medium)", fontSize: "0.85rem" }}>
                  Suggested expert to contact: <strong style={{ color: "#fbbf24" }}>{answer.suggested_expert}</strong>
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Answer bubble */}
              <div>
                <div className="chat-bubble-header">
                  <Bot size={13} color="var(--success)" />
                  <span style={{ color: "var(--success)" }}>Verified Know-How Response</span>
                  <span className="badge badge-green" style={{ marginLeft: "auto" }}>
                    <Sparkles size={9} /> KNOWLEDGE VERIFIED
                  </span>
                </div>
                <div className="chat-bubble" style={{ borderLeft: "3px solid var(--success)" }}>
                  {answer.answer}
                </div>
              </div>

              {/* Citations */}
              {answer.citations.length > 0 && (
                <div>
                  <div className="section-label">
                    <span className="section-label-text">Evidence Citations ({answer.citations.length})</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.65rem" }}>
                    {answer.citations.map((c, idx) => (
                      <div
                        key={idx}
                        className={`citation-card ${selectedCitation === c ? "active" : ""}`}
                        onClick={() => setSelectedCitation(selectedCitation === c ? null : c)}
                      >
                        <div style={{
                          width: 28, height: 28, borderRadius: "var(--r-sm)",
                          background: c.source_type === "video" ? "var(--cyan-dim)" : "var(--warning-dim)",
                          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                        }}>
                          {c.source_type === "video"
                            ? <Video size={13} color="var(--cyan)" />
                            : <FileText size={13} color="var(--warning)" />
                          }
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--cyan)", marginBottom: "0.2rem" }}>
                            [{idx + 1}] {c.source_type.toUpperCase()}
                          </div>
                          <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--text-high)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {c.title || c.ref_id}
                          </div>
                          {c.t_start !== undefined && (
                            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-dim)", marginTop: "0.18rem" }}>
                              {c.t_start}s – {c.t_end}s
                            </div>
                          )}
                        </div>
                        <ExternalLink size={12} color="var(--text-muted)" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Citation Detail */}
              {selectedCitation && (
                <div style={{
                  background: "var(--bg-input)",
                  border: "1px solid rgba(0,212,255,0.3)",
                  borderRadius: "var(--r-md)",
                  padding: "1.25rem",
                  boxShadow: "0 0 24px rgba(0,212,255,0.08)",
                  animation: "alert-in 0.25s ease",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.9rem" }}>
                    {selectedCitation.source_type === "video"
                      ? <Video size={16} color="var(--cyan)" />
                      : <FileText size={16} color="var(--warning)" />
                    }
                    <span style={{ fontFamily: "var(--font-body)", fontWeight: 700, fontSize: "0.9rem", color: "var(--text-high)" }}>
                      Source: {selectedCitation.title || selectedCitation.ref_id}
                    </span>
                    <span className="badge badge-cyan" style={{ marginLeft: "auto" }}>
                      {selectedCitation.source_type}
                    </span>
                  </div>

                  {selectedCitation.excerpt && (
                    <blockquote style={{
                      borderLeft: "3px solid var(--cyan)",
                      paddingLeft: "1rem",
                      fontStyle: "italic",
                      color: "var(--text-medium)",
                      fontSize: "0.9rem",
                      lineHeight: 1.7,
                      marginBottom: "0.75rem",
                    }}>
                      "{selectedCitation.excerpt}"
                    </blockquote>
                  )}

                  {selectedCitation.t_start !== undefined && (
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-dim)", letterSpacing: "0.05em" }}>
                      TIMELINE:{" "}
                      <strong style={{ color: "var(--text-high)" }}>{selectedCitation.t_start}s</strong>
                      {" → "}
                      <strong style={{ color: "var(--text-high)" }}>{selectedCitation.t_end}s</strong>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── Empty prompt state ── */}
      {!loading && !answer && !errorMsg && (
        <div className="card">
          <div className="empty-state">
            <MessageSquare size={40} />
            <p>Ask a technical question to retrieve verified factory know-how from the knowledge graph.</p>
          </div>
        </div>
      )}
    </div>
  );
}
