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
  Film,
  UserCheck,
  Filter,
  Video,
  Hash,
  RefreshCw,
  Shield,
  Pencil,
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
      setActionMsg({ type: "success", text: `APPROVED: ${updated.profile_id} promoted to VERIFIED KNOWLEDGE — synced to Neo4j Knowledge Graph.` });
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

      {/* ── Filter / Control Bar ── */}
      <div className="card" style={{ padding: "1rem 1.5rem" }}>
        <div className="filter-bar">
          <Filter size={15} color="var(--cyan)" />
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-dim)", letterSpacing: "0.08em" }}>
            LINE:
          </span>
          <select
            id="filter-process"
            className="form-select"
            style={{ width: 220, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}
            value={selectedProcess}
            onChange={(e) => setSelectedProcess(e.target.value)}
          >
            <option value="PACK01">PACK01 - Packaging Line</option>
            <option value="ASSY02">ASSY02 - Assembly Line</option>
          </select>

          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--text-dim)", letterSpacing: "0.08em" }}>
            STATUS:
          </span>
          <select
            id="filter-status"
            className="form-select"
            style={{ width: 220, fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="in_review">In Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>

          <button id="btn-refresh" className="btn btn-ghost btn-sm" onClick={loadProfiles} style={{ marginLeft: "auto" }}>
            <RefreshCw size={13} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Action Message ── */}
      {actionMsg && (
        <div className={`alert alert-${actionMsg.type === "success" ? "success" : actionMsg.type === "warning" ? "warning" : "error"}`}>
          <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* ── Two-Panel Layout ── */}
      <div className="review-layout">

        {/* Left — Profile List */}
        <div className="card " style={{ padding: "1.1rem" }}>
          <div className="card-header" style={{ marginBottom: "0.85rem", paddingBottom: "0.75rem" }}>
            <div className="card-title">
              <div className="card-icon ci-cyan">
                <Hash size={14} color="var(--cyan)" />
              </div>
              Work Profiles
              <span className="badge badge-cyan" style={{ marginLeft: "0.25rem" }}>{profiles.length}</span>
            </div>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-muted)", letterSpacing: "0.08em" }}>
              SELECT TO INSPECT
            </span>
          </div>

          <div className="profile-list scroll-panel" style={{ maxHeight: 720 }}>
            {loading ? (
              <div className="loading-center" style={{ padding: "2rem" }}>
                <div className="spinner" />
                <span>Loading profiles…</span>
              </div>
            ) : profiles.length === 0 ? (
              <div className="empty-state">
                <Hash size={32} />
                <p>No profiles found for the selected filters.</p>
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
                    <div className="profile-step-num">{p.step_order}</div>
                    <div className="profile-info">
                      <div className="profile-step-text">{p.step}</div>
                      <div className="profile-meta">
                        {p.profile_id} · v{p.version} ·{" "}
                        <span style={{ color: p.confidence >= 0.9 ? "var(--success)" : "var(--warning)" }}>
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

        {/* Right — Detail / Audit Console */}
        {selectedProfile ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

            {/* Profile Header Card */}
            <div className="card ">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.45rem", flexWrap: "wrap" }}>
                    <h2 style={{ fontFamily: "var(--font-body)", fontSize: "1.55rem", fontWeight: 800, letterSpacing: "0.03em", color: "var(--text-pure)" }}>
                      {selectedProfile.profile_id}
                    </h2>
                    <span className={statusBadge(selectedProfile.status)}>{selectedProfile.status.replace("_", " ")}</span>
                    <span className="mono-tag">v{selectedProfile.version}</span>
                  </div>
                  <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--text-dim)", letterSpacing: "0.05em" }}>
                    PROCESS: <strong style={{ color: "var(--text-high)" }}>{selectedProfile.process_id}</strong>
                    {" · "} SOURCE: <strong style={{ color: "var(--cyan)" }}>{selectedProfile.generated_by.toUpperCase()}</strong>
                    {" · "} CLASS: <strong style={{ color: "var(--text-medium)" }}>{selectedProfile.data_classification}</strong>
                  </p>
                </div>

                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--text-dim)", letterSpacing: "0.08em", marginBottom: "0.2rem" }}>
                    AI CONFIDENCE
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: "1.5rem", fontWeight: 800, color: selectedProfile.confidence >= 0.9 ? "var(--success)" : "var(--warning)" }}>
                    {(selectedProfile.confidence * 100).toFixed(1)}%
                  </div>
                  <div className="confidence-wrap" style={{ marginTop: "0.35rem" }}>
                    <div className="confidence-track" style={{ width: 100 }}>
                      <div className="confidence-fill" style={{ width: `${selectedProfile.confidence * 100}%` }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Video Keyframe Evidence Panel */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-cyan"><Film size={14} color="var(--cyan)" /></div>
                  Visual Evidence — Camera Viewfinder
                </div>
                <span className="mono-tag">
                  {selectedProfile.evidence.video_id || "VID-PACK01"} · {selectedProfile.evidence.t_start?.toFixed(1)}s–{selectedProfile.evidence.t_end?.toFixed(1)}s
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
                {[
                  { label: "Frame 1 · Initial Entry",  ts: selectedProfile.evidence.t_start?.toFixed(1) + "s" },
                  { label: "Frame 2 · Action Observed", ts: (((selectedProfile.evidence.t_start || 0) + (selectedProfile.evidence.t_end || 5)) / 2).toFixed(1) + "s" },
                  { label: "Frame 3 · Tool Settle", ts: selectedProfile.evidence.t_end?.toFixed(1) + "s" },
                ].map(({ label, ts }) => (
                  <div
                    key={label}
                    style={{
                      background: "var(--bg-input)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--r-md)",
                      height: 100,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "0.4rem",
                      position: "relative",
                      transition: "border-color var(--t-fast)",
                      cursor: "default",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(0,212,255,0.28)")}
                    onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
                  >
                    <Video size={24} color="var(--cyan)" style={{ opacity: 0.6 }} />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.6rem", color: "var(--text-dim)", letterSpacing: "0.06em" }}>
                      {label}
                    </span>
                    <span style={{
                      position: "absolute", bottom: 8, right: 10,
                      fontFamily: "var(--font-mono)", fontSize: "0.62rem",
                      color: "var(--cyan)", background: "var(--cyan-dim)",
                      padding: "0.1rem 0.4rem", borderRadius: 4,
                    }}>
                      {ts}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Editable Fields */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-blue"><Pencil size={14} color="var(--blue)" /></div>
                  Knowledge Field Editor
                </div>
              </div>

              <div className="data-grid data-grid-2">
                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label className="form-label">Step Name (start with verb)</label>
                  <input id="input-step" className="form-input" style={{ fontWeight: 600, fontSize: "1rem" }} value={step} onChange={(e) => setStep(e.target.value)} />
                </div>

                <div className="form-group">
                  <label className="form-label">Hand Action Observed</label>
                  <textarea id="input-hand-action" className="form-textarea" value={handAction} onChange={(e) => setHandAction(e.target.value)} />
                </div>

                <div className="form-group">
                  <label className="form-label">Key Point (Critical Observation)</label>
                  <textarea id="input-key-point" className="form-textarea" value={keyPoint} onChange={(e) => setKeyPoint(e.target.value)} />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Expert Know-How Reason
                    {reason.trim().length > 0 && <span style={{ color: "var(--danger)", marginLeft: "0.5rem" }}>* AC-08</span>}
                  </label>
                  <textarea
                    id="input-reason"
                    className="form-textarea"
                    placeholder="Only from actual expert explanation…"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Reason Source
                    {hasReasonWithoutSource && <span style={{ color: "var(--danger)", marginLeft: "0.5rem" }}>REQUIRED</span>}
                  </label>
                  <select
                    id="select-reason-source"
                    className="form-select"
                    value={reasonSource}
                    onChange={(e) => setReasonSource(e.target.value as ReasonSource)}
                    style={{ borderColor: hasReasonWithoutSource ? "var(--danger)" : undefined, fontFamily: "var(--font-mono)" }}
                  >
                    <option value="">— SELECT SOURCE —</option>
                    <option value="expert_verbal">EXPERT_VERBAL (spoken during task)</option>
                    <option value="expert_interview">EXPERT_INTERVIEW (deep interview)</option>
                  </select>
                </div>

                <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                  <label className="form-label">Pass Criteria (Acceptance Standard)</label>
                  <input id="input-pass-criteria" className="form-input" value={passCriteria} onChange={(e) => setPassCriteria(e.target.value)} />
                </div>
              </div>

              {hasReasonWithoutSource && (
                <div className="alert alert-warning" style={{ marginTop: "1rem" }}>
                  <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                  <span><strong>AC-08 VIOLATION:</strong> reason_source is required when reason is filled. The Approve button is locked.</span>
                </div>
              )}
            </div>

            {/* Human-in-the-Loop Audit Console */}
            <div className="card" >
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon ci-green"><UserCheck size={14} color="var(--success)" /></div>
                  Human-in-the-Loop Audit Console
                </div>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem", color: "var(--success)", letterSpacing: "0.08em" }}>
                  STATION SIGN-OFF
                </span>
              </div>

              <div className="data-grid data-grid-2" style={{ marginBottom: "1.1rem" }}>
                <div className="form-group">
                  <label className="form-label">Reviewer / QA Engineer</label>
                  <input id="input-reviewer" className="form-input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Comment / Rejection Reason (required for reject)</label>
                  <input
                    id="input-review-comment"
                    className="form-input"
                    placeholder="Engineer notes or rejection reason…"
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "1.1rem" }}>
                <div className="section-label">
                  <span className="section-label-text">Error Tagging Matrix</span>
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
                          display: "inline-flex", alignItems: "center",
                          padding: "0.35rem 0.8rem", borderRadius: 20,
                          border: sel ? "1px solid rgba(244,63,94,0.5)" : "1px solid var(--border-subtle)",
                          background: sel ? "var(--danger-dim)" : "var(--bg-glass)",
                          color: sel ? "#fb7185" : "var(--text-dim)",
                          fontFamily: "var(--font-mono)", fontSize: "0.68rem", fontWeight: 700,
                          cursor: "pointer", letterSpacing: "0.06em",
                          transition: "all var(--t-fast)",
                        }}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "0.75rem" }}>
                <button id="btn-approve" className="btn btn-success btn-lg" onClick={handleApprove} disabled={hasReasonWithoutSource}>
                  <CheckCircle size={16} />
                  Approve &amp; Verify
                </button>
                <button id="btn-reject" className="btn btn-danger btn-lg" onClick={handleReject}>
                  <XCircle size={16} />
                  Reject
                </button>
                <button id="btn-save" className="btn btn-primary btn-lg" onClick={handleSavePatch}>
                  <Save size={16} />
                  Save v{selectedProfile.version + 1}
                </button>
              </div>
            </div>
          </div>

        ) : (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 450 }}>
            <div className="empty-state">
              <Shield size={40} />
              <p>Select a work profile from the list to begin the audit inspection.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
