"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Image as ImageIcon, Paperclip, X } from "@phosphor-icons/react";
import { API_URL, apiRequest, parseApiDate } from "@/services/incidents";
import type {
  AuditEvent,
  CandidateProfile,
  Decision,
  DecisionDetail,
  EvidenceRequest,
  Incident,
  IntelligenceOverview,
  ObservationIngestResult,
  RequestAttachment,
  RequestStatus,
} from "@/types/incident";

type WorkflowActionsProps = {
  incident: Incident;
  decision: Decision | null;
  decisionDetail: DecisionDetail | null;
  overview: IntelligenceOverview | null;
  audit: AuditEvent[];
};

type ActorAssignment = {
  evidence_id: string;
  actor_id: string | null;
  actor_name: string | null;
  feasible: boolean;
  location: string | null;
  expected_delay_minutes: number | null;
  reasons: string[];
};

type FhirBundle = {
  resourceType: string;
  entry?: Array<{ resource: Record<string, unknown> }>;
};

const ATTACHMENT_ACCEPT = ".png,.jpg,.jpeg,.webp,.pdf,.csv,.txt";
const ATTACHMENT_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".webp", ".pdf", ".csv", ".txt"]);
const MAX_ATTACHMENT_COUNT = 5;
const MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024;
const MAX_ATTACHMENT_TOTAL_SIZE = 25 * 1024 * 1024;

function formatFileSize(bytes: number) {
  if (bytes === 0) return "0 MB";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentPicker({
  files,
  disabled,
  existingCount = 0,
  existingBytes = 0,
  error,
  onAdd,
  onRemove,
}: {
  files: File[];
  disabled: boolean;
  existingCount?: number;
  existingBytes?: number;
  error?: string;
  onAdd: (files: File[]) => void;
  onRemove: (index: number) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputId = useId();
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);

  return (
    <div className="attachment-field">
      <div
        className={`attachment-dropzone${dragging ? " attachment-dropzone-active" : ""}${disabled ? " attachment-dropzone-disabled" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); if (!disabled) setDragging(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) onAdd(Array.from(event.dataTransfer.files));
        }}
      >
        <input
          className="attachment-input"
          id={inputId}
          type="file"
          accept={ATTACHMENT_ACCEPT}
          multiple
          disabled={disabled}
          aria-label="Choose supporting images or files"
          onChange={(event) => {
            onAdd(Array.from(event.currentTarget.files ?? []));
            event.currentTarget.value = "";
          }}
        />
        <label htmlFor={inputId}>
          <span className="attachment-upload-icon"><Paperclip size={20} aria-hidden="true" /></span>
          <span><strong>Attach supporting material</strong><small>Drop files here or browse from your device</small></span>
        </label>
      </div>
      {files.length > 0 && (
        <ul className="attachment-pending-list" aria-label="Files ready to upload">
          {files.map((file, index) => {
            const Icon = file.type.startsWith("image/") ? ImageIcon : FileText;
            return (
              <li key={`${file.name}-${file.lastModified}-${index}`}>
                <Icon size={18} aria-hidden="true" />
                <span><strong>{file.name}</strong><small>{formatFileSize(file.size)}</small></span>
                <button type="button" aria-label={`Remove ${file.name}`} disabled={disabled} onClick={() => onRemove(index)}>
                  <X size={16} aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <p className="attachment-help">
        {Math.max(0, MAX_ATTACHMENT_COUNT - existingCount - files.length)} file slots left · up to 10 MB each · {formatFileSize(Math.max(0, MAX_ATTACHMENT_TOTAL_SIZE - existingBytes - totalBytes))} request space left · PNG, JPG, WEBP, PDF, CSV or TXT
      </p>
      {error && <p className="attachment-error" role="alert">{error}</p>}
      {files.length > 0 && <p className="attachment-total">{files.length} selected · {formatFileSize(totalBytes)} total</p>}
    </div>
  );
}

function RequestAttachmentList({ requestId, attachments }: { requestId: string; attachments: RequestAttachment[] }) {
  if (!attachments.length) return <p className="attachment-empty">No supporting files have been uploaded.</p>;
  return (
    <ul className="request-attachment-list">
      {attachments.map((attachment) => {
        const Icon = attachment.content_type.startsWith("image/") ? ImageIcon : FileText;
        return (
          <li key={attachment.id}>
            <Icon size={18} aria-hidden="true" />
            <a href={`${API_URL}/api/requests/${requestId}/attachments/${attachment.id}`} download={attachment.filename}>
              {attachment.filename}
            </a>
            <span>{formatFileSize(attachment.size_bytes)}</span>
          </li>
        );
      })}
    </ul>
  );
}

function localDateTimeValue(date: Date) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function profileFor(
  overview: IntelligenceOverview | null,
  evidenceId: string,
): CandidateProfile | undefined {
  return overview?.profiles.find((profile) => profile.evidence_id === evidenceId);
}

export function WorkflowActions({
  incident,
  decision,
  decisionDetail,
  overview,
  audit,
}: WorkflowActionsProps) {
  const router = useRouter();
  const ranked = useMemo(
    () => new Map((overview?.ranking.results ?? []).map((item) => [item.evidence_id, item])),
    [overview],
  );
  const defaultProfile = useMemo(
    () =>
      overview?.profiles.find((item) => item.feasible && ranked.get(item.evidence_id)?.selected) ??
      [...(overview?.profiles ?? [])]
        .filter((item) => item.feasible && ranked.has(item.evidence_id))
        .sort((a, b) => (ranked.get(a.evidence_id)?.rank ?? 999) - (ranked.get(b.evidence_id)?.rank ?? 999))[0] ??
      overview?.profiles.find((item) => item.feasible) ?? overview?.profiles[0],
    [overview, ranked],
  );

  const [selectedEvidenceId, setSelectedEvidenceId] = useState(defaultProfile?.evidence_id ?? "");
  const [request, setRequest] = useState<EvidenceRequest | null>(null);
  const [requester, setRequester] = useState("incident-reviewer");
  const [reviewer, setReviewer] = useState("decision-reviewer");
  const [reason, setReason] = useState("");
  const [reading, setReading] = useState("3.4");
  const [unit, setUnit] = useState("mg/L");
  const [observedAt, setObservedAt] = useState(localDateTimeValue(new Date()));
  const [source, setSource] = useState("Field measurement");
  const [reliability, setReliability] = useState("0.90");
  const [isSimulated, setIsSimulated] = useState(true);
  const [selectedHypothesis, setSelectedHypothesis] = useState(
    overview?.hypotheses.find((item) => item.status === "ACTIVE")?.code ?? "",
  );
  const [impactDirection, setImpactDirection] = useState("supports");
  const [impactRationale, setImpactRationale] = useState("");
  const [fhirBundle, setFhirBundle] = useState<FhirBundle | null>(null);
  const [result, setResult] = useState<ObservationIngestResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [attachmentFiles, setAttachmentFiles] = useState<File[]>([]);
  const [attachmentError, setAttachmentError] = useState("");
  const controlsBusy = busy || !hydrated;

  useEffect(() => setHydrated(true), []);

  useEffect(() => {
    const latestCreatedRequest = audit
      .filter((item) => item.event_type === "REQUEST_CREATED")
      .at(-1);
    if (!latestCreatedRequest) return;
    let cancelled = false;
    apiRequest<EvidenceRequest>("/api/requests/" + latestCreatedRequest.entity_id)
      .then((loaded) => {
        if (!cancelled) setRequest(loaded);
      })
      .catch(() => {
        if (!cancelled) setRequest(null);
      });
    return () => {
      cancelled = true;
    };
  }, [audit]);

  const selectedProfile = profileFor(overview, selectedEvidenceId) ?? defaultProfile;
  const currentVersion = decisionDetail?.versions.find(
    (item) => item.version_number === decisionDetail.current_version,
  );
  const pendingApproval =
    currentVersion?.approval_status === "PENDING" && decision?.status === "PENDING";
  const activeHypotheses = (overview?.hypotheses ?? []).filter((item) => item.status === "ACTIVE");

  function addAttachmentFiles(incoming: File[]) {
    const existingAttachments = request?.attachments ?? [];
    const existingBytes = existingAttachments.reduce((sum, attachment) => sum + attachment.size_bytes, 0);
    const next = [...attachmentFiles, ...incoming];
    const invalid = incoming.find((file) => {
      const extension = file.name.includes(".") ? `.${file.name.split(".").pop()!.toLowerCase()}` : "";
      return !ATTACHMENT_EXTENSIONS.has(extension) || file.size === 0 || file.size > MAX_ATTACHMENT_SIZE || file.name.length > 255;
    });
    if (invalid) {
      setAttachmentError(`${invalid.name}: choose a non-empty PNG, JPG, WEBP, PDF, CSV or TXT file up to 10 MB.`);
      return;
    }
    const unique = next.filter((file, index) =>
      next.findIndex((candidate) => candidate.name === file.name && candidate.size === file.size && candidate.lastModified === file.lastModified) === index,
    );
    if (existingAttachments.length + unique.length > MAX_ATTACHMENT_COUNT) {
      setAttachmentError(`A request can include up to ${MAX_ATTACHMENT_COUNT} files.`);
      return;
    }
    if (existingBytes + unique.reduce((sum, file) => sum + file.size, 0) > MAX_ATTACHMENT_TOTAL_SIZE) {
      setAttachmentError("Attachments must total 25 MB or less.");
      return;
    }
    setAttachmentFiles(unique);
    setAttachmentError("");
  }

  function removeAttachmentFile(index: number) {
    setAttachmentFiles((current) => current.filter((_, itemIndex) => itemIndex !== index));
  }

  async function uploadAttachmentFiles(requestId: string, files: File[]): Promise<RequestAttachment[]> {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file, file.name));
    return apiRequest<RequestAttachment[]>(`/api/requests/${requestId}/attachments`, {
      method: "POST",
      body: formData,
    });
  }

  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The operation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function createRequestDraft() {
    if (!decision || !selectedProfile) throw new Error("A decision and evidence option are required.");
    if (!selectedProfile.feasible) {
      throw new Error(selectedProfile.infeasibility_reason || "This collection is not currently feasible.");
    }

    let assignedActorId: string | null = null;
    if (selectedProfile.required_capability) {
      const capableActors = (overview?.actors ?? []).filter((actor) =>
        actor.capabilities.includes(selectedProfile.required_capability),
      );
      if (!capableActors.length) {
        throw new Error("No available actor has the required collection capability.");
      }
      const now = new Date().toISOString();
      const decisionDeadline = parseApiDate(decision.deadline).toISOString();
      const actorInputs = capableActors.map((actor) => ({
        actor_id: actor.id,
        actor_name: actor.name,
        actor_type: actor.actor_type,
        capability: selectedProfile.required_capability,
        location: actor.location_name || incident.location_name,
        status: actor.available && actor.capacity > 0 ? "available" : "busy",
        available_from: now,
        available_until: decisionDeadline,
        max_concurrent_tasks: actor.capacity,
        expected_delay_minutes: actor.turnaround_minutes ?? selectedProfile.estimated_minutes,
      }));
      const assignment = await apiRequest<ActorAssignment>(
        "/api/requests/assign",
        {
          method: "POST",
          body: JSON.stringify({
            evidence_id: selectedProfile.evidence_id,
            required_capability: selectedProfile.required_capability,
            required_location: incident.location_name,
            decision_deadline: decisionDeadline,
            actors: actorInputs,
          }),
        },
      );
      if (!assignment.feasible || !assignment.actor_id) {
        throw new Error(assignment.reasons.join(" ") || "No available actor can collect this evidence.");
      }
      assignedActorId = assignment.actor_id;
    }

    const created = await apiRequest<EvidenceRequest>("/api/requests", {
      method: "POST",
      body: JSON.stringify({
        incident_id: incident.id,
        decision_id: decision.id,
        evidence_gap_id: selectedProfile.database_gap_id,
        assigned_actor_id: assignedActorId,
        requested_evidence_code: selectedProfile.evidence_code,
        purpose: selectedProfile.purpose,
        priority: selectedProfile.priority,
        estimated_cost: selectedProfile.estimated_cost,
        estimated_minutes: selectedProfile.estimated_minutes,
        requested_by: requester.trim() || "incident-reviewer",
      }),
    });
    setRequest(created);
    setResult(null);
    setFhirBundle(null);
    if (attachmentFiles.length) {
      let uploaded: RequestAttachment[];
      try {
        uploaded = await uploadAttachmentFiles(created.id, attachmentFiles);
      } catch (caught) {
        setAttachmentError(caught instanceof Error ? caught.message : "Files could not be uploaded.");
        throw caught;
      }
      setRequest({ ...created, attachments: uploaded });
      setAttachmentFiles([]);
      setAttachmentError("");
    }
    router.refresh();
  }

  async function addAttachmentsToDraft() {
    if (!request || !attachmentFiles.length) return;
    let uploaded: RequestAttachment[];
    try {
      uploaded = await uploadAttachmentFiles(request.id, attachmentFiles);
    } catch (caught) {
      setAttachmentError(caught instanceof Error ? caught.message : "Files could not be uploaded.");
      throw caught;
    }
    setRequest({ ...request, attachments: [...(request.attachments ?? []), ...uploaded] });
    setAttachmentFiles([]);
    setAttachmentError("");
    router.refresh();
  }

  async function transition(toStatus: RequestStatus, note: string) {
    if (!request) return;
    const updated = await apiRequest<EvidenceRequest>(
      "/api/requests/" + request.id + "/transitions",
      {
        method: "POST",
        body: JSON.stringify({
          to_status: toStatus,
          actor_name: requester.trim() || "incident-reviewer",
          note,
        }),
      },
    );
    setRequest(updated);
    router.refresh();
  }

  async function submitObservation() {
    if (!request) return;
    const numericValue = Number(reading);
    const numericReliability = Number(reliability);
    const code = request.requested_evidence_code;
    const extensions: Array<Record<string, unknown>> = [
      {
        url: "https://aquapass.example/fhir/StructureDefinition/reliability",
        valueDecimal: numericReliability,
      },
    ];
    if (selectedHypothesis) {
      if (!impactRationale.trim()) {
        throw new Error("Explain how the field result relates to the selected hypothesis.");
      }
      extensions.push({
        url: "https://aquapass.example/fhir/StructureDefinition/hypothesis-impact",
        extension: [
          { url: "hypothesisCode", valueCode: selectedHypothesis },
          { url: "direction", valueCode: impactDirection },
          { url: "rationale", valueString: impactRationale.trim() },
        ],
      });
    }
    const observation = {
      resourceType: "Observation",
      id: "OBS-" + crypto.randomUUID(),
      status: "final",
      code: {
        coding: [{ system: "https://aquapass.example/evidence", code, display: code }],
        text: code,
      },
      effectiveDateTime: new Date(observedAt).toISOString(),
      valueQuantity: {
        value: numericValue,
        unit,
        system: "http://unitsofmeasure.org",
        code: unit,
      },
      device: { display: source.trim() || "Field measurement" },
      performer: [{ display: requester.trim() || "field-operator" }],
      meta: isSimulated
        ? {
            tag: [
              {
                system: "https://aquapass.example/tags",
                code: "simulated",
                display: "Simulated demonstration input",
              },
            ],
          }
        : undefined,
      extension: extensions,
      note: [{ text: "Submitted by a field operator for human review." }],
    };
    if (!Number.isFinite(numericValue)) throw new Error("Enter a valid numeric result.");
    if (!Number.isFinite(numericReliability) || numericReliability < 0 || numericReliability > 1) {
      throw new Error("Reliability must be between 0 and 1.");
    }
    if (Number.isNaN(new Date(observedAt).getTime())) throw new Error("Enter a valid observation time.");

    if (request.status === "COLLECTING") {
      const submitted = await apiRequest<EvidenceRequest>(
        "/api/requests/" + request.id + "/transitions",
        {
          method: "POST",
          body: JSON.stringify({
            to_status: "SUBMITTED",
            actor_name: requester.trim() || "field-operator",
            note: "Field result submitted for verification.",
          }),
        },
      );
      setRequest(submitted);
    }

    const ingested = await apiRequest<ObservationIngestResult>(
      "/api/requests/" + request.id + "/observation",
      { method: "POST", body: JSON.stringify(observation) },
    );
    setResult(ingested);
    const refreshed = await apiRequest<EvidenceRequest>("/api/requests/" + request.id);
    setRequest(refreshed);
    router.refresh();
  }

  async function loadFhirBundle() {
    if (!request) return;
    const bundle = await apiRequest<FhirBundle>("/api/requests/" + request.id + "/fhir");
    setFhirBundle(bundle);
  }

  async function submitApproval(action: "APPROVE" | "REJECT") {
    if (!decision) throw new Error("No decision is available for review.");
    if (action === "REJECT" && !reason.trim()) {
      throw new Error("Add a reason before rejecting this decision.");
    }
    await apiRequest("/api/decisions/" + decision.id + "/approval", {
      method: "POST",
      body: JSON.stringify({
        action,
        reviewer_id: reviewer.trim() || "decision-reviewer",
        reason: reason.trim() || undefined,
      }),
    });
    router.refresh();
  }

  return (
    <section className="workflow-panel" aria-labelledby="workflow-title">
      <div className="workflow-panel-heading">
        <div>
          <p className="eyebrow">NEXT ACTION</p>
          <h2 id="workflow-title">Collection & approval</h2>
        </div>
        <span className="subtle-tag">Human reviewed</span>
      </div>

      {error && <p className="inline-alert" role="alert">{error}</p>}
      {result && (
        <p className="success-alert" role="status">
          Result stored on this incident. Decision version {result.decision_version} is waiting for review.
        </p>
      )}

      {!request && (
        <div className="workflow-section">
          <h3>Create a collection request</h3>
          <p className="panel-intro">
            Choose a ranked option. AquaPass will save a draft; a person must explicitly send it.
          </p>
          <label className="field">
            <span>Evidence to collect</span>
            <select
              value={selectedEvidenceId}
              onChange={(event) => setSelectedEvidenceId(event.target.value)}
              disabled={controlsBusy || !overview?.profiles.length}
            >
              {(overview?.profiles ?? []).map((profile) => {
                const item = ranked.get(profile.evidence_id);
                const suffix = profile.feasible
                  ? item
                    ? " · rank " + item.rank
                    : " · feasible"
                  : " · unavailable";
                return (
                  <option key={profile.evidence_id} value={profile.evidence_id}>
                    {profile.candidate_name + suffix}
                  </option>
                );
              })}
            </select>
          </label>
          {selectedProfile && (
            <div className="selected-profile">
              <strong>{selectedProfile.purpose}</strong>
              <span>
                Estimated {selectedProfile.estimated_minutes} minutes · cost units {selectedProfile.estimated_cost}
              </span>
              {!selectedProfile.feasible && (
                <span className="field-error">{selectedProfile.infeasibility_reason}</span>
              )}
            </div>
          )}
          <label className="field">
            <span>Requested by</span>
            <input value={requester} onChange={(event) => setRequester(event.target.value)} maxLength={120} />
          </label>
          <div className="field">
            <span>Supporting images or files <span className="optional-label">Optional</span></span>
            <AttachmentPicker
              files={attachmentFiles}
              disabled={controlsBusy}
              error={attachmentError}
              onAdd={addAttachmentFiles}
              onRemove={removeAttachmentFile}
            />
          </div>
          <button
            className="primary-button"
            type="button"
            disabled={controlsBusy || !decision || !selectedProfile?.feasible}
            onClick={() => void perform(createRequestDraft)}
          >
            {busy ? "Saving request…" : "Create request draft"}
          </button>
        </div>
      )}

      {request && (
        <div className="workflow-section">
          <div className="request-status-line">
            <div>
              <h3>Request {request.id.slice(0, 8).toUpperCase()}</h3>
              <p>{request.requested_evidence_code.replaceAll("_", " ")}</p>
            </div>
            <span className={"status status-" + request.status.toLowerCase().replaceAll("_", "-")}>
              {request.status.replaceAll("_", " ")}
            </span>
          </div>
          <details className="request-history"><summary>Request history · {request.status_events.length} events</summary><ol className="event-list" aria-label="Request status history">
            {request.status_events.map((event) => (
              <li key={event.id}>
                <span className="event-marker" aria-hidden="true" />
                <div>
                  <strong>{event.to_status.replaceAll("_", " ")}</strong>
                  <small>
                    {event.actor_name} · {parseApiDate(event.occurred_at).toLocaleString("en-GB", { timeZone: "Asia/Ho_Chi_Minh" })}
                  </small>
                  {event.note && <p>{event.note}</p>}
                </div>
              </li>
            ))}
          </ol></details>

          <div className="request-attachments">
            <div className="request-attachments-heading">
              <h4>Supporting files</h4>
              <span>{request.attachments?.length ?? 0}</span>
            </div>
            <RequestAttachmentList requestId={request.id} attachments={request.attachments ?? []} />
            {request.status === "DRAFT" && (
              <>
                <AttachmentPicker
                  files={attachmentFiles}
                  disabled={controlsBusy}
                  existingCount={request.attachments?.length ?? 0}
                  existingBytes={(request.attachments ?? []).reduce((sum, item) => sum + item.size_bytes, 0)}
                  error={attachmentError}
                  onAdd={addAttachmentFiles}
                  onRemove={removeAttachmentFile}
                />
                <div className="request-attachment-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    disabled={controlsBusy || attachmentFiles.length === 0}
                    onClick={() => void perform(addAttachmentsToDraft)}
                  >
                    {busy ? "Uploading files…" : `Upload ${attachmentFiles.length || "selected"} file${attachmentFiles.length === 1 ? "" : "s"}`}
                  </button>
                  <small>Files are locked when you send the request.</small>
                </div>
              </>
            )}
          </div>

          <div className="transition-actions">
            {request.status === "DRAFT" && (
              <>
                <button
                  className="primary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() =>
                    void perform(() =>
                      transition("REQUESTED", "Human reviewed and confirmed the request."),
                    )
                  }
                >
                  Confirm and send request
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() =>
                    void perform(() => transition("REJECTED", "Human rejected the draft request."))
                  }
                >
                  Reject draft
                </button>
              </>
            )}
            {request.status === "REQUESTED" && (
              <>
                <button
                  className="primary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() => void perform(() => transition("ACCEPTED", "Collector accepted the request."))}
                >
                  Accept request
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() => void perform(() => transition("REJECTED", "Collector cannot fulfill the request."))}
                >
                  Reject request
                </button>
              </>
            )}
            {request.status === "ACCEPTED" && (
              <>
                <button
                  className="primary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() => void perform(() => transition("COLLECTING", "Collection started."))}
                >
                  Start collection
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() => void perform(() => transition("REJECTED", "Collection cannot proceed."))}
                >
                  Reject request
                </button>
              </>
            )}
          </div>

          {(request.status === "COLLECTING" || request.status === "SUBMITTED") && (
            <div className="field-result-form">
              <h3>Submit the collected evidence</h3>
              <p className="panel-intro">
                These values are entered by the collector and stored as a FHIR Observation.
              </p>
              <div className="form-grid">
                <label className="field">
                  <span>Measured value</span>
                  <input
                    type="number"
                    step="any"
                    value={reading}
                    onChange={(event) => setReading(event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Unit</span>
                  <input value={unit} onChange={(event) => setUnit(event.target.value)} required />
                </label>
                <label className="field">
                  <span>Observed at</span>
                  <input
                    type="datetime-local"
                    value={observedAt}
                    onChange={(event) => setObservedAt(event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Measurement source</span>
                  <input value={source} onChange={(event) => setSource(event.target.value)} required />
                </label>
                <label className="field">
                  <span>Reliability (0–1)</span>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={reliability}
                    onChange={(event) => setReliability(event.target.value)}
                    required
                  />
                </label>
                <label className="field">
                  <span>Submitted by</span>
                  <input value={requester} onChange={(event) => setRequester(event.target.value)} />
                </label>
                {activeHypotheses.length ? (
                  <>
                    <label className="field">
                      <span>Related hypothesis</span>
                      <select
                        value={selectedHypothesis}
                        onChange={(event) => setSelectedHypothesis(event.target.value)}
                      >
                        {activeHypotheses.map((item) => (
                          <option key={item.code} value={item.code}>{item.code} · {item.title}</option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Observed impact</span>
                      <select
                        value={impactDirection}
                        onChange={(event) => setImpactDirection(event.target.value)}
                      >
                        <option value="supports">Supports</option>
                        <option value="corroborates">Corroborates</option>
                        <option value="contradicts">Contradicts</option>
                      </select>
                    </label>
                    <label className="field field-wide">
                      <span>Why this result has that impact</span>
                      <textarea
                        value={impactRationale}
                        onChange={(event) => setImpactRationale(event.target.value)}
                        rows={2}
                        required
                      />
                    </label>
                  </>
                ) : null}
              </div>
              <label className="simulation-toggle">
                <input
                  type="checkbox"
                  checked={isSimulated}
                  onChange={(event) => setIsSimulated(event.target.checked)}
                />
                <span>
                  Label this result as simulated
                  <small>Keep enabled for demonstration or sample values.</small>
                </span>
              </label>
              <button
                className="primary-button"
                type="button"
                disabled={controlsBusy}
                onClick={() => void perform(submitObservation)}
              >
                {busy ? "Submitting…" : request.status === "COLLECTING" ? "Submit result" : "Retry evidence ingest"}
              </button>
            </div>
          )}

          <div className="workflow-tools">
            <button className="text-button" type="button" disabled={controlsBusy} onClick={() => void perform(loadFhirBundle)}>
              View FHIR request
            </button>
            <button
              className="text-button"
              type="button"
              disabled={controlsBusy}
              onClick={() => void perform(async () => {
                setRequest(await apiRequest<EvidenceRequest>("/api/requests/" + request.id));
              })}
            >
              Refresh status
            </button>
          </div>
          {fhirBundle && (
            <details className="fhir-details">
              <summary>FHIR ServiceRequest and Task payload</summary>
              <pre>{JSON.stringify(fhirBundle, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      {decisionDetail && currentVersion && (
        <div className="workflow-section approval-section">
          <h3>Review the current decision</h3>
          <p className="approval-summary">{currentVersion.summary}</p>
          <p className="panel-intro">
            Version {currentVersion.version_number} · uncertainty {currentVersion.uncertainty_level} ·
            approval {currentVersion.approval_status.toLowerCase()}
          </p>
          {pendingApproval ? (
            <>
              <label className="field">
                <span>Reviewer</span>
                <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} maxLength={120} />
              </label>
              <label className="field">
                <span>Review note (required to reject)</span>
                <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} />
              </label>
              <div className="transition-actions">
                <button
                  className="primary-button"
                  type="button"
                  disabled={controlsBusy}
                  onClick={() => void perform(() => submitApproval("APPROVE"))}
                >
                  Approve decision
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={controlsBusy || !reason.trim()}
                  onClick={() => void perform(() => submitApproval("REJECT"))}
                >
                  Reject decision
                </button>
              </div>
            </>
          ) : (
            <p className="success-alert" role="status">
              This decision version has already been reviewed or is not awaiting approval.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
