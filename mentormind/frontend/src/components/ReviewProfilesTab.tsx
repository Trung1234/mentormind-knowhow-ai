import React, { useEffect, useState } from "react";
import { api } from "../api";
import {
  ErrorTag,
  ProfilePatchRequest,
  ProfileStatus,
  ReasonSource,
  ReviewRequest,
  WorkProfile,
} from "../types";
import {
  CheckCircle,
  XCircle,
  Save,
  AlertTriangle,
  UserCheck,
  Filter,
  Video,
  RefreshCw,
  Shield,
  Pencil,
  Layers,
  Eye,
  Wrench,
  ShieldCheck,
  FileText,
} from "lucide-react";

// ── Status badge class helper ─────────────────────────────────
function statusBadge(s: ProfileStatus) {
  const map: Record<ProfileStatus, string> = {
    draft:     "badge badge-draft",
    in_review: "badge badge-review",
    approved:  "badge badge-approved",
    rejected:  "badge badge-rejected",
  };
  return map[s] || "badge badge-muted";
}

export function ReviewProfilesTab() {
  const [profiles,        setProfiles]        = useState<WorkProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<WorkProfile | null>(null);
  const [selectedProcess, setSelectedProcess] = useState<string>("PACK01");
  const [selectedStatus,  setSelectedStatus]  = useState<string>("");
  const [loading,         setLoading]         = useState(false);
  const [actionMsg,       setActionMsg]       = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Editable form state
  const [step,         setStep]         = useState("");
  const [handAction,   setHandAction]   = useState("");
  const [keyPoint,     setKeyPoint]     = useState("");
  const [reason,       setReason]       = useState("");
  const [reasonSource, setReasonSource] = useState<ReasonSource | "">("");
  const [passCriteria, setPassCriteria] = useState("");

  // Review state
  const [reviewer,           setReviewer]           = useState("Lead Engineer (DENSO QA)");
  const [reviewComment,      setReviewComment]      = useState("");
  const [selectedErrorTags,  setSelectedErrorTags]  = useState<ErrorTag[]>([]);

  const loadProfiles = async () => {
    setLoading(true);
    try {
      const data = await api.getProfiles(
        selectedProcess || undefined,
        selectedStatus ? (selectedStatus as ProfileStatus) : undefined
      );
      setProfiles(data);
      if (data.length > 0 && (!selectedProfile || !data.some((p) => p.profile_id === selectedProfile.profile_id))) {
        selectProfile(data[0]);
      } else if (data.length === 0) {
        setSelectedProfile(null);
      }
    } catch (err: any) {
      setActionMsg({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadProfiles(); }, [selectedProcess, selectedStatus]);

  const selectProfile = (p: WorkProfile) => {
    setSelectedProfile(p);
    setStep(p.step || "");
    setHandAction(p.hand_action || "");
    setKeyPoint(p.key_point || "");
    setReason(p.reason || "");
    setReasonSource(p.reason_source || "");
    setPassCriteria(p.pass_criteria || "");
    setReviewComment("");
    setSelectedErrorTags([]);
    setActionMsg(null);
  };

  const hasReasonWithoutSource = reason.trim().length > 0 && !reasonSource;

  const handleSavePatch = async () => {
    if (!selectedProfile) return;
    try {
      const patchData: ProfilePatchRequest = {
        step,
        hand_action:   handAction || undefined,
        key_point:     keyPoint || undefined,
        reason:        reason.trim() ? reason : undefined,
        reason_source: reasonSource ? (reasonSource as ReasonSource) : null,
        pass_criteria: passCriteria || undefined,
      };
      const updated = await api.patchProfile(selectedProfile.profile_id, patchData);
      setActionMsg({ type: "success", text: `SAVED: Profile ${updated.profile_id} updated to v${updated.version} — status IN_REVIEW.` });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `WRITE ERROR: ${err.message}` });
    }
  };

  const handleApprove = async () => {
    if (!selectedProfile) return;
    if (hasReasonWithoutSource) {
      setActionMsg({ type: "warning", text: "AC-08 VIOLATION: reason_source must be set before approving." });
      return;
    }
    try {
      const req: ReviewRequest = {
        action:   "approve",
        reviewer: reviewer.trim() || "QA Engineer",
        comment:  reviewComment || "Meets operation standard",
      };
      const updated = await api.reviewProfile(selectedProfile.profile_id, req);
      setActionMsg({ type: "success", text: `APPROVED: ${updated.profile_id} verified & synced to Neo4j Knowledge Graph.` });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `APPROVE FAILED: ${err.message}` });
    }
  };

  const handleReject = async () => {
    if (!selectedProfile) return;
    if (!reviewComment.trim()) {
      setActionMsg({ type: "error", text: "AC-03 REQUIRED: A rejection comment is mandatory." });
      return;
    }
    try {
      const req: ReviewRequest = {
        action:     "reject",
        reviewer:   reviewer.trim() || "QA Engineer",
        comment:    reviewComment.trim(),
        error_tags: selectedErrorTags,
      };
      const updated = await api.reviewProfile(selectedProfile.profile_id, req);
      setActionMsg({ type: "warning", text: `REJECTED: ${updated.profile_id} — status set to REJECTED.` });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `ERROR: ${err.message}` });
    }
  };

  const toggleErrorTag = (tag: ErrorTag) => {
    setSelectedErrorTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const ERROR_TAGS: { id: ErrorTag; label: string }[] = [
    { id: "missed_step",       label: "Missed Step" },
    { id: "hallucinated_step", label: "Hallucinated Step" },
    { id: "wrong_order",       label: "Wrong Order" },
    { id: "wrong_object",      label: "Wrong Object" },
    { id: "wrong_action",      label: "Wrong Action" },
    { id: "other",             label: "Other Defect" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

      {/* ── Production Line Filter Bar ── */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon ci-red">
              <Filter size={14} />
            </div>
            Line Inspection Filter
          </div>
          <span className="badge badge-red">DENSO PACK01 // ST-04</span>
        </div>
        <div className="filter-bar">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Process Line:
            </span>
            <select
              id="filter-process"
              className="form-select"
              style={{ width: 220, fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value)}
            >
              <option value="PACK01">PACK01 — Packaging Line</option>
              <option value="ASSY02">ASSY02 — Assembly Line</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontFamily: "var(--font-display)", fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Status:
            </span>
            <select
              id="filter-status"
              className="form-select"
              style={{ width: 180, fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="in_review">In Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          <button id="btn-refresh" className="btn btn-ghost btn-sm" onClick={loadProfiles} style={{ marginLeft: "auto" }}>
            <RefreshCw size={13} />
            Refresh Queue
          </button>
        </div>
      </div>

      {/* ── Action Notification Message ── */}
      {actionMsg && (
        <div className={`alert alert-${actionMsg.type === "success" ? "success" : actionMsg.type === "warning" ? "warning" : "error"}`}>
          <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* ── Two-Panel Industrial Layout ── */}
      <div className="review-layout">

        {/* Left Column — Sticky Profile List */}
        <div className="card profile-sidebar-card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon ci-cyan">
                <Layers size={14} />
              </div>
              Work Profiles
              <span className="badge badge-cyan" style={{ marginLeft: "0.3rem" }}>{profiles.length}</span>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-muted)", letterSpacing: "0.06em" }}>
              QUEUE
            </span>
          </div>

          <div className="profile-list" style={{ maxHeight: "calc(100vh - 250px)" }}>
            {loading ? (
              <div className="loading-center">
                <div className="spinner" />
                <span>Reading Station DB…</span>
              </div>
            ) : profiles.length === 0 ? (
              <div className="empty-state">
                <FileText size={32} />
                <p>No profiles match current filter criteria.</p>
              </div>
            ) : (
              profiles.map((p) => {
                const isSel = selectedProfile?.profile_id === p.profile_id;
                return (
                  <div
                    key={p.profile_id}
                    className={`profile-item ${isSel ? "selected" : ""}`}
                    onClick={() => selectProfile(p)}
                  >
                    <div className="profile-step-num">0{p.step_order}</div>
                    <div className="profile-info">
                      <div className="profile-step-text">{p.step}</div>
                      <div className="profile-meta">
                        {p.profile_id} · v{p.version} ·{" "}
                        <span style={{ color: p.confidence >= 0.9 ? "var(--status-success)" : "var(--status-warning)", fontWeight: 600 }}>
                          {(p.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <span className={statusBadge(p.status)}>{p.status.replace("_", " ")}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column — Detail Inspection & Sign-off Console */}
        {selectedProfile ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

            {/* Profile Overview & Telemetry Banner */}
            <div className="card">
              <div className="card-body" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.45rem", flexWrap: "wrap" }}>
                    <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.45rem", fontWeight: 700, color: "var(--text-pure)", letterSpacing: "0.02em" }}>
                      {selectedProfile.profile_id}
                    </h2>
                    <span className={statusBadge(selectedProfile.status)}>{selectedProfile.status.replace("_", " ")}</span>
                    <span className="mono-tag">v{selectedProfile.version}.0</span>
                  </div>
                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.74rem", color: "var(--text-muted)", letterSpacing: "0.03em" }}>
                    PROCESS: <strong style={{ color: "var(--text-pure)" }}>{selectedProfile.process_id}</strong>
                    {" · "} PIPELINE: <strong style={{ color: "var(--accent-cyan)" }}>{selectedProfile.generated_by.toUpperCase()}</strong>
                    {" · "} CLASSIFICATION: <strong style={{ color: "var(--text-secondary)" }}>{selectedProfile.data_classification}</strong>
                  </p>
                </div>

                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "0.68rem", fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: "0.2rem" }}>
                    Vision AI Confidence
                  </div>
                  <div style={{ fontFamily: "var(--font-display)", fontSize: "1.45rem", fontWeight: 700, color: selectedProfile.confidence >= 0.9 ? "var(--status-success)" : "var(--status-warning)" }}>
                    {(selectedProfile.confidence * 100).toFixed(1)}%
                  </div>
                  <div className="confidence-wrap" style={{ marginTop: "0.25rem" }}>
                    <div className="confidence-track" style={{ width: 110 }}>
                      <div className="confidence-fill" style={{ width: `${selectedProfile.confidence * 100}%` }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Visual Evidence — 3-Frame Machine Vision Viewfinder */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-cyan">
                    <Video size={14} />
                  </div>
                  Visual Evidence — Machine Vision CCTV
                </div>
                <span className="mono-tag">
                  FEED: {selectedProfile.evidence.video_id || "CAM-01-PACK"} · {selectedProfile.evidence.t_start?.toFixed(1)}s – {selectedProfile.evidence.t_end?.toFixed(1)}s
                </span>
              </div>

              <div className="cctv-grid">
                {[
                  { label: "FRAME 1 // ENTRY",  ts: selectedProfile.evidence.t_start?.toFixed(1) + "s" },
                  { label: "FRAME 2 // ACTION", ts: (((selectedProfile.evidence.t_start || 0) + (selectedProfile.evidence.t_end || 5)) / 2).toFixed(1) + "s" },
                  { label: "FRAME 3 // SETTLE", ts: selectedProfile.evidence.t_end?.toFixed(1) + "s" },
                ].map(({ label, ts }) => (
                  <div key={label} className="cctv-frame">
                    <div className="cctv-rec-badge">
                      <span className="cctv-rec-dot" />
                      REC
                    </div>
                    <div className="cctv-crosshair" />
                    <span className="cctv-label">{label}</span>
                    <span className="cctv-timestamp">{ts}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Knowledge Field Editor */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-red">
                    <Wrench size={14} />
                  </div>
                  Operational Know-How Editor
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.65rem", color: "var(--text-muted)" }}>
                  STANDARD SPEC 08
                </span>
              </div>

              <div className="card-body">
                <div className="data-grid data-grid-2">
                  <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                    <label className="form-label">
                      <Pencil size={12} color="var(--denso-red)" />
                      Step Action Name (Must start with active verb)
                    </label>
                    <input
                      id="input-step"
                      className="form-input"
                      style={{ fontWeight: 600, fontSize: "0.95rem" }}
                      value={step}
                      onChange={(e) => setStep(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <Eye size={12} color="var(--accent-cyan)" />
                      Hand Action Observed
                    </label>
                    <textarea
                      id="input-hand-action"
                      className="form-textarea"
                      value={handAction}
                      onChange={(e) => setHandAction(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      <AlertTriangle size={12} color="var(--status-warning)" />
                      Key Point / Critical Observation
                    </label>
                    <textarea
                      id="input-key-point"
                      className="form-textarea"
                      value={keyPoint}
                      onChange={(e) => setKeyPoint(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      Expert Know-How Reason
                      {reason.trim().length > 0 && <span style={{ color: "var(--status-danger)", marginLeft: "0.35rem" }}>* AC-08</span>}
                    </label>
                    <textarea
                      id="input-reason"
                      className="form-textarea"
                      placeholder="Explicit rationale from expert operator…"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">
                      Reason Source Classification
                      {hasReasonWithoutSource && <span style={{ color: "var(--status-danger)", marginLeft: "0.35rem" }}>* MANDATORY</span>}
                    </label>
                    <select
                      id="select-reason-source"
                      className="form-select"
                      value={reasonSource}
                      onChange={(e) => setReasonSource(e.target.value as ReasonSource)}
                      style={{ borderColor: hasReasonWithoutSource ? "var(--status-danger)" : undefined, fontFamily: "var(--font-mono)" }}
                    >
                      <option value="">— SELECT SOURCE —</option>
                      <option value="expert_verbal">EXPERT_VERBAL (Recorded during run)</option>
                      <option value="expert_interview">EXPERT_INTERVIEW (Structured post-shift Q&amp;A)</option>
                    </select>
                  </div>

                  <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                    <label className="form-label">
                      <CheckCircle size={12} color="var(--status-success)" />
                      Pass Criteria &amp; Acceptance Standard
                    </label>
                    <input
                      id="input-pass-criteria"
                      className="form-input"
                      value={passCriteria}
                      onChange={(e) => setPassCriteria(e.target.value)}
                    />
                  </div>
                </div>

                {hasReasonWithoutSource && (
                  <div className="alert alert-warning" style={{ marginTop: "1rem" }}>
                    <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                    <span><strong>AC-08 RULE:</strong> A valid Reason Source is mandatory when Reason is filled. Approval is locked until selected.</span>
                  </div>
                )}
              </div>
            </div>

            {/* QA Verification & Station Sign-Off Console */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-green">
                    <ShieldCheck size={14} />
                  </div>
                  QA Verification &amp; Station Sign-Off
                </div>
                <span className="badge badge-green">STATION SIGN-OFF</span>
              </div>

              <div className="card-body">
                <div className="data-grid data-grid-2" style={{ marginBottom: "1.1rem" }}>
                  <div className="form-group">
                    <label className="form-label">
                      <UserCheck size={12} />
                      Lead Reviewer / QA Engineer
                    </label>
                    <input
                      id="input-reviewer"
                      className="form-input"
                      value={reviewer}
                      onChange={(e) => setReviewer(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">
                      Review Comment / Audit Notes
                    </label>
                    <input
                      id="input-review-comment"
                      className="form-input"
                      placeholder="Engineer notes or rejection cause…"
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: "1.25rem" }}>
                  <div className="section-label">
                    <span className="section-label-text">Defect &amp; Error Tagging Matrix</span>
                  </div>
                  <div className="chip-list">
                    {ERROR_TAGS.map(({ id, label }) => {
                      const sel = selectedErrorTags.includes(id);
                      return (
                        <button
                          key={id}
                          type="button"
                          onClick={() => toggleErrorTag(id)}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.4rem",
                            padding: "0.38rem 0.85rem",
                            borderRadius: "var(--r-xs)",
                            border: sel ? "1px solid var(--status-danger)" : "1px solid var(--border-tech)",
                            background: sel ? "var(--status-danger-bg)" : "var(--bg-surface)",
                            color: sel ? "var(--status-danger-text)" : "var(--text-secondary)",
                            fontFamily: "var(--font-display)",
                            fontSize: "0.78rem",
                            fontWeight: 700,
                            cursor: "pointer",
                            letterSpacing: "0.04em",
                            textTransform: "uppercase",
                            transition: "all 120ms ease",
                          }}
                        >
                          {sel ? "✓" : "+"} {label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr", gap: "0.85rem" }}>
                  <button id="btn-approve" className="btn btn-success btn-lg" onClick={handleApprove} disabled={hasReasonWithoutSource}>
                    <CheckCircle size={16} />
                    Approve &amp; Verify
                  </button>
                  <button id="btn-reject" className="btn btn-danger btn-lg" onClick={handleReject}>
                    <XCircle size={16} />
                    Reject Step
                  </button>
                  <button id="btn-save" className="btn btn-primary btn-lg" onClick={handleSavePatch}>
                    <Save size={16} />
                    Save Draft v{selectedProfile.version + 1}
                  </button>
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 450 }}>
            <div className="empty-state">
              <Shield size={44} />
              <p>Select an operational profile from the queue to start the verification audit.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
