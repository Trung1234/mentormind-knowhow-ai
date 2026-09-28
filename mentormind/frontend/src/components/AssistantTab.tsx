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
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Top Controls Card */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
          <Sparkles size={24} color="#3b82f6" />
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Trợ lý Know-How Nhà Máy (AI Assistant)</h2>
        </div>

        <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem" }}>
          <label style={{ fontWeight: 600, color: "#94a3b8" }}>Công đoạn:</label>
          <select
            className="form-select"
            style={{ width: "220px" }}
            value={processId}
            onChange={(e) => setProcessId(e.target.value)}
          >
            <option value="PACK01">PACK01 (Đóng gói thành phẩm)</option>
            <option value="ASSY02">ASSY02 (Lắp ráp cơ điện tử)</option>
          </select>
        </div>

        {/* Suggestion Chips */}
        <div style={{ marginBottom: "1rem" }}>
          <span style={{ fontSize: "0.85rem", color: "#94a3b8", display: "block", marginBottom: "0.4rem" }}>
            Câu hỏi gợi ý thường gặp:
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuestion(q);
                  handleAsk(q);
                }}
                style={{
                  background: "#0f172a",
                  border: "1px solid #334155",
                  color: "#cbd5e1",
                  borderRadius: "20px",
                  padding: "0.4rem 0.9rem",
                  fontSize: "0.875rem",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                }}
              >
                <HelpCircle size={14} color="#60a5fa" />
                <span>{q}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Box */}
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <textarea
            className="form-textarea"
            style={{ flex: 1, minHeight: "60px" }}
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
            style={{ padding: "0 1.5rem" }}
          >
            <Send size={20} />
            <span>Gửi câu hỏi</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="alert-box alert-danger">
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Answer Section */}
      {loading ? (
        <div className="card" style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
          Đang tra cứu cơ sở tri thức (GraphRAG & SOP tài liệu)...
        </div>
      ) : answer ? (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          {answer.refused ? (
            <div className="alert-box alert-warning" style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "0.5rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700 }}>
                <AlertCircle size={20} />
                <span>Cần chuyển tiếp chuyên gia (Refused by Guardrail)</span>
              </div>
              <p>{answer.answer}</p>
              {answer.suggested_expert && (
                <div style={{ marginTop: "0.5rem", padding: "0.5rem 0.8rem", background: "rgba(0,0,0,0.2)", borderRadius: "6px" }}>
                  Chuyên gia gợi ý liên hệ: <strong>{answer.suggested_expert}</strong>
                </div>
              )}
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <MessageSquare size={20} color="#10b981" />
                <h3 style={{ fontSize: "1.15rem", fontWeight: 700 }}>Câu trả lời được chứng thực:</h3>
              </div>

              <div
                style={{
                  fontSize: "1.05rem",
                  lineHeight: "1.7",
                  background: "#0f172a",
                  padding: "1.25rem",
                  borderRadius: "8px",
                  border: "1px solid #334155",
                  marginBottom: "1rem",
                }}
              >
                {answer.answer}
              </div>

              {/* Citations List */}
              {answer.citations.length > 0 && (
                <div>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 600, color: "#94a3b8", marginBottom: "0.5rem" }}>
                    Căn cứ & Trích dẫn nguồn (Citations):
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
                    {answer.citations.map((c, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setSelectedCitation(c)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          background: selectedCitation === c ? "rgba(59, 130, 246, 0.2)" : "#1e293b",
                          border: selectedCitation === c ? "1px solid #3b82f6" : "1px solid #334155",
                          borderRadius: "8px",
                          padding: "0.6rem 1rem",
                          color: "#f8fafc",
                          cursor: "pointer",
                        }}
                      >
                        {c.source_type === "video" ? <Video size={16} color="#60a5fa" /> : <FileText size={16} color="#f59e0b" />}
                        <span style={{ fontWeight: 600 }}>[{idx + 1}]</span>
                        <span>{c.title || c.ref_id}</span>
                        {c.t_start !== undefined && (
                          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                            ({c.t_start}s - {c.t_end}s)
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Citation Detail Preview */}
              {selectedCitation && (
                <div
                  style={{
                    marginTop: "1.25rem",
                    padding: "1.25rem",
                    background: "#0f172a",
                    border: "1px solid #3b82f6",
                    borderRadius: "8px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, color: "#60a5fa" }}>
                      {selectedCitation.source_type === "video" ? <Video size={18} /> : <FileText size={18} />}
                      <span>Chi tiết căn cứ: {selectedCitation.title || selectedCitation.ref_id}</span>
                    </div>
                  </div>

                  {selectedCitation.excerpt && (
                    <blockquote style={{ borderLeft: "3px solid #3b82f6", paddingLeft: "1rem", fontStyle: "italic", color: "#cbd5e1" }}>
                      "{selectedCitation.excerpt}"
                    </blockquote>
                  )}

                  {selectedCitation.t_start !== undefined && (
                    <div style={{ marginTop: "0.75rem", fontSize: "0.9rem", color: "#94a3b8" }}>
                      Thời lượng trích xuất từ video: <strong>{selectedCitation.t_start}s</strong> đến <strong>{selectedCitation.t_end}s</strong>.
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
