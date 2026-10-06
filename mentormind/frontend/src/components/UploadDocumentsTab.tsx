import React, { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api";
import {
  DataClassification,
  DocumentIngestFile,
  DocumentIngestResult,
  JobResponse,
  JobStatus,
} from "../types";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileText,
  ShieldCheck,
  Upload,
} from "lucide-react";

// Spec 08 §3, page 4 "Tải tài liệu": upload -> POST /ingest/documents, then poll GET /jobs/{id}.
const ACCEPTED_TYPES = ".pdf,.docx,.xlsx,.pptx";
const POLL_INTERVAL_MS = 2000;

const CLASSIFICATION_LABELS: Record<DataClassification, string> = {
  public:               "Công khai",
  synthetic:            "Dữ liệu tổng hợp",
  factory_confidential: "Mật – dữ liệu nhà máy",
};

const JOB_STATUS: Record<JobStatus, { label: string; badge: string }> = {
  queued:  { label: "Đang chờ",   badge: "badge badge-draft" },
  running: { label: "Đang xử lý", badge: "badge badge-review" },
  done:    { label: "Hoàn tất",   badge: "badge badge-approved" },
  failed:  { label: "Lỗi",        badge: "badge badge-rejected" },
};

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

// Vietnamese message for the user; never a stack trace.
function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === "string") return err.detail; // the API's own messages are Vietnamese
    if (err.status === 422) return "Yêu cầu không hợp lệ: cần ít nhất một tệp và một nhãn dữ liệu.";
    return `Máy chủ báo lỗi (mã ${err.status}). Vui lòng thử lại.`;
  }
  return "Không kết nối được tới máy chủ API. Kiểm tra backend đang chạy rồi thử lại.";
}

function FileOutcome({ file }: { file: DocumentIngestFile }) {
  if (file.error) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", alignItems: "flex-start" }}>
        <span className="badge badge-rejected">Lỗi</span>
        <span style={{ color: "var(--status-danger-text)" }}>{file.error}</span>
      </div>
    );
  }
  if (file.skipped) return <span className="badge badge-muted">Bỏ qua – định dạng không hỗ trợ</span>;
  return <span className="badge badge-approved">Xong</span>;
}

export function UploadDocumentsTab() {
  const [files,          setFiles]          = useState<File[]>([]);
  const [classification, setClassification] = useState<DataClassification | "">("");
  const [busy,           setBusy]           = useState(false);
  const [job,            setJob]            = useState<JobResponse<DocumentIngestResult> | null>(null);
  const [errorMsg,       setErrorMsg]       = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  // Polling stops when the user leaves the tab.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const handleUpload = async () => {
    if (files.length === 0 || !classification) return;
    setBusy(true);
    setErrorMsg(null);
    setJob(null);
    try {
      const { job_id } = await api.uploadDocuments(files, classification);
      for (;;) {
        const current = await api.getJob<DocumentIngestResult>(job_id);
        if (!mounted.current) return;
        setJob(current);
        if (current.status === "done" || current.status === "failed") return;
        await sleep(POLL_INTERVAL_MS);
      }
    } catch (err) {
      if (mounted.current) setErrorMsg(describeError(err));
    } finally {
      if (mounted.current) setBusy(false);
    }
  };

  const result = job?.result ?? null;
  const canUpload = !busy && files.length > 0 && classification !== "";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>

      {/* ── Upload form ── */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon ci-cyan">
              <Upload size={14} color="var(--accent-cyan)" />
            </div>
            Tải tài liệu vào kho tri thức
          </div>
          <span className="badge badge-cyan">PDF · DOCX · XLSX · PPTX</span>
        </div>

        <div className="card-body">
          <div className="data-grid data-grid-2" style={{ marginBottom: "1.1rem" }}>
            <div className="form-group">
              <label className="form-label" htmlFor="input-documents">
                <FileText size={12} color="var(--accent-cyan)" />
                Tệp tài liệu
              </label>
              {/* Hidden: the native button's text follows the browser language, ours is Vietnamese. */}
              <input
                id="input-documents"
                ref={fileInput}
                type="file"
                multiple
                accept={ACCEPTED_TYPES}
                hidden
                disabled={busy}
                onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
              />
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  id="btn-choose-documents"
                  type="button"
                  className="btn btn-ghost"
                  disabled={busy}
                  onClick={() => fileInput.current?.click()}
                >
                  <FileText size={14} />
                  Chọn tệp…
                </button>
                {files.length === 0 ? (
                  <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>Chưa chọn tệp nào</span>
                ) : (
                  <div className="chip-list">
                    {files.map((f) => (
                      <span key={f.name} className="mono-tag">{f.name}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="select-classification">
                <ShieldCheck size={12} color="var(--accent-cyan)" />
                Nhãn dữ liệu (bắt buộc)
              </label>
              <select
                id="select-classification"
                className="form-select"
                value={classification}
                disabled={busy}
                onChange={(e) => setClassification(e.target.value as DataClassification)}
              >
                <option value="" disabled>— Chọn nhãn dữ liệu —</option>
                {(Object.keys(CLASSIFICATION_LABELS) as DataClassification[]).map((c) => (
                  <option key={c} value={c}>{CLASSIFICATION_LABELS[c]}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
              {files.length === 0 || !classification
                ? "Chọn ít nhất một tệp và nhãn dữ liệu để tải lên."
                : `${files.length} tệp · nhãn: ${CLASSIFICATION_LABELS[classification]}`}
            </span>
            <button
              id="btn-upload-documents"
              className="btn btn-primary btn-lg"
              onClick={handleUpload}
              disabled={!canUpload}
            >
              {busy ? <div className="spinner" /> : <Upload size={16} />}
              {busy ? (job ? "Đang xử lý…" : "Đang tải lên…") : "Tải lên & xử lý"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Error ── */}
      {errorMsg && (
        <div className="alert alert-error">
          <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── Job progress & per-file result ── */}
      {job && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon ci-green">
                <Database size={14} color="var(--status-success)" />
              </div>
              Kết quả xử lý
            </div>
            <span className={JOB_STATUS[job.status].badge}>{JOB_STATUS[job.status].label}</span>
          </div>

          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <span className="mono-tag" style={{ alignSelf: "flex-start" }}>{job.job_id}</span>

            {(job.status === "queued" || job.status === "running") && (
              <div className="loading-center" style={{ padding: "1.5rem 1rem" }}>
                <div className="spinner spinner-lg" />
                <span>Đang tách chunk và đưa vào kho tìm kiếm… (tự cập nhật mỗi 2 giây)</span>
              </div>
            )}

            {job.status === "failed" && (
              <div className="alert alert-error">
                <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                <span>Xử lý thất bại: {job.error || "không rõ nguyên nhân."}</span>
              </div>
            )}

            {job.status === "done" && result && (
              <div className="alert alert-success">
                <CheckCircle2 size={15} style={{ flexShrink: 0, marginTop: 2 }} />
                <span>
                  Hoàn tất: tài liệu đã được tách chunk và index với nhãn{" "}
                  <strong>{CLASSIFICATION_LABELS[result.classification]}</strong>.
                </span>
              </div>
            )}

            {result && result.files.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Tệp</th>
                      <th>doc_id</th>
                      <th>Extractor</th>
                      <th className="num">Số trang</th>
                      <th className="num">Số chunk</th>
                      <th>Kết quả</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.files.map((f) => (
                      <tr key={f.name}>
                        <td>{f.name}</td>
                        <td className="mono">{f.doc_id ?? "—"}</td>
                        <td>{f.extractor ?? "—"}</td>
                        <td className="num">{f.pages}</td>
                        <td className="num">{f.chunks}</td>
                        <td><FileOutcome file={f} /></td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={4}>Tổng số chunk đã index</td>
                      <td className="num">{result.chunks_indexed}</td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
