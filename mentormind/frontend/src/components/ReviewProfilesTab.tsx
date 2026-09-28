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
  ChevronRight,
  Filter,
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
        text: `Đã lưu cập nhật cho ${updated.profile_id}. Phiên bản tăng lên v${updated.version} (trạng thái: Đang duyệt).`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `Lỗi khi lưu: ${err.message}` });
    }
  };

  const handleApprove = async () => {
    if (!selectedProfile) return;
    if (hasReasonWithoutSource) {
      setActionMsg({
        type: "warning",
        text: "AC-08: Bắt buộc chọn Nguồn lý do (expert_verbal / expert_interview) trước khi duyệt!",
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
        text: `Đã DUYỆT thành công hồ sơ ${updated.profile_id}! Dữ liệu đã đồng bộ vào Knowledge Graph.`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `Không thể duyệt: ${err.message}` });
    }
  };

  const handleReject = async () => {
    if (!selectedProfile) return;
    if (!reviewComment.trim()) {
      setActionMsg({
        type: "error",
        text: "AC-03: Từ chối bắt buộc phải nhập lý do cụ thể vào ô Nhận xét/Lý do từ chối!",
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
        text: `Đã TỪ CHỐI hồ sơ ${updated.profile_id}. Trạng thái đã chuyển thành Rejected.`,
      });
      selectProfile(updated);
      loadProfiles();
    } catch (err: any) {
      setActionMsg({ type: "error", text: `Lỗi: ${err.message}` });
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
    { id: "missed_step", label: "Bỏ sót bước" },
    { id: "hallucinated_step", label: "Bịa bước (Hallucination)" },
    { id: "wrong_order", label: "Sai thứ tự" },
    { id: "wrong_object", label: "Sai vật thể/dụng cụ" },
    { id: "wrong_action", label: "Sai thao tác tay" },
    { id: "other", label: "Lỗi khác" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Filter Header */}
      <div className="card" style={{ padding: "1rem 1.5rem", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Filter size={18} color="#94a3b8" />
            <span style={{ fontWeight: 600, color: "#94a3b8" }}>Công đoạn:</span>
            <select
              className="form-select"
              style={{ width: "160px", minHeight: "42px", padding: "0.4rem 0.8rem" }}
              value={selectedProcess}
              onChange={(e) => setSelectedProcess(e.target.value)}
            >
              <option value="PACK01">PACK01 (Đóng gói)</option>
              <option value="ASSY02">ASSY02 (Lắp ráp)</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontWeight: 600, color: "#94a3b8" }}>Trạng thái:</span>
            <select
              className="form-select"
              style={{ width: "160px", minHeight: "42px", padding: "0.4rem 0.8rem" }}
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
            >
              <option value="">Tất cả trạng thái</option>
              <option value="draft">Bản nháp (draft)</option>
              <option value="in_review">Đang duyệt (in_review)</option>
              <option value="approved">Đã duyệt (approved)</option>
              <option value="rejected">Bị từ chối (rejected)</option>
            </select>
          </div>
        </div>

        <button className="btn btn-secondary" onClick={loadProfiles} style={{ minHeight: "42px" }}>
          Làm mới danh sách
        </button>
      </div>

      {actionMsg && (
        <div className={`alert-box alert-${actionMsg.type}`}>
          <AlertTriangle size={20} />
          <span>{actionMsg.text}</span>
        </div>
      )}

      {/* Main Grid: Left List + Right Detail */}
      <div className="grid-2">
        {/* Left Column: Profile Selector */}
        <div className="card" style={{ padding: "1rem" }}>
          <h2 className="card-title" style={{ fontSize: "1.1rem", padding: "0.5rem" }}>
            Danh sách thao tác ({profiles.length})
          </h2>

          {loading ? (
            <p style={{ color: "#94a3b8", padding: "1rem" }}>Đang tải danh sách...</p>
          ) : profiles.length === 0 ? (
            <p style={{ color: "#94a3b8", padding: "1rem" }}>Không tìm thấy hồ sơ nào phù hợp.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", maxHeight: "720px", overflowY: "auto" }}>
              {profiles.map((p) => {
                const isSelected = selectedProfile?.profile_id === p.profile_id;
                return (
                  <div
                    key={p.profile_id}
                    onClick={() => selectProfile(p)}
                    style={{
                      padding: "0.85rem 1rem",
                      borderRadius: "8px",
                      background: isSelected ? "rgba(59, 130, 246, 0.15)" : "#0f172a",
                      border: isSelected ? "1px solid #3b82f6" : "1px solid #334155",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.4rem",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "0.9rem", color: "#60a5fa" }}>
                        {p.profile_id} (v{p.version})
                      </span>
                      <span className={`badge badge-${p.status}`}>{p.status}</span>
                    </div>
                    <div style={{ fontWeight: 600, fontSize: "0.95rem", color: "#f8fafc" }}>
                      Bước {p.step_order}: {p.step}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                      Thời gian: {p.evidence.t_start?.toFixed(1)}s - {p.evidence.t_end?.toFixed(1)}s · Độ tin cậy: {(p.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Detailed Review & Inspection */}
        {selectedProfile ? (
          <div className="card" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #334155", paddingBottom: "1rem" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.35rem" }}>
                  <h2 style={{ fontSize: "1.4rem", fontWeight: 800 }}>{selectedProfile.profile_id}</h2>
                  <span className={`badge badge-${selectedProfile.status}`}>{selectedProfile.status}</span>
                  <span style={{ fontSize: "0.9rem", color: "#94a3b8" }}>Phiên bản {selectedProfile.version}</span>
                </div>
                <p style={{ color: "#94a3b8", fontSize: "0.9rem" }}>
                  Công đoạn: <strong>{selectedProfile.process_id}</strong> · Nguồn sinh: <strong>{selectedProfile.generated_by.toUpperCase()}</strong> · Phân loại: <strong>{selectedProfile.data_classification}</strong>
                </p>
              </div>
            </div>

            {/* Evidence & Keyframes */}
            <div>
              <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Film size={18} color="#60a5fa" />
                <span>Bằng chứng hình ảnh & Keyframes ({selectedProfile.evidence.t_start?.toFixed(1)}s - {selectedProfile.evidence.t_end?.toFixed(1)}s)</span>
              </label>
              <div className="keyframe-gallery">
                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.3rem" }}>
                    <Film size={28} />
                    <span style={{ fontSize: "0.8rem" }}>Đoạn clip {selectedProfile.evidence.video_id}</span>
                  </div>
                  <span className="timestamp-badge">{selectedProfile.evidence.t_start?.toFixed(1)}s</span>
                </div>
                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.3rem" }}>
                    <Film size={28} />
                    <span style={{ fontSize: "0.8rem" }}>Keyframe Giữa</span>
                  </div>
                  <span className="timestamp-badge">{(((selectedProfile.evidence.t_start || 0) + (selectedProfile.evidence.t_end || 5)) / 2).toFixed(1)}s</span>
                </div>
                <div className="keyframe-box">
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#94a3b8", gap: "0.3rem" }}>
                    <Film size={28} />
                    <span style={{ fontSize: "0.8rem" }}>Keyframe Kết thúc</span>
                  </div>
                  <span className="timestamp-badge">{selectedProfile.evidence.t_end?.toFixed(1)}s</span>
                </div>
              </div>
            </div>

            {/* Editable Fields */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Tên bước thao tác (Bắt đầu bằng động từ)</label>
                <input className="form-input" value={step} onChange={(e) => setStep(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Thao tác tay quan sát được (Hand action)</label>
                <textarea className="form-textarea" value={handAction} onChange={(e) => setHandAction(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Điểm then chốt (Key point)</label>
                <textarea className="form-textarea" value={keyPoint} onChange={(e) => setKeyPoint(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Lý do đằng sau thao tác (Reason - Bí quyết chuyên gia)</label>
                <textarea
                  className="form-textarea"
                  placeholder="Chỉ điền từ lời giải thích thực tế của chuyên gia..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  Nguồn lý do (Reason source)
                  {reason.trim().length > 0 && <span style={{ color: "#ef4444" }}> * Bắt buộc khi có Reason</span>}
                </label>
                <select
                  className="form-select"
                  value={reasonSource}
                  onChange={(e) => setReasonSource(e.target.value as ReasonSource)}
                  style={{ borderColor: hasReasonWithoutSource ? "#ef4444" : undefined }}
                >
                  <option value="">-- Chưa chọn nguồn --</option>
                  <option value="expert_verbal">Lời nói khi thao tác (expert_verbal)</option>
                  <option value="expert_interview">Phỏng vấn chuyên sâu (expert_interview)</option>
                </select>
              </div>

              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Tiêu chuẩn nghiệm thu (Pass criteria)</label>
                <input className="form-input" value={passCriteria} onChange={(e) => setPassCriteria(e.target.value)} />
              </div>
            </div>

            {/* Validation warning for AC-08 */}
            {hasReasonWithoutSource && (
              <div className="alert-box alert-warning">
                <AlertTriangle size={20} />
                <span><strong>Lưu ý quy định AC-08:</strong> Đã nhập nội dung ô Lý do nhưng chưa chọn Nguồn lý do. Nút Duyệt sẽ tạm thời bị khóa!</span>
              </div>
            )}

            {/* Rejection / Review section */}
            <div style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: "8px", padding: "1rem" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "0.75rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <UserCheck size={18} color="#10b981" />
                <span>Khu vực Thẩm định & Duyệt (Human-in-the-Loop)</span>
              </h3>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "0.75rem" }}>
                <div>
                  <label className="form-label">Người thẩm định (Reviewer)</label>
                  <input className="form-input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
                </div>
                <div>
                  <label className="form-label">Nhận xét / Lý do từ chối (Bắt buộc nếu từ chối)</label>
                  <input
                    className="form-input"
                    placeholder="Ghi chú ý kiến chuyên gia hoặc lý do từ chối..."
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ marginBottom: "1rem" }}>
                <label className="form-label">Gắn nhãn lỗi nếu có (Error tags)</label>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                  {ERROR_TAG_OPTIONS.map((tag) => {
                    const isSelected = selectedErrorTags.includes(tag.id);
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleErrorTag(tag.id)}
                        style={{
                          padding: "0.4rem 0.8rem",
                          borderRadius: "6px",
                          border: isSelected ? "1px solid #f43f5e" : "1px solid #334155",
                          background: isSelected ? "#4c0519" : "#1e293b",
                          color: isSelected ? "#fda4af" : "#94a3b8",
                          fontSize: "0.85rem",
                          cursor: "pointer",
                        }}
                      >
                        {tag.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                <button
                  className="btn btn-success"
                  onClick={handleApprove}
                  disabled={hasReasonWithoutSource}
                  style={{ flex: 1 }}
                >
                  <CheckCircle size={20} />
                  <span>Duyệt thao tác (Approve)</span>
                </button>

                <button
                  className="btn btn-danger"
                  onClick={handleReject}
                  style={{ flex: 1 }}
                >
                  <XCircle size={20} />
                  <span>Từ chối (Reject)</span>
                </button>

                <button
                  className="btn btn-primary"
                  onClick={handleSavePatch}
                  style={{ flex: 1 }}
                >
                  <Save size={20} />
                  <span>Lưu thay đổi (v{selectedProfile.version + 1})</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "400px" }}>
            <p style={{ color: "#94a3b8" }}>Chọn một hồ sơ thao tác từ cột bên trái để thẩm định</p>
          </div>
        )}
      </div>
    </div>
  );
}
