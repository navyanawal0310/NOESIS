import React, { useEffect, useState } from 'react';
import { X, Quote, AlertTriangle, FileText, CheckCircle2 } from 'lucide-react';
import { Claim, Evidence } from '../types';
import { api } from '../services/api';

interface ClaimDetailModalProps {
  claim: Claim | null;
  onClose: () => void;
  onSelectDocument?: (docId: string) => void;
}

export const ClaimDetailModal: React.FC<ClaimDetailModalProps> = ({ claim, onClose, onSelectDocument }) => {
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!claim) return;
    setLoading(true);
    api
      .getClaimEvidence(claim.id)
      .then((evs) => setEvidenceList(evs))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [claim]);

  if (!claim) return null;

  const isNegated = claim.polarity === 'negated';
  const hasContradiction = claim.contradiction_ids && claim.contradiction_ids.length > 0;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-graphite-900 border border-graphite-700 rounded-lg max-w-2xl w-full shadow-2xl p-6 font-mono relative max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-neutral-400 hover:text-neutral-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div
            className={`w-9 h-9 rounded border flex items-center justify-center ${
              isNegated
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            }`}
          >
            <Quote className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-base font-semibold text-neutral-100">{claim.predicate}</h3>
              <span
                className={`text-[10px] uppercase px-2 py-0.5 rounded border font-mono ${
                  isNegated
                    ? 'bg-rose-500/10 border-rose-500/40 text-rose-400'
                    : 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
                }`}
              >
                {claim.polarity}
              </span>
              {hasContradiction && (
                <span className="flex items-center space-x-1 text-[10px] uppercase px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 text-amber-400">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Disputed</span>
                </span>
              )}
            </div>
            <p className="text-xs text-neutral-400 font-mono mt-0.5">Fingerprint: {claim.id}</p>
          </div>
        </div>

        {/* Claim Details */}
        <div className="grid grid-cols-2 gap-3 mb-5 text-xs bg-graphite-950 p-3 rounded border border-graphite-800">
          <div>
            <span className="text-neutral-500 block text-[11px]">Subject Entity</span>
            <span className="text-neutral-200 font-medium">{claim.subject_id}</span>
          </div>
          <div>
            <span className="text-neutral-500 block text-[11px]">Object Entity</span>
            <span className="text-neutral-200 font-medium">{claim.object_id}</span>
          </div>
          <div>
            <span className="text-neutral-500 block text-[11px]">Temporal Scope</span>
            <span className="text-neutral-300">{claim.temporal_scope || 'Unrestricted'}</span>
          </div>
          <div>
            <span className="text-neutral-500 block text-[11px]">Heuristic Confidence C(e)</span>
            <span className="text-amber-400 font-semibold">{claim.confidence}</span>
          </div>
        </div>

        {/* Supporting Evidence List */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-neutral-300 uppercase tracking-wider flex items-center space-x-1.5">
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span>Grounded Evidence Records ({evidenceList.length})</span>
            </span>
          </div>

          {loading ? (
            <div className="p-4 text-center text-xs text-neutral-400">Loading evidence records...</div>
          ) : evidenceList.length === 0 ? (
            <div className="p-4 text-center text-xs text-neutral-400 bg-graphite-950 rounded border border-graphite-800">
              No direct evidence records linked to this claim.
            </div>
          ) : (
            <div className="space-y-3">
              {evidenceList.map((ev) => (
                <div
                  key={ev.id}
                  className="p-3 bg-graphite-950 rounded border border-graphite-800 hover:border-graphite-700 transition-colors"
                >
                  <div className="flex items-center justify-between text-[11px] mb-1.5 text-neutral-400">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => onSelectDocument && onSelectDocument(ev.document_id)}
                        className="text-amber-400 hover:underline flex items-center space-x-1 font-semibold"
                      >
                        <span>{ev.document_id}</span>
                      </button>
                      <span>•</span>
                      <span>Page {ev.page || 1}</span>
                      <span>•</span>
                      <span className="text-neutral-500">
                        Offsets: [{ev.char_offset_start}:{ev.char_offset_end}]
                      </span>
                    </div>
                    <div className="flex items-center space-x-1 text-emerald-400 text-[10px]">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Span Verified</span>
                    </div>
                  </div>

                  <blockquote className="text-xs text-neutral-200 font-sans italic border-l-2 border-amber-500/60 pl-3 py-1 my-1 leading-relaxed bg-graphite-900/40 rounded-r">
                    "{ev.quote}"
                  </blockquote>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-5 pt-3 border-t border-graphite-800 flex justify-between items-center text-xs">
          <span className="text-[11px] text-neutral-500 italic font-sans">
            Quotation matching verifies lexical presence in source text, not semantic
            claim correctness or factual truth.
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-graphite-800 hover:bg-graphite-700 text-neutral-200 text-xs transition-colors border border-graphite-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
