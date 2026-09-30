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
  ShieldCheck,
  Video,
  CornerDownRight,
  Hash,
} from "lucide-react";

export function ReviewProfilesTab() {
  const [profiles, setProfiles] = useState<WorkProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<WorkProfile | null>(null);
  const [selectedProcess, setSelectedProcess] = useState<string>("PACK01");
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Form edit state for selected profile
  const [step, setStep] = useState("");
  const [handAction, setHandAction] = useState("");
  const [keyPoint, setKeyPoint] = useState("");
  const [reason, setReason] = useState("");
  const [reasonSource, setReasonSource] = useState<ReasonSource | "">("");
  const [passCriteria, setPassCriteria] = useState("");

  // Review state
  const [reviewer, setReviewer] = useState("Kỹ sư Trưởng (DENSO QA)");
  const [reviewComment, setReviewComment] = useState("");
  const [selectedErrorTags, setSelectedErrorTags] = useState<ErrorTag[]>([]);

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

  useEffect(() => {
    loadProfiles();
  }, [selectedProcess, selectedStatus]);

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

  // AC-08: Nếu có nhập reason mà không chọn reason_source -> nút Duyệt bị vô hiệu
  const hasReasonWithoutSource = reason.trim().length > 0 && !reasonSource;

  const handleSavePatch = async () => {
    if (!selectedProfile) return;
    try {
      const patchData: ProfilePatchRequest = {
        step,
        hand_action: handAction || undefined,
        key_point: keyPoint || undefined,
        reason: reason.trim() ? reason : undefined,
        reason_source: reasonSource ? (reasonSource as ReasonSource) : null,
        pass_criteria: passCriteria || undefined,
      };
      const updated = await api.patchProfile(selectedProfile.profile_id, patchData);
      setActionMsg({
        type: "success",
        text: `ĐÃ LƯU THÀNH CÔNG: Hồ sơ ${updated.profile_id} đã cập nhật lên phiên bản v${updated.version} (Trạng thái: IN_REVIEW).`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `LỖI GHI DỮ LIỆU: ${err.message}` });
    }
  };

  const handleApprove = async () => {
    if (!selectedProfile) return;
    if (hasReasonWithoutSource) {
      setActionMsg({
        type: "warning",
        text: "VI PHẠM QUY ĐỊNH AC-08: Phải chọn Nguồn lý do (expert_verbal / expert_interview) trước khi duyệt!",
      });
      return;
    }
    try {
      const req: ReviewRequest = {
        action: "approve",
        reviewer: reviewer.trim() || "Chuyên gia kiểm duyệt",
        comment: reviewComment || "Đạt chuẩn thao tác",
      };
      const updated = await api.reviewProfile(selectedProfile.profile_id, req);
      setActionMsg({
        type: "success",
        text: `ĐÃ PHÊ DUYỆT THÀNH CÔNG: Hồ sơ ${updated.profile_id} đã chuyển thành VERIFIED KNOWLEDGE và đồng bộ vào Neo4j Knowledge Graph.`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `TỪ CHỐI DUYỆT: ${err.message}` });
    }
  };

  const handleReject = async () => {
    if (!selectedProfile) return;
    if (!reviewComment.trim()) {
      setActionMsg({
        type: "error",
        text: "YÊU CẦU BẮT BUỘC AC-03: Từ chối hồ sơ bắt buộc phải nhập lý do cụ thể vào ô Nhận xét/Lý do từ chối!",
      });
      return;
    }
    try {
      const req: ReviewRequest = {
        action: "reject",
        reviewer: reviewer.trim() || "Chuyên gia kiểm duyệt",
        comment: reviewComment.trim(),
        error_tags: selectedErrorTags,
      };
      const updated = await api.reviewProfile(selectedProfile.profile_id, req);
      setActionMsg({
        type: "warning",
        text: `ĐÃ TỪ CHỐI HỒ SƠ: ${updated.profile_id} đã chuyển trạng thái REJECTED.`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `LỖI: ${err.message}` });
    }
  };

  const toggleErrorTag = (tag: ErrorTag) => {
    if (selectedErrorTags.includes(tag)) {
      setSelectedErrorTags(selectedErrorTags.filter((t) => t !== tag));
    } else {
      setSelectedErrorTags([...selectedErrorTags, tag]);
    }
  };

  const ERROR_TAG_OPTIONS: { id: ErrorTag; label: string }[] = [
    { id: "missed_step", label: "[E1] BỎ SÓT BƯỚC" },
    { id: "hallucinated_step", label: "[E2] BỊA BƯỚC (HALLUCINATION)" },
    { id: "wrong_order", label: "[E3] SAI THỨ TỰ THAO TÁC" },
    { id: "wrong_object", label: "[E4] SAI VẬT THỂ / DỤNG CỤ" },
    { id: "wrong_action", label: "[E5] SAI HƯỚNG / LỰC MIẾT" },
    { id: "other", label: "[E6] LỖI KHÁC" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.75rem" }}>
      {/* Precision Filter HUD */}
      <div className="card" style={{ padding: "1.1rem 1.75rem", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Filter size={18} color="#06b6d4" />
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "0.95rem", color: "#94a3b8" }}>
              CÔNG ĐOẠN (LINE):
            </span>
            <select
              className="form-select"
              style={{ width: "200px", minHeight: "44px", fontFamily: "var(--font-mono)", fontWeight: 600 }}
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value)}
            >
              <option value="PACK01">PACK01 // ĐÓNG GÓI</option>
              <option value="ASSY02">ASSY02 // LẮP RÁP</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: "0.95rem", color: "#94a3b8" }}>
              TRẠNG THÁI:
            </span>
            <select
              className="form-select"
              style={{ width: "200px", minHeight: "44px", fontFamily: "var(--font-mono)", fontWeight: 600 }}
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="">-- TẤT CẢ TRẠNG THÁI --</option>
              <option value="draft">BẢN NHÁP (DRAFT)</option>
              <option value="in_review">ĐANG DUYỆT (IN_REVIEW)</option>
              <option value="approved">ĐÃ DUYỆT (APPROVED)</option>
              <option value="rejected">TỪ CHỐI (REJECTED)</option>
            </select>
          </div>
        </div>

        <button className="btn btn-secondary" onClick={loadProfiles} style={{ minHeight: "44px" }}>
          LÀM MỚI DANH SÁCH
        </button>
      </div>

      {actionMsg && (
        <div className={`alert-box alert-${actionMsg.type}`}>
          <AlertTriangle size={24} style={{ flexShrink: 0 }} />
          <span style={{ fontWeight: 600 }}>{actionMsg.text}</span>
        </div>
      )}

      {/* Main Inspection Grid */}
      <div className="grid-2">
        {/* Left Column: Tactical Profile Selector */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "0.75rem", marginBottom: "1rem" }}>
            <h2 className="card-title" style={{ fontSize: "1.1rem", marginBottom: 0 }}>
              <Hash size={18} color="#06b6d4" />
              <span>HỒ SƠ THAO TÁC ({profiles.length})</span>
            </h2>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#94a3b8" }}>SELECT TO AUDIT</span>
          </div>

          {loading ? (
            <p style={{ color: "#94a3b8", padding: "1.5rem", textAlign: "center", fontFamily: "var(--font-mono)" }}>
              ĐANG ĐỐI SOÁT CƠ SỞ DỮ LIỆU...
            </p>
          ) : profiles.length === 0 ? (
            <p style={{ color: "#94a3b8", padding: "1.5rem", textAlign: "center" }}>
              Không tìm thấy hồ sơ thao tác nào.
            </p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", maxHeight: "780px", overflowY: "auto", paddingRight: "4px" }}>
              {profiles.map((p) => {
                const isSelected = selectedProfile?.profile_id === p.profile_id;
                return (
                  <div
                    key={p.profile_id}
                    onClick={() => selectProfile(p)}
                    style={{
                      padding: "1rem 1.15rem",
                      borderRadius: "4px",
                      background: isSelected ? "rgba(6, 182, 212, 0.12)" : "#0b101c",
                      border: isSelected ? "1px solid #06b6d4" : "1px solid #1e293b",
                      borderLeft: isSelected ? "4px solid #06b6d4" : "4px solid transparent",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                      transition: "all 0.15s ease",
                      position: "relative",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "0.95rem", color: isSelected ? "#38bdf8" : "#cbd5e1" }}>
                        {p.profile_id} <span style={{ opacity: 0.6, fontSize: "0.8rem" }}>v{p.version}</span>
                      </span>
                      <span className={`badge badge-${p.status}`}>{p.status}</span>
                    </div>

                    <div style={{ fontWeight: 600, fontSize: "0.975rem", color: "#f8fafc", lineHeight: 1.4 }}>
                      [BƯỚC {p.step_order}] {p.step}
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.8rem", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                      <span>TIMELINE: {p.evidence.t_start?.toFixed(1)}s - {p.evidence.t_end?.toFixed(1)}s</span>
                      <span style={{ color: p.confidence >= 0.9 ? "#10b981" : "#f59e0b" }}>CONF: {(p.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: High-End Inspection Console */}
        {selectedProfile ? (
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Header Telemetry */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #334155", paddingBottom: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.85rem", marginBottom: "0.45rem" }}>
                  <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.6rem", fontWeight: 800, letterSpacing: "0.03em" }}>
                    {selectedProfile.profile_id}
                  </h2>
                  <span className={`badge badge-${selectedProfile.status}`}>{selectedProfile.status}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem", color: "#06b6d4", background: "rgba(6,182,212,0.1)", padding: "0.2rem 0.5rem", borderRadius: "3px" }}>
                    REVISION v{selectedProfile.version}
                  </span>
                </div>
                <p style={{ color: "#94a3b8", fontSize: "0.9rem", fontFamily: "var(--font-mono)" }}>
                  PROCESS: <strong style={{ color: "#f8fafc" }}>{selectedProfile.process_id}</strong> · PROVENANCE: <strong style={{ color: "#38bdf8" }}>{selectedProfile.generated_by.toUpperCase()}</strong> · CLASSIFICATION: <strong style={{ color: "#f8fafc" }}>{selectedProfile.data_classification}</strong>
                </p>
              </div>

              <div style={{ textAlign: "right" }}>
                <span style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#94a3b8" }}>ĐỘ TIN CẬY THUẬT TOÁN</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "1.25rem", fontWeight: 800, color: "#10b981" }}>
                  {(selectedProfile.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Viewfinder & Video Keyframe Telemetry */}
            <div>
              <label className="form-label" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <Film size={18} color="#06b6d4" />
                  <span>BẰNG CHỨNG THỊ GIÁC (CAMERA VIEWFINDER — {selectedProfile.evidence.t_start?.toFixed(1)}s - {selectedProfile.evidence.t_end?.toFixed(1)}s)</span>
                </span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", color: "#38bdf8" }}>
                  CLIP: {selectedProfile.evidence.video_id || "VID-PACK01"}
                </span>
              </label>

              <div className="keyframe-gallery">
                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.4rem" }}>
                    <Video size={32} color="#06b6d4" />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>FRAME 01 // ENTRY</span>
                  </div>
                  <span className="timestamp-badge">{selectedProfile.evidence.t_start?.toFixed(1)}s</span>
                </div>

                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.4rem" }}>
                    <Video size={32} color="#06b6d4" />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>FRAME 02 // ACTION</span>
                  </div>
                  <span className="timestamp-badge">{(((selectedProfile.evidence.t_start || 0) + (selectedProfile.evidence.t_end || 5)) / 2).toFixed(1)}s</span>
                </div>

                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.4rem" }}>
                    <Video size={32} color="#06b6d4" />
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>FRAME 03 // SETTLE</span>
                  </div>
                  <span className="timestamp-badge">{selectedProfile.evidence.t_end?.toFixed(1)}s</span>
                </div>
              </div>
            </div>

            {/* Editable Inspection Fields */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">TÊN BƯỚC THAO TÁC (ĐỘNG TỪ Ở ĐẦU)</label>
                <input className="form-input" style={{ fontWeight: 600, fontSize: "1.05rem" }} value={step} onChange={(e) => setStep(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">THAO TÁC TAY QUAN SÁT ĐƯỢC (HAND ACTION)</label>
                <textarea className="form-textarea" value={handAction} onChange={(e) => setHandAction(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">ĐIỂM THEN CHỐT QUAN SÁT (KEY POINT)</label>
                <textarea className="form-textarea" value={keyPoint} onChange={(e) => setKeyPoint(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">
                  LÝ DO ĐẰNG SAU THAO TÁC (REASON — BÍ QUYẾT CHUYÊN GIA)
                </label>
                <textarea
                  className="form-textarea"
                  placeholder="Chỉ điền từ lời giải thích thực tế của chuyên gia..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  NGUỒN LÝ DO (REASON SOURCE)
                  {reason.trim().length > 0 && <span style={{ color: "#f43f5e" }}> * BẮT BUỘC THEO AC-08</span>}
                </label>
                <select
                  className="form-select"
                  value={reasonSource}
                  onChange={(e) => setReasonSource(e.target.value as ReasonSource)}
                  style={{ borderColor: hasReasonWithoutSource ? "#f43f5e" : undefined, fontFamily: "var(--font-mono)" }}
                >
                  <option value="">-- CHƯA CHỌN NGUỒN --</option>
                  <option value="expert_verbal">LỜI NÓI KHI THAO TÁC (EXPERT_VERBAL)</option>
                  <option value="expert_interview">PHỎNG VẤN CHUYÊN SÂU (EXPERT_INTERVIEW)</option>
                </select>
              </div>

              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">TIÊU CHUẨN NGHIỆM THU (PASS CRITERIA)</label>
                <input className="form-input" value={passCriteria} onChange={(e) => setPassCriteria(e.target.value)} />
              </div>
            </div>

            {/* AC-08 Tactical Alert */}
            {hasReasonWithoutSource && (
              <div className="alert-box alert-warning">
                <AlertTriangle size={24} style={{ flexShrink: 0 }} />
                <span>
                  <strong>CẢNH BÁO VI PHẠM AC-08:</strong> Đã nhập nội dung ô Lý do nhưng chưa chọn Nguồn lý do (reason_source). Nút Duyệt thao tác bị khóa theo quy chuẩn Constitution Điều 3!
                </span>
              </div>
            )}

            {/* Tactile Review Audit Console */}
            <div style={{ background: "#0a0e1a", border: "1px solid #334155", borderRadius: "4px", padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.05rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <UserCheck size={18} color="#10b981" />
                  <span>THẨM ĐỊNH CHẤT LƯỢNG (HUMAN-IN-THE-LOOP AUDIT)</span>
                </h3>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "#10b981" }}>STATION SIGN-OFF</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
                <div>
                  <label className="form-label">KỸ SƯ KIỂM DUYỆT (REVIEWER)</label>
                  <input className="form-input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
                </div>
                <div>
                  <label className="form-label">NHẬN XÉT / LÝ DO TỪ CHỐI (BẮT BUỘC KHI REJECT)</label>
                  <input
                    className="form-input"
                    placeholder="Ghi chú ý kiến chuyên gia hoặc lý do từ chối..."
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "1.25rem" }}>
                <label className="form-label">GẮN NHÃN LỖI PHÁT HIỆN (ERROR TAGGING MATRIX)</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {ERROR_TAG_OPTIONS.map((tag) => {
                    const isSelected = selectedErrorTags.includes(tag.id);
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleErrorTag(tag.id)}
                        style={{
                          padding: "0.45rem 0.85rem",
                          borderRadius: "4px",
                          border: isSelected ? "1px solid #f43f5e" : "1px solid #334155",
                          background: isSelected ? "rgba(244, 63, 94, 0.2)" : "#131a2c",
                          color: isSelected ? "#fca5a5" : "#94a3b8",
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.8rem",
                          fontWeight: 600,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        {tag.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "1rem" }}>
                <button
                  className="btn btn-success"
                  onClick={handleApprove}
                  disabled={hasReasonWithoutSource}
                >
                  <CheckCircle size={20} />
                  <span>DUYỆT THAO TÁC (APPROVE)</span>
                </button>

                <button
                  className="btn btn-danger"
                  onClick={handleReject}
                >
                  <XCircle size={20} />
                  <span>TỪ CHỐI (REJECT)</span>
                </button>

                <button
                  className="btn btn-primary"
                  onClick={handleSavePatch}
                >
                  <Save size={20} />
                  <span>LƯU SỬA (v{selectedProfile.version + 1})</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "450px" }}>
            <p style={{ color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
              CHỌN MỘT HỒ SƠ TỪ DANH SÁCH BÊN TRÁI ĐỂ TIẾN HÀNH THẨM ĐỊNH
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
