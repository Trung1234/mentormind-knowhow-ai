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
        return <span className="badge" style={{ background: "#4c0519", color: "#f43f5e", border: "1px solid #e11d48" }}>Cao (High)</span>;
      case "medium":
        return <span className="badge" style={{ background: "#451a03", color: "#f59e0b", border: "1px solid #b45309" }}>Trung bình</span>;
      default:
        return <span className="badge" style={{ background: "#1e293b", color: "#94a3b8", border: "1px solid #475569" }}>Thấp (Low)</span>;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Control Card */}
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
          <AlertOctagon size={24} color="#f43f5e" />
          <h2 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Truy Nguyên Nguyên Nhân Gốc Rễ (RCA & 5-Why)</h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
          <div>
            <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <FileSpreadsheet size={16} color="#3b82f6" />
              <span>Chọn lô sản xuất lỗi (Dữ liệu từ Sigma MES):</span>
            </label>
            <select
              className="form-select"
              value={selectedLotId}
              onChange={(e) => setSelectedLotId(e.target.value)}
            >
              <option value="">-- Nhập triệu chứng tùy ý --</option>
              {lots.map((l) => (
                <option key={l.lot_id} value={l.lot_id}>
                  {l.lot_id} · {l.part_number} · [{l.status}] {l.defect_type ? `- ${l.defect_type}` : ""}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="form-label">Mô tả triệu chứng bổ sung (Tùy chọn):</label>
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
          style={{ width: "100%", maxWidth: "320px" }}
        >
          <Search size={20} />
          <span>{loading ? "Đang suy luận RCA..." : "Khởi chạy điều tra RCA"}</span>
        </button>
      </div>

      {errorMsg && (
        <div className="alert-box alert-danger">
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Investigation Results */}
      {report && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Header Summary */}
          <div className="card" style={{ background: "#0f172a", border: "1px solid #334155" }}>
            <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem" }}>
              <div>
                <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Lô được phân tích:</span>
                <div style={{ fontSize: "1.2rem", fontWeight: 800, color: "#60a5fa" }}>
                  {report.lot_id || "Khảo sát theo triệu chứng"}
                </div>
              </div>
              <div>
                <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Triệu chứng phát hiện:</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "#f8fafc" }}>
                  {report.symptom}
                </div>
              </div>
            </div>
          </div>

          {/* Hypotheses Table */}
          <div className="card">
            <h3 className="card-title">
              <Layers size={20} color="#f59e0b" />
              <span>Bảng Giả thuyết Nguyên nhân (Hypotheses)</span>
            </h3>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #334155", color: "#94a3b8", fontSize: "0.9rem" }}>
                    <th style={{ padding: "0.75rem 1rem" }}>Khả năng xảy ra</th>
                    <th style={{ padding: "0.75rem 1rem" }}>Giả thuyết kỹ thuật</th>
                    <th style={{ padding: "0.75rem 1rem" }}>Căn cứ dữ liệu đối soát</th>
                  </tr>
                </thead>
                <tbody>
                  {report.hypotheses.map((h, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                      <td style={{ padding: "0.85rem 1rem" }}>{getLikelihoodBadge(h.likelihood)}</td>
                      <td style={{ padding: "0.85rem 1rem", fontWeight: 600 }}>{h.hypothesis}</td>
                      <td style={{ padding: "0.85rem 1rem", color: "#94a3b8", fontSize: "0.9rem" }}>
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
              <ArrowRight size={20} color="#3b82f6" />
              <span>Chuỗi Phân Tích 5-Why (Root Cause Chain)</span>
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              {report.five_whys.map((step) => (
                <div
                  key={step.order}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "1rem",
                    padding: "1rem",
                    borderRadius: "8px",
                    background: "#0f172a",
                    border: "1px solid #334155",
                  }}
                >
                  <div
                    style={{
                      background: "#1e293b",
                      border: "1px solid #3b82f6",
                      borderRadius: "50%",
                      width: "36px",
                      height: "36px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 800,
                      color: "#60a5fa",
                      flexShrink: 0,
                    }}
                  >
                    W{step.order}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#cbd5e1", marginBottom: "0.25rem" }}>
                      {step.question}
                    </div>
                    <div style={{ color: "#f8fafc", fontSize: "1rem" }}>{step.answer}</div>
                  </div>
                  {step.verified && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        color: "#10b981",
                        fontSize: "0.85rem",
                        fontWeight: 600,
                      }}
                    >
                      <CheckCircle2 size={16} />
                      <span>Đã xác minh</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Preventive Actions & Lots */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
            <div className="card">
              <h3 className="card-title" style={{ fontSize: "1.1rem" }}>
                <ShieldCheck size={20} color="#10b981" />
                <span>Biện pháp phòng ngừa (Preventive Actions)</span>
              </h3>
              <ul style={{ paddingLeft: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {report.preventive_actions.map((act, i) => (
                  <li key={i} style={{ color: "#f8fafc" }}>{act}</li>
                ))}
              </ul>
            </div>

            <div className="card">
              <h3 className="card-title" style={{ fontSize: "1.1rem" }}>
                <span>Các lô có nguy cơ tương tự (Related Lots)</span>
              </h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                {report.related_lots.map((lot, i) => (
                  <span
                    key={i}
                    style={{
                      background: "#0f172a",
                      border: "1px solid #f43f5e",
                      color: "#fca5a5",
                      padding: "0.4rem 0.8rem",
                      borderRadius: "6px",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.9rem",
                    }}
                  >
                    {lot}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div style={{ padding: "0.75rem 1rem", background: "#111827", borderRadius: "8px", border: "1px solid #334155", color: "#94a3b8", fontSize: "0.85rem", textAlign: "center" }}>
            {report.disclaimer}
          </div>
        </div>
      )}
    </div>
  );
}
