import React, { useEffect, useState } from "react";
import { api } from "../api";
import { LotRecord, RcaReport } from "../types";
import {
  Search,
  CheckCircle2,
  AlertOctagon,
  ArrowRight,
  ShieldCheck,
  FileSpreadsheet,
  Cpu,
  Info,
  Zap,
  AlertTriangle,
  TrendingDown,
} from "lucide-react";

// ── Likelihood badge ──────────────────────────────────────────
function LikelihoodBadge({ l }: { l: string }) {
  if (l === "high")   return <span className="badge badge-rejected">HIGH LIKELIHOOD</span>;
  if (l === "medium") return <span className="badge badge-review">MEDIUM</span>;
  return                     <span className="badge badge-muted">LOW</span>;
}

export function RcaTab() {
  const [lots,          setLots]          = useState<LotRecord[]>([]);
  const [selectedLotId, setSelectedLotId] = useState<string>("");
  const [customSymptom, setCustomSymptom] = useState<string>("");
  const [loading,       setLoading]       = useState(false);
  const [report,        setReport]        = useState<RcaReport | null>(null);
  const [errorMsg,      setErrorMsg]      = useState<string | null>(null);

  useEffect(() => {
    api
      .getSigmaLots()
      .then((data) => {
        setLots(data);
        if (data.length > 0) setSelectedLotId(data[0].lot_id);
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

      {/* ── Sigma Integration Control Panel ── */}
      <div className="card ">
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon ci-danger">
              <AlertOctagon size={14} color="var(--danger)" />
            </div>
            Root Cause Analysis — Sigma MES 5-Why Engine
          </div>
          <span className="badge badge-red">DEFECT TRACEABILITY</span>
        </div>

        <div className="data-grid data-grid-2" style={{ marginBottom: "1.1rem" }}>
          <div className="form-group">
            <label className="form-label">
              <FileSpreadsheet size={12} color="var(--cyan)" />
              Select Defective Production Lot (MES Feed)
            </label>
            <select
              id="select-lot"
              className="form-select"
              style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
              value={selectedLotId}
              onChange={(e) => setSelectedLotId(e.target.value)}
            >
              {lots.length === 0 && <option value="">— No sigma lots available —</option>}
              {lots.map((lot) => (
                <option key={lot.lot_id} value={lot.lot_id}>
                  {lot.lot_id} · {lot.part_number} · {lot.defect_type || "DEFECT"}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">
              <Cpu size={12} color="var(--blue)" />
              Custom Symptom Description (overrides lot)
            </label>
            <input
              id="input-custom-symptom"
              className="form-input"
              style={{ fontFamily: "var(--font-body)" }}
              placeholder="e.g. Carton bottom staple misalignment > 3mm at ST-04…"
              value={customSymptom}
              onChange={(e) => setCustomSymptom(e.target.value)}
            />
          </div>
        </div>

        <button
          id="btn-investigate"
          className="btn btn-primary btn-lg"
          onClick={handleInvestigate}
          disabled={loading || (!selectedLotId && !customSymptom.trim())}
        >
          {loading ? <div className="spinner" /> : <Search size={16} />}
          {loading ? "Running 5-Why Analysis…" : "Investigate Root Cause"}
        </button>
      </div>

      {/* ── Error ── */}
      {errorMsg && (
        <div className="alert alert-error">
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="card">
          <div className="loading-center">
            <div className="spinner spinner-lg" />
            <span>Running cross-reference analysis against Knowledge Graph &amp; MES logs…</span>
          </div>
        </div>
      )}

      {/* ── RCA Report ── */}
      {!loading && report && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

          {/* Report Header */}
          <div className="card" style={{ background: "var(--status-danger-bg)", border: "1px solid var(--status-danger-border)" }}>
            <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
              <div>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-dim)", letterSpacing: "0.08em", marginBottom: "0.4rem" }}>
                  DEFECT TRACEABILITY REPORT
                </div>
                <h2 style={{ fontFamily: "var(--font-body)", fontSize: "1.35rem", fontWeight: 800, color: "var(--text-pure)", marginBottom: "0.4rem" }}>
                  {report.lot_id ? `LOT: ${report.lot_id}` : "Custom Symptom Analysis"}
                </h2>
                <p style={{ fontSize: "0.875rem", color: "var(--text-medium)", lineHeight: 1.6, maxWidth: 600 }}>
                  <strong style={{ color: "var(--danger)" }}>Symptom:</strong> {report.symptom}
                </p>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", flexShrink: 0 }}>
                <span className="badge badge-rejected" style={{ justifyContent: "center" }}>
                  <TrendingDown size={10} /> DEFECT DETECTED
                </span>
                <span className="badge badge-cyan" style={{ justifyContent: "center" }}>
                  {report.hypotheses.length} HYPOTHESES
                </span>
              </div>
            </div>
          </div>

          {/* Hypotheses */}
          {report.hypotheses.length > 0 && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-danger"><Zap size={14} color="var(--danger)" /></div>
                  Failure Hypotheses
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.65rem" }}>
                {report.hypotheses.map((h, idx) => (
                  <div key={idx} className="hypothesis-card">
                    <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem", marginBottom: "0.5rem" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.55rem", flex: 1 }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-muted)", flexShrink: 0, marginTop: 2 }}>
                          H{idx + 1}
                        </span>
                        <span style={{ fontSize: "0.875rem", color: "var(--text-high)", lineHeight: 1.6 }}>
                          {h.hypothesis}
                        </span>
                      </div>
                      <LikelihoodBadge l={h.likelihood} />
                    </div>
                    {h.evidence_refs.length > 0 && (
                      <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", paddingLeft: "1.3rem" }}>
                        {h.evidence_refs.map((ref, ri) => (
                          <span key={ri} className="mono-tag" style={{ fontSize: "0.62rem" }}>{ref}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5-Why Chain */}
          {report.five_whys.length > 0 && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-cyan"><ArrowRight size={14} color="var(--cyan)" /></div>
                  5-Why Causal Chain
                </div>
                <span className="badge badge-cyan">{report.five_whys.length} STEPS</span>
              </div>
              <div className="why-chain">
                {report.five_whys.map((w) => (
                  <div key={w.order} className="why-step">
                    <div className="why-node">{w.order}</div>
                    <div className="why-content">
                      <div className="why-q">Why #{w.order}</div>
                      <div className="why-a">
                        <strong style={{ color: "var(--text-medium)" }}>Q: </strong>{w.question}
                        <br />
                        <strong style={{ color: "var(--success)" }}>A: </strong>{w.answer}
                        {w.verified && (
                          <span className="badge badge-green" style={{ marginLeft: "0.6rem" }}>
                            <CheckCircle2 size={9} /> VERIFIED
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Preventive Actions */}
          {report.preventive_actions.length > 0 && (
            <div className="card" style={{ border: "1px solid rgba(16,185,129,0.2)" }}>
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-green"><ShieldCheck size={14} color="var(--success)" /></div>
                  Preventive Actions &amp; Countermeasures
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.55rem" }}>
                {report.preventive_actions.map((action, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex", alignItems: "flex-start", gap: "0.75rem",
                      padding: "0.75rem 1rem",
                      background: "var(--status-success-bg)",
                      border: "1px solid var(--status-success-border)",
                      borderRadius: "var(--r-md)",
                    }}
                  >
                    <div style={{
                      width: 22, height: 22, borderRadius: 11,
                      background: "var(--success)", display: "flex",
                      alignItems: "center", justifyContent: "center",
                      flexShrink: 0, marginTop: 1,
                    }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", fontWeight: 700, color: "#fff" }}>
                        {idx + 1}
                      </span>
                    </div>
                    <span style={{ fontSize: "0.875rem", color: "var(--text-high)", lineHeight: 1.6 }}>{action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Related Lots */}
          {report.related_lots.length > 0 && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-warning"><Info size={14} color="var(--warning)" /></div>
                  Related Lots (Pattern Match)
                </div>
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0.45rem" }}>
                {report.related_lots.map((lot, idx) => (
                  <span key={idx} className="mono-tag">{lot}</span>
                ))}
              </div>
            </div>
          )}

          {/* Disclaimer */}
          <div className="alert alert-info">
            <Info size={15} style={{ flexShrink: 0, marginTop: 2 }} />
            <span style={{ fontSize: "0.82rem" }}>{report.disclaimer}</span>
          </div>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && !report && !errorMsg && (
        <div className="card">
          <div className="empty-state">
            <AlertOctagon size={40} />
            <p>Select a sigma defect lot or enter a custom symptom to start the 5-Why root cause analysis.</p>
          </div>
        </div>
      )}
    </div>
  );
}
