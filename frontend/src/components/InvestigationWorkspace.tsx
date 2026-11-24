import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  Layers,
  Network,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';
import { Claim, Entity, ReasoningResult, StructuredQueryPlan } from '../types';
import { AblationPanel } from './AblationPanel';
import { QueryBuilder } from './QueryBuilder';

interface InvestigationWorkspaceProps {
  entities: Entity[];
  onSelectEntity: (entity: Entity) => void;
  onSelectClaim: (claim: Claim) => void;
  onSelectDocument: (docId: string) => void;
  onNavigateToGraph: () => void;
  onExecuteQuery: (plan: StructuredQueryPlan) => Promise<ReasoningResult>;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  entities,
  onSelectEntity,
  onSelectClaim,
  onSelectDocument,
  onNavigateToGraph,
  onExecuteQuery,
}) => {
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [activePlan, setActivePlan] = useState<StructuredQueryPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedTargetForAblation, setSelectedTargetForAblation] = useState<Entity | null>(null);

  const handleRunQuery = async (plan: StructuredQueryPlan) => {
    setLoading(true);
    setActivePlan(plan);
    try {
      const res = await onExecuteQuery(plan);
      setResult(res);
      if (res.matching_entities.length > 0) {
        setSelectedTargetForAblation(res.matching_entities[0]);
      } else {
        setSelectedTargetForAblation(null);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Verifiable Path Established</span>
          </span>
        );
      case 'contradiction_detected':
        return (
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-500/15 border border-amber-500/40 text-amber-400 text-xs font-mono">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Factual Contradiction Detected</span>
          </span>
        );
      case 'insufficient_evidence':
        return (
          <span className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Insufficient Evidence (Bounded Control)</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Mission Statement */}
      <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-amber-400 text-xs font-mono uppercase tracking-widest mb-1">
              <Compass className="w-4 h-4" />
              <span>Investigative Reasoning Substrate</span>
            </div>
            <h1 className="text-xl font-bold text-neutral-100 font-sans tracking-tight">
              Evidence-Native Multi-Hop Synthesis
            </h1>
            <p className="text-xs text-neutral-400 font-sans mt-1 max-w-2xl leading-relaxed">
              Execute deterministic, bounded graph traversals across reified claims. Every factual link
              is substantiated by exact source text quotations, character offsets, and contradiction analysis.
            </p>
          </div>

          <div className="flex items-center space-x-2 self-start md:self-auto font-mono text-xs">
            <button
              onClick={onNavigateToGraph}
              className="flex items-center space-x-2 px-3.5 py-2 rounded bg-graphite-850 hover:bg-graphite-800 border border-graphite-700 text-neutral-200 transition-colors"
            >
              <Network className="w-4 h-4 text-amber-400" />
              <span>Inspect Full Graph</span>
            </button>
          </div>
        </div>
      </div>

      {/* Structured Query Builder */}
      <QueryBuilder entities={entities} onExecute={handleRunQuery} loading={loading} />

      {/* Query Execution Telemetry & Results */}
      {result && (
        <div className="space-y-6">
          {/* Results Header Bar */}
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-4 font-mono flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-3">
              {getStatusBadge(result.status)}
              <span className="text-neutral-500">|</span>
              <div className="flex items-center space-x-1 text-neutral-300">
                <Clock className="w-3.5 h-3.5 text-neutral-400" />
                <span>{result.execution_time_ms} ms</span>
              </div>
              <span className="text-neutral-500">|</span>
              <div className="flex items-center space-x-1 text-neutral-300">
                <Layers className="w-3.5 h-3.5 text-neutral-400" />
                <span>{result.hop_count} Hop(s)</span>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-neutral-400">Path Confidence C(P):</span>
              <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-bold">
                {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Answer Card */}
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5 font-mono">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs uppercase text-neutral-400 tracking-wider">Synthesized Answer & Findings</span>
              {result.matching_entities.length > 0 && (
                <span className="text-xs text-amber-400">
                  {result.matching_entities.length} Match(es) Found
                </span>
              )}
            </div>

            <p className="text-sm font-sans text-neutral-200 leading-relaxed bg-graphite-950 p-4 rounded border border-graphite-850">
              {result.explanation}
            </p>

            {/* Target Entities Cards */}
            {result.matching_entities.length > 0 && (
              <div className="mt-4">
                <span className="text-[11px] text-neutral-400 uppercase tracking-wider block mb-2">
                  Matching Target Entities
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {result.matching_entities.map((ent) => (
                    <div
                      key={ent.id}
                      onClick={() => onSelectEntity(ent)}
                      className="cursor-pointer p-3 bg-graphite-950 hover:bg-graphite-850 rounded border border-graphite-800 hover:border-amber-500/40 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-neutral-100">{ent.canonical_name}</span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-graphite-800 text-amber-400 border border-graphite-700">
                          {ent.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-neutral-400 truncate">{ent.id}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Reasoning Paths Breakdown */}
          {result.paths.length > 0 && (
            <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5 font-mono">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs uppercase text-neutral-400 tracking-wider flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  <span>Demonstrable Reasoning Paths ({result.paths.length})</span>
                </span>
              </div>

              <div className="space-y-4">
                {result.paths.map((path, pathIdx) => (
                  <div
                    key={pathIdx}
                    className="p-4 bg-graphite-950 rounded-lg border border-graphite-800 hover:border-graphite-700 transition-colors"
                  >
                    <div className="flex items-center justify-between text-xs mb-3 border-b border-graphite-850 pb-2">
                      <span className="text-amber-400 font-semibold">Path #{pathIdx + 1} ({path.hop_count} Hops)</span>
                      <div className="flex items-center space-x-3 text-neutral-400">
                        <span>Confidence: <strong className="text-neutral-200">{(path.path_confidence * 100).toFixed(1)}%</strong></span>
                        <span>•</span>
                        <span>Sources: {path.supporting_document_ids.join(', ')}</span>
                      </div>
                    </div>

                    {/* Step-by-step Segments */}
                    <div className="space-y-3">
                      {path.segments.map((seg, segIdx) => (
                        <div key={segIdx} className="bg-graphite-900/60 p-3 rounded border border-graphite-800">
                          <div className="flex items-center flex-wrap gap-2 text-xs mb-2">
                            <button
                              onClick={() => onSelectEntity(seg.from_entity)}
                              className="px-2 py-0.5 rounded bg-graphite-800 hover:bg-graphite-700 text-neutral-200 border border-graphite-700 font-semibold"
                            >
                              {seg.from_entity.canonical_name}
                            </button>

                            <ArrowRight className="w-3.5 h-3.5 text-neutral-500" />

                            <button
                              onClick={() => onSelectClaim(seg.claim)}
                              className={`px-2 py-0.5 rounded border text-xs font-mono flex items-center space-x-1 ${
                                seg.claim.polarity === 'negated'
                                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                                  : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                              }`}
                            >
                              <span>{seg.claim.predicate}</span>
                              <span className="text-[10px] text-neutral-400">({seg.direction})</span>
                            </button>

                            <ArrowRight className="w-3.5 h-3.5 text-neutral-500" />

                            <button
                              onClick={() => onSelectEntity(seg.to_entity)}
                              className="px-2 py-0.5 rounded bg-graphite-800 hover:bg-graphite-700 text-neutral-200 border border-graphite-700 font-semibold"
                            >
                              {seg.to_entity.canonical_name}
                            </button>

                            {seg.is_disputed && (
                              <span className="ml-auto text-[10px] px-2 py-0.5 rounded bg-amber-500/15 border border-amber-500/40 text-amber-400 flex items-center space-x-1">
                                <AlertTriangle className="w-3 h-3" />
                                <span>Contradiction Flagged</span>
                              </span>
                            )}
                          </div>

                          {/* Evidence Quotes */}
                          {seg.evidence.map((ev) => (
                            <div key={ev.id} className="text-xs mt-2 pl-3 border-l-2 border-graphite-700">
                              <div className="flex items-center space-x-2 text-[11px] text-neutral-400 mb-0.5">
                                <button
                                  onClick={() => onSelectDocument(ev.document_id)}
                                  className="text-amber-400 hover:underline font-semibold"
                                >
                                  {ev.document_id}
                                </button>
                                <span>•</span>
                                <span>Page {ev.page || 1}</span>
                                <span>•</span>
                                <span className="text-neutral-500">[{ev.char_offset_start}:{ev.char_offset_end}]</span>
                              </div>
                              <blockquote className="text-xs text-neutral-300 font-sans italic">
                                "{ev.quote}"
                              </blockquote>
                            </div>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Counterfactual Evidence Ablation Section */}
          {activePlan && result.matching_entities.length > 0 && selectedTargetForAblation && (
            <AblationPanel
              queryPlan={activePlan}
              targetEntityId={selectedTargetForAblation.id}
              targetEntityName={selectedTargetForAblation.canonical_name}
            />
          )}
        </div>
      )}
    </div>
  );
};
