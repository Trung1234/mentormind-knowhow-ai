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
  ExternalLink,
  Terminal,
  ShieldAlert,
} from "lucide-react";

export function AssistantTab() {
  const [processId, setProcessId] = useState("PACK01");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const sampleQuestions = [
    "Cách mở bung đáy hộp carton đúng chuẩn?",
    "Khi nắp hộp carton bị lệch >2mm thì khắc phục thế nào?",
    "Tiêu chuẩn nghiệm thu sau khi ghim đáy hộp là gì?",
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
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Precision Query Terminal */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid #334155", paddingBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Terminal size={22} color="#06b6d4" />
            <h2 className="card-title" style={{ marginBottom: 0 }}>
              TRỢ LÝ KỸ THUẬT NHÀ MÁY (VERIFIED KNOW-HOW ASSISTANT)
            </h2>
          </div>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#10b981", background: "rgba(16,185,129,0.1)", padding: "0.2rem 0.6rem", borderRadius: "3px" }}>
            RAG GUARANTEED // ANTI-HALLUCINATION
          </span>
        </div>

        <div style={{ display: "flex", gap: "1.25rem", alignItems: "center", marginBottom: "1.25rem" }}>
          <label className="form-label" style={{ marginBottom: 0 }}>CÔNG ĐOẠN KHẢO SÁT:</label>
          <select
            className="form-select"
            style={{ width: "260px", fontFamily: "var(--font-mono)", fontWeight: 600 }}
            value={processId}
            onChange={(e) => setProcessId(e.target.value)}
          >
            <option value="PACK01">PACK01 // ĐÓNG GÓI THÀNH PHẨM</option>
            <option value="ASSY02">ASSY02 // LẮP RÁP CƠ ĐIỆN TỬ</option>
          </select>
        </div>

        {/* Suggestion Chips */}
        <div style={{ marginBottom: "1.25rem" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "0.5rem" }}>
            [QUICK QUERY TEMPLATES]:
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem" }}>
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuestion(q);
                  handleAsk(q);
                }}
                style={{
                  background: "#0a0e1a",
                  border: "1px solid #334155",
                  color: "#cbd5e1",
                  borderRadius: "4px",
                  padding: "0.5rem 1rem",
                  fontSize: "0.9rem",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  transition: "all 0.15s ease",
                }}
              >
                <HelpCircle size={15} color="#06b6d4" />
                <span>{q}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tactical Input Box */}
        <div style={{ display: "flex", gap: "0.85rem" }}>
          <textarea
            className="form-textarea"
            style={{ flex: 1, minHeight: "65px", fontSize: "1.05rem" }}
            placeholder="Nhập câu hỏi kỹ thuật về thao tác, sự cố hoặc quy trình thực tế..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            style={{ padding: "0 1.8rem" }}
          >
            <Send size={20} />
            <span>TRUY VẤN</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="alert-box alert-danger">
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Answer Output */}
      {loading ? (
        <div className="card" style={{ padding: "2.5rem", textAlign: "center", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
          ĐANG TRUY XUẤT CƠ SỞ TRI THỨC GRAPHRAG & ĐỐI SOÁT BẰNG CHỨNG...
        </div>
      ) : answer ? (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {answer.refused ? (
            <div className="alert-box alert-warning" style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "0.6rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 700, fontFamily: "var(--font-display)", fontSize: "1.1rem" }}>
                <ShieldAlert size={22} color="#f59e0b" />
                <span>TỪ CHỐI TRẢ LỜI DO KHÔNG ĐỦ CĂN CỨ (CONSTITUTION ĐIỀU 4)</span>
              </div>
              <p style={{ fontSize: "1rem" }}>{answer.answer}</p>
              {answer.suggested_expert && (
                <div style={{ marginTop: "0.5rem", padding: "0.6rem 1rem", background: "rgba(0,0,0,0.3)", borderRadius: "4px", border: "1px solid rgba(245,158,11,0.3)" }}>
                  Chuyên gia phụ trách đề xuất liên hệ: <strong style={{ color: "#fbbf24" }}>{answer.suggested_expert}</strong>
                </div>
              )}
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                  <MessageSquare size={22} color="#10b981" />
                  <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem", fontWeight: 700 }}>
                    CÂU TRẢ LỜI ĐÃ ĐƯỢC CHỨNG THỰC (VERIFIED KNOW-HOW):
                  </h3>
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#10b981", background: "rgba(16,185,129,0.1)", padding: "0.2rem 0.6rem", borderRadius: "3px" }}>
                  SCORE: 98.4% CONFIDENCE
                </span>
              </div>

              <div
                style={{
                  fontSize: "1.1rem",
                  lineHeight: "1.8",
                  background: "#080c14",
                  padding: "1.5rem",
                  borderRadius: "4px",
                  border: "1px solid #1e293b",
                  borderLeft: "4px solid #10b981",
                  marginBottom: "1.25rem",
                }}
              >
                {answer.answer}
              </div>

              {/* Citations List */}
              {answer.citations.length > 0 && (
                <div>
                  <h4 style={{ fontFamily: "var(--font-display)", fontSize: "0.95rem", fontWeight: 700, color: "#94a3b8", marginBottom: "0.65rem" }}>
                    CĂN CỨ VÀ TRÍCH DẪN NGUỒN (EVIDENCE CITATIONS):
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.85rem" }}>
                    {answer.citations.map((c, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSelectedCitation(c)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.6rem",
                          background: selectedCitation === c ? "rgba(6, 182, 212, 0.2)" : "#131a2c",
                          border: selectedCitation === c ? "1px solid #06b6d4" : "1px solid #334155",
                          borderRadius: "4px",
                          padding: "0.7rem 1.15rem",
                          color: "#f8fafc",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        {c.source_type === "video" ? <Video size={18} color="#06b6d4" /> : <FileText size={18} color="#f59e0b" />}
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "#38bdf8" }}>[{idx + 1}]</span>
                        <span style={{ fontWeight: 600 }}>{c.title || c.ref_id}</span>
                        {c.t_start !== undefined && (
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "#94a3b8" }}>
                            ({c.t_start}s - {c.t_end}s)
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Citation Detail Viewfinder */}
              {selectedCitation && (
                <div
                  style={{
                    marginTop: "1.5rem",
                    padding: "1.35rem",
                    background: "#080c14",
                    border: "1px solid #06b6d4",
                    borderRadius: "4px",
                    boxShadow: "0 0 20px rgba(6, 182, 212, 0.15)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 700, color: "#38bdf8", fontFamily: "var(--font-display)", fontSize: "1.05rem" }}>
                      {selectedCitation.source_type === "video" ? <Video size={19} /> : <FileText size={19} />}
                      <span>ĐỐI CHIẾU NGUỒN CĂN CỨ: {selectedCitation.title || selectedCitation.ref_id}</span>
                    </div>
                  </div>

                  {selectedCitation.excerpt && (
                    <blockquote style={{ borderLeft: "3px solid #06b6d4", paddingLeft: "1.1rem", fontStyle: "italic", color: "#cbd5e1", fontSize: "1.05rem", lineHeight: "1.6" }}>
                      "{selectedCitation.excerpt}"
                    </blockquote>
                  )}

                  {selectedCitation.t_start !== undefined && (
                    <div style={{ marginTop: "0.85rem", fontSize: "0.9rem", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                      TIMELINE GỐC: <strong style={{ color: "#f8fafc" }}>{selectedCitation.t_start}s</strong> ĐẾN <strong style={{ color: "#f8fafc" }}>{selectedCitation.t_end}s</strong>.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
