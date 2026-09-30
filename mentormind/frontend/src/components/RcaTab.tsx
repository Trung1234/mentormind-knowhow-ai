import React, { useEffect, useState } from "react";
import { api } from "../api";
import { LotRecord, RcaReport } from "../types";
import {
  Search,
  CheckCircle2,
  AlertOctagon,
  Layers,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
  Cpu,
  Info,
} from "lucide-react";

export function RcaTab() {
  const [lots, setLots] = useState<LotRecord[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<string>("");
  const [customSymptom, setCustomSymptom] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<RcaReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSigmaLots()
      .then((data) => {
        setLots(data);
        if (data.length > 0) {
          setSelectedLotId(data[0].lot_id);
        }
      })
      .catch((err) => console.error(err));
  }, []);

  const handleInvestigate = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.investigateRca(selectedLotId || undefined, customSymptom || undefined);
      setReport(res);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getLikelihoodBadge = (likelihood: string) => {
    switch (likelihood) {
      case "high":
        return <span className="badge" style={{ background: "rgba(244,63,94,0.15)", color: "#fb7185", border: "1px solid #e11d48" }}>XÁC SUẤT CAO [HIGH]</span>;
      case "medium":
        return <span className="badge" style={{ background: "rgba(245,158,11,0.15)", color: "#fbbf24", border: "1px solid #d97706" }}>TRUNG BÌNH [MED]</span>;
      default:
        return <span className="badge" style={{ background: "rgba(100,116,139,0.15)", color: "#94a3b8", border: "1px solid #475569" }}>THẤP [LOW]</span>;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* MES Sigma Integration Control */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem", borderBottom: "1px solid #334155", paddingBottom: "0.75rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <AlertOctagon size={24} color="#f43f5e" />
            <h2 className="card-title" style={{ marginBottom: 0 }}>
              TRUY NGUYÊN NGUYÊN NHÂN GỐC RỄ (SIGMA MES RCA & 5-WHY)
            </h2>
          </div>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#f43f5e", background: "rgba(244,63,94,0.1)", padding: "0.2rem 0.6rem", borderRadius: "3px" }}>
            DEFECT TRACEABILITY SYSTEM
          </span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
          <div>
            <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <FileSpreadsheet size={16} color="#06b6d4" />
              <span>CHỌN LÔ SẢN XUẤT PHÁT SINH LỖI (MES FEED):</span>
            </label>
            <select
              className="form-select"
              style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}
              value={selectedLotId}
              onChange={(e) => setSelectedLotId(e.target.value)}
            >
              <option value="">-- NHẬP TRIỆU CHỨNG TÙY BIẾN --</option>
              {lots.map((l) => (
                <option key={l.lot_id} value={l.lot_id}>
                  {l.lot_id} // {l.part_number} // [{l.status}] {l.defect_type ? `- ${l.defect_type}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">MÔ TẢ TRIỆU CHỨNG LỖI QUAN SÁT (SYMPTOM OVERRIDE):</label>
            <input
              className="form-input"
              placeholder="Ví dụ: Nắp hộp bị lệch mép >2mm, rách gập mép..."
              value={customSymptom}
              onChange={(e) => setCustomSymptom(e.target.value)}
            />
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={handleInvestigate}
          disabled={loading || (!selectedLotId && !customSymptom)}
          style={{ width: "100%", maxWidth: "340px" }}
        >
          <Search size={20} />
          <span>{loading ? "ĐANG TỔNG HỢP NGUYÊN NHÂN..." : "KHỞI CHẠY ĐIỀU TRA RCA"}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="alert-box alert-danger">
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Investigation Dashboard */}
      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
          {/* Header Summary HUD */}
          <div className="card" style={{ background: "#080c14", border: "1px solid #334155", borderLeft: "4px solid #06b6d4" }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "#94a3b8" }}>MÃ LÔ ĐƯỢC PHÂN TÍCH:</span>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.4rem", fontWeight: 800, color: "#38bdf8" }}>
                  {report.lot_id || "TRIỆU CHỨNG THỦ CÔNG"}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "#94a3b8" }}>TRIỆU CHỨNG PHÁT HIỆN:</span>
                <div style={{ fontFamily: "var(--font-display)", fontSize: "1.2rem", fontWeight: 700, color: "#f8fafc" }}>
                  {report.symptom}
                </div>
              </div>
            </div>
          </div>

          {/* Hypotheses Matrix */}
          <div className="card">
            <h3 className="card-title">
              <Layers size={22} color="#f59e0b" />
              <span>MA TRẬN GIẢ THUYẾT NGUYÊN NHÂN (HYPOTHESES MATRIX)</span>
            </h3>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #334155", color: "#94a3b8", fontFamily: "var(--font-display)", fontSize: "0.95rem" }}>
                    <th style={{ padding: "0.9rem 1.2rem", width: "220px" }}>MỨC ĐỘ XÁC SUẤT</th>
                    <th style={{ padding: "0.9rem 1.2rem" }}>GIẢ THUYẾT KỸ THUẬT</th>
                    <th style={{ padding: "0.9rem 1.2rem", width: "300px" }}>CĂN CỨ ĐỐI SOÁT</th>
                  </tr>
                </thead>
                <tbody>
                  {report.hypotheses.map((h, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent" }}>
                      <td style={{ padding: "1rem 1.2rem" }}>{getLikelihoodBadge(h.likelihood)}</td>
                      <td style={{ padding: "1rem 1.2rem", fontWeight: 600, fontSize: "1.05rem" }}>{h.hypothesis}</td>
                      <td style={{ padding: "1rem 1.2rem", color: "#06b6d4", fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>
                        {h.evidence_refs.join(", ") || "Chưa có bằng chứng trực tiếp"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* 5-Why Analysis Chain */}
          <div className="card">
            <h3 className="card-title">
              <ArrowRight size={22} color="#06b6d4" />
              <span>CHUỖI PHÂN TÍCH 5-WHY (ROOT CAUSE TELEMETRY CHAIN)</span>
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
              {report.five_whys.map((step) => (
                <div
                  key={step.order}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "1.25rem",
                    padding: "1.2rem",
                    borderRadius: "4px",
                    background: "#080c14",
                    border: "1px solid #1e293b",
                    borderLeft: "4px solid #06b6d4",
                  }}
                >
                  <div
                    style={{
                      background: "#151d30",
                      border: "1px solid #06b6d4",
                      borderRadius: "4px",
                      width: "42px",
                      height: "42px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: "var(--font-mono)",
                      fontWeight: 800,
                      fontSize: "1.1rem",
                      color: "#38bdf8",
                      flexShrink: 0,
                    }}
                  >
                    W{step.order}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, color: "#94a3b8", fontSize: "0.95rem", marginBottom: "0.35rem" }}>
                      [WHY {step.order}]: {step.question}
                    </div>
                    <div style={{ color: "#f8fafc", fontSize: "1.05rem", lineHeight: "1.5" }}>{step.answer}</div>
                  </div>
                  {step.verified && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        color: "#10b981",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.85rem",
                        fontWeight: 700,
                        background: "rgba(16,185,129,0.1)",
                        padding: "0.3rem 0.6rem",
                        borderRadius: "3px",
                      }}
                    >
                      <CheckCircle2 size={16} />
                      <span>VERIFIED</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Preventive Roadmap & Related Lots */}
          <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "1.75rem" }}>
            <div className="card">
              <h3 className="card-title" style={{ fontSize: "1.15rem" }}>
                <ShieldCheck size={22} color="#10b981" />
                <span>BIỆN PHÁP PHÒNG NGỪA (PREVENTIVE ACTIONS)</span>
              </h3>
              <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {report.preventive_actions.map((act, i) => (
                  <li key={i} style={{ color: "#f8fafc", fontSize: "1.025rem", lineHeight: "1.6" }}>{act}</li>
                ))}
              </ul>
            </div>

            <div className="card">
              <h3 className="card-title" style={{ fontSize: "1.15rem" }}>
                <span>CÁC LÔ CÙNG NGUY CƠ (AFFECTED LOTS)</span>
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem" }}>
                {report.related_lots.map((lot, i) => (
                  <span
                    key={i}
                    style={{
                      background: "rgba(244, 63, 94, 0.12)",
                      border: "1px solid #f43f5e",
                      color: "#fca5a5",
                      padding: "0.5rem 0.9rem",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.95rem",
                      fontWeight: 700,
                    }}
                  >
                    {lot}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Official Disclaimer */}
          <div style={{ padding: "0.9rem 1.25rem", background: "#0a0e1a", borderRadius: "4px", border: "1px solid #334155", color: "#94a3b8", fontSize: "0.9rem", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.5rem" }}>
            <Info size={16} color="#94a3b8" />
            <span>{report.disclaimer}</span>
          </div>
        </div>
      )}
    </div>
  );
}
