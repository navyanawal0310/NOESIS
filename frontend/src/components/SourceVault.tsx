import React, { useEffect, useState, useRef } from 'react';
import {
  FileText,
  Hash,
  Calendar,
  CheckCircle2,
  Search,
  ShieldCheck,
  Upload,
  Cpu,
  AlertCircle,
  Layers,
  Loader2,
} from 'lucide-react';
import { Document, IngestionJob, LLMStatus } from '../types';
import { api } from '../services/api';

interface SourceVaultProps {
  initialDocumentId?: string | null;
  llmStatus?: LLMStatus | null;
  onIngestionComplete?: (docId: string, result?: any) => void;
  onActiveJobChange?: (job: IngestionJob | null) => void;
}

export const SourceVault: React.FC<SourceVaultProps> = ({
  initialDocumentId,
  llmStatus,
  onIngestionComplete,
  onActiveJobChange,
}) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [highlightOffsets, setHighlightOffsets] = useState<[number, number] | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>('');

  // Upload & Ingestion state
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Active Job & Polling state
  const [activeJob, setActiveJob] = useState<IngestionJob | null>(null);
  const [ingesting, setIngesting] = useState<boolean>(false);
  const pollingTimer = useRef<any>(null);

  const stopPolling = () => {
    if (pollingTimer.current) {
      window.clearInterval(pollingTimer.current);
      pollingTimer.current = null;
    }
  };

  const startPolling = (jobId: string, docId: string) => {
    stopPolling();
    pollingTimer.current = window.setInterval(async () => {
      try {
        const job = await api.getJobStatus(jobId);
        setActiveJob(job);
        if (onActiveJobChange) onActiveJobChange(job);

        const statusUpper = job.status.toUpperCase();
        if (statusUpper === 'COMPLETED') {
          stopPolling();
          setIngesting(false);
          if (onActiveJobChange) onActiveJobChange(null);
          await fetchDocs();
          const doc = await api.getDocument(docId);
          setSelectedDoc(doc);
          if (onIngestionComplete) {
            onIngestionComplete(docId, job.result);
          }
        } else if (statusUpper === 'FAILED') {
          stopPolling();
          setIngesting(false);
          if (onActiveJobChange) onActiveJobChange(null);
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 750);
  };

  const fetchDocs = () => {
    return api
      .getDocuments()
      .then((docs) => {
        setDocuments(docs);
        if (initialDocumentId) {
          const match = docs.find((d) => d.id === initialDocumentId);
          if (match) setSelectedDoc(match);
          else if (docs.length > 0 && !selectedDoc) setSelectedDoc(docs[0]);
        } else if (docs.length > 0 && !selectedDoc) {
          setSelectedDoc(docs[0]);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchDocs();
  }, [initialDocumentId]);

  // Check document status and resume active polling on selection or page refresh
  useEffect(() => {
    if (!selectedDoc) {
      stopPolling();
      setActiveJob(null);
      setIngesting(false);
      return;
    }

    api
      .getDocumentStatus(selectedDoc.id)
      .then((statusResp) => {
        if (statusResp.job) {
          const job = statusResp.job;
          setActiveJob(job);
          const s = job.status.toUpperCase();
          if (s !== 'COMPLETED' && s !== 'FAILED') {
            setIngesting(true);
            startPolling(job.job_id, selectedDoc.id);
          }
        } else {
          if (!ingesting) {
            setActiveJob(null);
          }
        }
      })
      .catch((err) => console.debug('Status check failed:', err));

    return () => {
      stopPolling();
    };
  }, [selectedDoc?.id]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const resp = await api.uploadDocument(file);
      setUploadSuccess(`Uploaded '${file.name}' (${resp.total_chars} chars, ${resp.total_pages} page(s)).`);
      await fetchDocs();
      const updatedDocs = await api.getDocuments();
      const match = updatedDocs.find((d) => d.id === resp.document_id);
      if (match) setSelectedDoc(match);
    } catch (err: any) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const isJobActive = Boolean(
    activeJob && !['COMPLETED', 'FAILED'].includes(activeJob.status.toUpperCase())
  );

  const handleIngestDocument = async () => {
    if (!selectedDoc || isJobActive) return;
    setIngesting(true);
    setUploadError(null);

    try {
      const submitRes = await api.ingestDocument(selectedDoc.id);
      const initialJob: IngestionJob = {
        job_id: submitRes.job_id,
        document_id: selectedDoc.id,
        status: submitRes.status || 'QUEUED',
        progress_percent: submitRes.progress_percent || 0.0,
        total_chunks: 0,
        processed_chunks: 0,
        accepted_claims: 0,
        rejected_claims: 0,
        evidence_records: 0,
        elapsed_time_seconds: 0.0,
        created_at: new Date().toISOString(),
      };
      setActiveJob(initialJob);
      if (onActiveJobChange) onActiveJobChange(initialJob);
      startPolling(submitRes.job_id, selectedDoc.id);
    } catch (err: any) {
      setIngesting(false);
      const failedJob: IngestionJob = {
        job_id: 'error',
        document_id: selectedDoc.id,
        status: 'FAILED',
        progress_percent: 0.0,
        total_chunks: 0,
        processed_chunks: 0,
        accepted_claims: 0,
        rejected_claims: 0,
        error_message: err.message || 'Failed to submit ingestion job',
        created_at: new Date().toISOString(),
      };
      setActiveJob(failedJob);
      if (onActiveJobChange) onActiveJobChange(failedJob);
    }
  };

  const filteredDocs = documents.filter(
    (d) =>
      d.id.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      d.raw_text.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const renderHighlightedText = (text: string, offsets: [number, number] | null) => {
    if (!offsets) return text;
    const [start, end] = offsets;
    if (start < 0 || end > text.length || start >= end) return text;

    const before = text.slice(0, start);
    const target = text.slice(start, end);
    const after = text.slice(end);

    return (
      <>
        {before}
        <mark className="bg-amber-500/25 text-amber-200 border-b-2 border-amber-400 px-0.5 rounded font-medium">
          {target}
        </mark>
        {after}
      </>
    );
  };

  const isIngested =
    selectedDoc?.source_type === 'synthetic' ||
    selectedDoc?.metadata?.ingestion_status === 'ingested' ||
    activeJob?.status.toUpperCase() === 'COMPLETED';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 font-mono text-xs">
      {/* Document Sidebar (4 cols) */}
      <div className="lg:col-span-4 space-y-3">
        {/* Document Ingestion / Upload Box */}
        <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-wider text-amber-400 font-semibold flex items-center space-x-1.5">
              <Upload className="w-3.5 h-3.5" />
              <span>Ingest Document</span>
            </span>
            <span className="text-[10px] text-neutral-500">PDF, TXT, MD</span>
          </div>

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.txt,.md,.markdown"
            className="hidden"
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full py-2 px-3 rounded border border-dashed border-graphite-700 hover:border-amber-500/50 bg-graphite-950 text-neutral-300 hover:text-amber-400 text-xs flex items-center justify-center space-x-2 transition-colors disabled:opacity-50"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{uploading ? 'Parsing & Hashing...' : 'Select File for Ingestion'}</span>
          </button>

          {uploadSuccess && (
            <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px]">
              {uploadSuccess}
            </div>
          )}

          {uploadError && (
            <div className="p-2 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[11px] flex items-start space-x-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        {/* Document Vault List */}
        <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-3">
          <div className="relative mb-3">
            <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Filter vault documents..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-graphite-950 border border-graphite-700 rounded pl-8 pr-3 py-1.5 text-neutral-200 placeholder-neutral-500 focus:outline-none focus:border-amber-500 text-xs"
            />
          </div>

          <div className="space-y-1.5 max-h-[540px] overflow-y-auto pr-1">
            {loading ? (
              <div className="p-4 text-center text-neutral-500">Loading documents...</div>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = selectedDoc?.id === doc.id;
                const docIngested =
                  doc.source_type === 'synthetic' ||
                  doc.metadata?.ingestion_status === 'ingested';

                return (
                  <div
                    key={doc.id}
                    onClick={() => {
                      setSelectedDoc(doc);
                      setHighlightOffsets(null);
                    }}
                    className={`p-3 rounded cursor-pointer transition-colors border ${
                      isSelected
                        ? 'bg-amber-500/10 border-amber-500/40 text-neutral-100'
                        : 'bg-graphite-950 hover:bg-graphite-850 border-graphite-800 text-neutral-400'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-amber-400">{doc.id}</span>
                      <div className="flex items-center space-x-1">
                        <span className="text-[10px] uppercase px-1.5 py-0.2 rounded bg-graphite-800 text-neutral-400 border border-graphite-700">
                          {doc.source_type}
                        </span>
                        {docIngested && (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            Indexed
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="font-sans font-medium text-xs text-neutral-200 line-clamp-2">
                      {doc.title}
                    </p>
                    <div className="flex items-center space-x-2 text-[10px] text-neutral-500 mt-2 font-mono">
                      <span>{doc.publication_date || '2023'}</span>
                      <span>•</span>
                      <span>{doc.raw_text.length} chars</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Document Reader (8 cols) */}
      <div className="lg:col-span-8 space-y-4">
        {selectedDoc ? (
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-6 shadow-xl space-y-5">
            {/* Header info */}
            <div>
              <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
                <div className="flex items-center space-x-2 text-[11px] text-amber-400">
                  <FileText className="w-4 h-4" />
                  <span>
                    {selectedDoc.source_type === 'synthetic'
                      ? 'SYNTHETIC SOURCE DOSSIER'
                      : 'INGESTED SOURCE DOCUMENT'}
                  </span>
                  <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px]">
                    {selectedDoc.source_type.toUpperCase()}
                  </span>
                </div>

                {/* Extraction action button */}
                {!isIngested || isJobActive ? (
                  <button
                    onClick={handleIngestDocument}
                    disabled={isJobActive || !llmStatus?.available}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-graphite-950 font-bold text-xs transition-colors"
                  >
                    {isJobActive ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>{activeJob?.status.toUpperCase()} ({Math.round(activeJob?.progress_percent || 0)}%)...</span>
                      </>
                    ) : (
                      <>
                        <Cpu className="w-3.5 h-3.5" />
                        <span>Extract & Ingest Claims</span>
                      </>
                    )}
                  </button>
                ) : (
                  <span className="flex items-center space-x-1 text-emerald-400 text-xs">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Claims Ingested into Graph</span>
                  </span>
                )}
              </div>

              <h2 className="text-lg font-bold text-neutral-100 font-sans tracking-tight">
                {selectedDoc.title}
              </h2>

              <div className="flex flex-wrap items-center gap-4 text-[11px] text-neutral-400 mt-2 pt-2 border-t border-graphite-800">
                <div className="flex items-center space-x-1">
                  <Hash className="w-3.5 h-3.5 text-neutral-500" />
                  <span>ID: <strong className="text-neutral-200">{selectedDoc.id}</strong></span>
                </div>
                <div className="flex items-center space-x-1">
                  <Calendar className="w-3.5 h-3.5 text-neutral-500" />
                  <span>Date: {selectedDoc.publication_date || 'N/A'}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Hash: {selectedDoc.content_hash.slice(0, 16)}...</span>
                </div>
                {selectedDoc.metadata?.total_pages && (
                  <div className="flex items-center space-x-1">
                    <Layers className="w-3.5 h-3.5 text-neutral-500" />
                    <span>Pages: {selectedDoc.metadata.total_pages}</span>
                  </div>
                )}
              </div>

              {/* Real-time Ingestion Processing Status Panel (Tasks 2 & 3) */}
              {activeJob && (
                <div className={`mt-3 p-3.5 rounded-lg border font-mono text-xs space-y-2.5 ${
                  activeJob.status.toUpperCase() === 'FAILED'
                    ? 'bg-rose-950/20 border-rose-500/40 text-rose-300'
                    : activeJob.status.toUpperCase() === 'COMPLETED'
                    ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                    : 'bg-graphite-950 border-amber-500/30 text-neutral-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {activeJob.status.toUpperCase() === 'COMPLETED' ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : activeJob.status.toUpperCase() === 'FAILED' ? (
                        <AlertCircle className="w-4 h-4 text-rose-400" />
                      ) : (
                        <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
                      )}
                      <span className="font-bold uppercase tracking-wider text-[11px]">
                        {activeJob.status.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-neutral-400">
                        ({Math.round(activeJob.progress_percent)}%)
                      </span>
                    </div>
                    <span className="text-[10px] text-neutral-400">
                      Job: {activeJob.job_id}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full bg-graphite-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        activeJob.status.toUpperCase() === 'FAILED'
                          ? 'bg-rose-500'
                          : activeJob.status.toUpperCase() === 'COMPLETED'
                          ? 'bg-emerald-500'
                          : 'bg-amber-400'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, activeJob.progress_percent))}%` }}
                    />
                  </div>

                  {/* Live Metrics Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1 border-t border-graphite-800 text-[10px]">
                    <div>
                      <span className="text-neutral-500 block">Elapsed</span>
                      <span className="font-semibold text-neutral-200">{activeJob.elapsed_time_seconds ?? 0}s</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Chunks</span>
                      <span className="font-semibold text-neutral-200">{activeJob.processed_chunks} / {activeJob.total_chunks}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Accepted</span>
                      <span className="font-semibold text-emerald-400">{activeJob.accepted_claims}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Rejected</span>
                      <span className="font-semibold text-neutral-400">{activeJob.rejected_claims}</span>
                    </div>
                    <div>
                      <span className="text-neutral-500 block">Evidence</span>
                      <span className="font-semibold text-neutral-200">{activeJob.evidence_records ?? 0}</span>
                    </div>
                  </div>

                  {/* Terminal success summary */}
                  {activeJob.status.toUpperCase() === 'COMPLETED' && (
                    <div className="text-[11px] text-emerald-400 pt-1">
                      ✓ Ingested successfully: {activeJob.total_chunks} chunk(s) processed in {activeJob.elapsed_time_seconds ?? 0}s. {activeJob.accepted_claims} claims accepted, {activeJob.evidence_records ?? 0} evidence records created.
                    </div>
                  )}

                  {/* Terminal failure summary */}
                  {activeJob.status.toUpperCase() === 'FAILED' && (
                    <div className="text-[11px] text-rose-400 pt-1">
                      ✗ Ingestion failed: {activeJob.error_message || 'Pipeline execution failed'}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Document Text Viewer */}
            <div className="bg-graphite-950 border border-graphite-850 rounded-lg p-5 font-sans text-sm text-neutral-200 leading-relaxed whitespace-pre-wrap selection:bg-amber-500/30 max-h-[500px] overflow-y-auto">
              {renderHighlightedText(selectedDoc.raw_text, highlightOffsets)}
            </div>

            {/* Quotation Verification Footnote */}
            <div className="p-3 bg-graphite-950 rounded border border-graphite-800 flex items-start space-x-2 text-[11px] text-neutral-400 font-sans">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-neutral-300 font-medium">Lexical Grounding & Text Provenance</p>
                <p className="mt-0.5 text-neutral-400 leading-relaxed">
                  Evidence quotations mapped to {selectedDoc.id} are verified at exact character offsets against this source text.
                  Quotation matching verifies lexical presence in the document; it does not establish semantic entailment or factual truth.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-12 text-center text-neutral-500">
            Select a document from the vault to inspect its source text and provenance records.
          </div>
        )}
      </div>
    </div>
  );
};
