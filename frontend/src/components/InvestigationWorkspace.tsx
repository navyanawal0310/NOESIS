import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Compass,
  Cpu,
  Layers,
  MessageSquare,
  Network,
  Search,
  ShieldAlert,
  Sparkles,
  Terminal,
} from 'lucide-react';
import {
  Claim,
  Entity,
  GroundedAnswer,
  LLMStatus,
  ReasoningResult,
  StructuredQueryPlan,
} from '../types';
import { api } from '../services/api';
import { AblationPanel } from './AblationPanel';
import { QueryBuilder } from './QueryBuilder';

interface InvestigationWorkspaceProps {
  entities: Entity[];
  llmStatus?: LLMStatus | null;
  onSelectEntity: (entity: Entity) => void;
  onSelectClaim: (claim: Claim) => void;
  onSelectDocument: (docId: string) => void;
  onNavigateToGraph: () => void;
  onExecuteQuery: (plan: StructuredQueryPlan) => Promise<ReasoningResult>;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  entities,
  llmStatus,
  onSelectEntity,
  onSelectClaim,
  onSelectDocument,
  onNavigateToGraph,
  onExecuteQuery,
}) => {
  const [queryMode, setQueryMode] = useState<'structured' | 'natural'>('structured');
  const [result, setResult] = useState<ReasoningResult | null>(null);
  const [naturalAnswer, setNaturalAnswer] = useState<GroundedAnswer | null>(null);
  const [activePlan, setActivePlan] = useState<StructuredQueryPlan | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedTargetForAblation, setSelectedTargetForAblation] = useState<Entity | null>(null);

  // Natural query state
  const [naturalQuestion, setNaturalQuestion] = useState<string>('');
  const [naturalMaxHops, setNaturalMaxHops] = useState<number>(3);
  const [naturalError, setNaturalError] = useState<string | null>(null);
  const [showExecutedPlan, setShowExecutedPlan] = useState<boolean>(true);

  const exampleQuestions = [
    'What organization was founded by Elena Vance?',
    'Who did Dr. Alyssa Vance collaborate with?',
    'What technology or project was developed by Aetheris?',
  ];

  const handleRunQuery = async (plan: StructuredQueryPlan) => {
    setLoading(true);
    setActivePlan(plan);
    setNaturalAnswer(null);
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

  const handleRunNaturalQuery = async () => {
    if (!naturalQuestion.trim()) return;
    setLoading(true);
    setNaturalError(null);
    setResult(null);
    try {
      const ans = await api.executeNaturalQuery(naturalQuestion, naturalMaxHops, false);
      setNaturalAnswer(ans);
    } catch (err: any) {
      setNaturalError(err.message || 'Natural query execution failed');
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
            <span>Evidentiary Path Traversed</span>
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
      {/* Top Banner */}
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

        {/* Query Mode Switcher */}
        <div className="flex items-center space-x-2 mt-4 pt-4 border-t border-graphite-800 font-mono text-xs">
          <span className="text-neutral-500 uppercase tracking-wider text-[11px] mr-2">Query Engine:</span>
          <button
            onClick={() => setQueryMode('structured')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-colors ${
              queryMode === 'structured'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                : 'bg-graphite-950 text-neutral-400 hover:text-neutral-200 border border-graphite-800'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Structured Query Plan (Symbolic)</span>
          </button>
          <button
            onClick={() => setQueryMode('natural')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded transition-colors ${
              queryMode === 'natural'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                : 'bg-graphite-950 text-neutral-400 hover:text-neutral-200 border border-graphite-800'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Natural Language Query (Local LLM)</span>
          </button>
        </div>
      </div>

      {/* Query Builders */}
      {queryMode === 'structured' ? (
        <QueryBuilder entities={entities} onExecute={handleRunQuery} loading={loading} />
      ) : (
        <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5 font-mono space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase text-amber-400 tracking-wider flex items-center space-x-2">
              <Cpu className="w-4 h-4" />
              <span>Natural-Language Query Planner</span>
            </span>
            <div className="text-[11px] text-neutral-500">
              Ollama Model: <span className="text-neutral-300">{llmStatus?.configured_model || 'qwen3:4b'}</span>
            </div>
          </div>

          {!llmStatus?.available && (
            <div className="p-3.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start space-x-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong className="font-semibold block">Local LLM Offline (Ollama)</strong>
                <span>
                  Ollama is currently unreachable on http://127.0.0.1:11434. Natural language query planning requires an active local LLM.
                  Switch to <strong>Structured Query Plan</strong> above to execute deterministic multi-hop reasoning directly on the graph.
                </span>
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-[11px] text-neutral-400 uppercase tracking-wider block">
              Enter Research Question:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="e.g., What organization was founded by Elena Vance?"
                value={naturalQuestion}
                onChange={(e) => setNaturalQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRunNaturalQuery()}
                className="flex-1 bg-graphite-950 border border-graphite-700 rounded px-3 py-2 text-neutral-100 placeholder-neutral-500 text-xs focus:outline-none focus:border-amber-500"
              />
              <div className="flex items-center space-x-2 bg-graphite-950 border border-graphite-700 rounded px-3 py-1">
                <span className="text-neutral-400 text-[11px]">Max Hops:</span>
                <select
                  value={naturalMaxHops}
                  onChange={(e) => setNaturalMaxHops(Number(e.target.value))}
                  className="bg-graphite-900 text-neutral-200 border-none text-xs focus:outline-none"
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                  <option value={5}>5</option>
                </select>
              </div>
              <button
                onClick={handleRunNaturalQuery}
                disabled={loading || !naturalQuestion.trim()}
                className="px-4 py-2 rounded bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-graphite-950 font-bold text-xs flex items-center space-x-1.5 transition-colors"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{loading ? 'Synthesizing...' : 'Execute'}</span>
              </button>
            </div>
          </div>

          {/* Quick Examples */}
          <div className="flex items-center flex-wrap gap-2 pt-2 text-[11px]">
            <span className="text-neutral-500">Suggested queries:</span>
            {exampleQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => setNaturalQuestion(q)}
                className="px-2 py-0.5 rounded bg-graphite-950 hover:bg-graphite-800 text-neutral-400 hover:text-amber-400 border border-graphite-800 transition-colors"
              >
                "{q}"
              </button>
            ))}
          </div>

          {naturalError && (
            <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {naturalError}
            </div>
          )}
        </div>
      )}

      {/* Natural Query Grounded Answer Display */}
      {naturalAnswer && (
        <div className="space-y-6">
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-4 font-mono space-y-3 text-xs">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center space-x-3">
                {getStatusBadge(naturalAnswer.status)}
                {naturalAnswer.status_code && (
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                      naturalAnswer.status_code === 'SUCCESS'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : naturalAnswer.status_code === 'ENTITY_NOT_FOUND'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {naturalAnswer.status_code}
                  </span>
                )}
                <span className="text-neutral-500">|</span>
                <div className="flex items-center space-x-1 text-neutral-300">
                  <Clock className="w-3.5 h-3.5 text-neutral-400" />
                  <span>{naturalAnswer.execution_time_ms} ms</span>
                </div>
                <span className="text-neutral-500">|</span>
                <div className="flex items-center space-x-1 text-neutral-300">
                  <Layers className="w-3.5 h-3.5 text-neutral-400" />
                  <span>{naturalAnswer.hop_count} Hop(s)</span>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-neutral-400">Path Confidence:</span>
                <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-bold">
                  {(naturalAnswer.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Latency Breakdown Telemetry */}
            {naturalAnswer.latencies && Object.keys(naturalAnswer.latencies).length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-graphite-800 text-[11px] text-neutral-400">
                <span className="text-neutral-500 uppercase tracking-wider flex items-center space-x-1 mr-1">
                  <Activity className="w-3 h-3 text-amber-400" />
                  <span>Latencies:</span>
                </span>
                {naturalAnswer.latencies.entity_resolution_ms !== undefined && (
                  <span className="px-2 py-0.5 rounded bg-graphite-950 border border-graphite-800">
                    Resolution: <strong className="text-neutral-200">{naturalAnswer.latencies.entity_resolution_ms} ms</strong>
                  </span>
                )}
                {naturalAnswer.latencies.llm_planning_ms !== undefined && (
                  <span className="px-2 py-0.5 rounded bg-graphite-950 border border-graphite-800">
                    Planning: <strong className="text-neutral-200">{naturalAnswer.latencies.llm_planning_ms} ms</strong>
                  </span>
                )}
                {naturalAnswer.latencies.traversal_ms !== undefined && (
                  <span className="px-2 py-0.5 rounded bg-graphite-950 border border-graphite-800">
                    Traversal: <strong className="text-neutral-200">{naturalAnswer.latencies.traversal_ms} ms</strong>
                  </span>
                )}
                {naturalAnswer.latencies.total_ms !== undefined && (
                  <span className="px-2 py-0.5 rounded bg-graphite-950 border border-graphite-800 text-amber-400">
                    Total: <strong>{naturalAnswer.latencies.total_ms} ms</strong>
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Answer Text */}
          <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-5 font-mono space-y-4">
            <span className="text-xs uppercase text-neutral-400 tracking-wider block">Grounded Answer</span>
            <p className="text-sm font-sans text-neutral-100 leading-relaxed bg-graphite-950 p-4 rounded border border-graphite-850">
              {naturalAnswer.answer}
            </p>

            {/* Executed Query Plan (Symbolic) */}
            {naturalAnswer.executed_plan && (
              <div className="border border-graphite-800 rounded bg-graphite-950 overflow-hidden text-xs">
                <button
                  onClick={() => setShowExecutedPlan(!showExecutedPlan)}
                  className="w-full px-3 py-2 bg-graphite-900/60 hover:bg-graphite-900 flex items-center justify-between text-neutral-300 font-mono transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <Terminal className="w-3.5 h-3.5 text-amber-400" />
                    <span className="font-semibold text-neutral-200">Executed Query Plan (Symbolic)</span>
                    <span className="text-[10px] text-neutral-500 font-normal">
                      Start: {naturalAnswer.executed_plan.start_entity} | {naturalAnswer.executed_plan.steps.length} step(s)
                    </span>
                  </div>
                  {showExecutedPlan ? (
                    <ChevronDown className="w-4 h-4 text-neutral-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-neutral-400" />
                  )}
                </button>
                {showExecutedPlan && (
                  <div className="p-3 space-y-2 border-t border-graphite-800 font-mono text-[11px]">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pb-2 border-b border-graphite-850 text-neutral-400">
                      <div>
                        Start Entity: <strong className="text-amber-300">{naturalAnswer.executed_plan.start_entity}</strong>
                      </div>
                      <div>
                        Return Type: <strong className="text-neutral-200">{naturalAnswer.executed_plan.return_type || 'ANY'}</strong>
                      </div>
                      {naturalAnswer.executed_plan.temporal_constraint && (
                        <div>
                          Temporal Scope: <strong className="text-cyan-300">{naturalAnswer.executed_plan.temporal_constraint}</strong>
                        </div>
                      )}
                    </div>
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[10px] uppercase text-neutral-500 block">Traversal Steps:</span>
                      {naturalAnswer.executed_plan.steps.map((st, idx) => (
                        <div key={idx} className="flex items-center space-x-2 bg-graphite-900 px-2.5 py-1.5 rounded border border-graphite-800">
                          <span className="text-amber-400 font-bold">{idx + 1}.</span>
                          <span className="text-neutral-300 uppercase font-semibold">{st.predicate}</span>
                          <span className="text-neutral-500">
                            {st.direction === 'incoming' ? '← incoming (from object)' : '→ outgoing (from subject)'}
                          </span>
                          {st.target_type && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-graphite-950 text-neutral-400 border border-graphite-800">
                              Target: {st.target_type}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Knowledge Gap Diagnostics */}
            {naturalAnswer.gap_diagnostics && (
              <div className="p-4 rounded bg-rose-500/10 border border-rose-500/30 space-y-2">
                <div className="flex items-center space-x-2 text-rose-400 font-semibold text-xs">
                  <ShieldAlert className="w-4 h-4" />
                  <span>Knowledge Gap Discontinuity Detected</span>
                </div>
                <p className="text-xs text-neutral-300 font-sans">
                  {naturalAnswer.gap_diagnostics.diagnostic_message}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-[11px] text-neutral-400 font-mono">
                  <div>
                    Completed Hops: <strong className="text-neutral-200">{naturalAnswer.gap_diagnostics.completed_hops}</strong>
                  </div>
                  <div>
                    Halted Entity: <strong className="text-neutral-200">{naturalAnswer.gap_diagnostics.terminal_entity?.canonical_name || 'Unresolved'}</strong>
                  </div>
                  <div>
                    Missing Predicate: <strong className="text-neutral-200">{naturalAnswer.gap_diagnostics.missing_predicate || 'None'}</strong>
                  </div>
                  <div>
                    Expected Target: <strong className="text-neutral-200">{naturalAnswer.gap_diagnostics.expected_target_type || 'Any'}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Contradiction Warnings */}
            {naturalAnswer.has_contradictions && naturalAnswer.contradiction_notes.length > 0 && (
              <div className="p-3.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-1">
                <div className="flex items-center space-x-2 font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Active Factual Contradictions in Traversed Evidence:</span>
                </div>
                <ul className="list-disc list-inside text-neutral-300 text-[11px] pl-1">
                  {naturalAnswer.contradiction_notes.map((note, idx) => (
                    <li key={idx}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Supporting Evidence Quotes */}
            {naturalAnswer.supporting_quotes.length > 0 && (
              <div>
                <span className="text-[11px] text-neutral-400 uppercase tracking-wider block mb-2">
                  Grounding Source Quotations ({naturalAnswer.supporting_quotes.length})
                </span>
                <div className="space-y-2">
                  {naturalAnswer.supporting_quotes.map((quote, idx) => (
                    <div key={idx} className="p-3 rounded bg-graphite-950 border border-graphite-800 text-xs">
                      <p className="text-amber-200/90 font-sans italic mb-1.5">"{quote}"</p>
                      {naturalAnswer.supporting_document_ids[idx] && (
                        <button
                          onClick={() => onSelectDocument(naturalAnswer.supporting_document_ids[idx])}
                          className="text-[10px] text-amber-400 hover:underline uppercase"
                        >
                          Source: {naturalAnswer.supporting_document_ids[idx]}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Structured Query Telemetry & Results */}
      {result && (
        <div className="space-y-6">
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

                            <span className="text-neutral-500 font-mono text-[10px]">
                              {seg.direction === 'outgoing' ? '─[' : '◀─['}
                            </span>
                            <button
                              onClick={() => onSelectClaim(seg.claim)}
                              className="px-2 py-0.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[11px] font-bold"
                            >
                              {seg.claim.predicate}
                            </button>
                            <span className="text-neutral-500 font-mono text-[10px]">
                              {seg.direction === 'outgoing' ? ']─▶' : ']─'}
                            </span>

                            <button
                              onClick={() => onSelectEntity(seg.to_entity)}
                              className="px-2 py-0.5 rounded bg-graphite-800 hover:bg-graphite-700 text-neutral-200 border border-graphite-700 font-semibold"
                            >
                              {seg.to_entity.canonical_name}
                            </button>

                            <div className="ml-auto flex items-center space-x-2 text-[11px]">
                              <span className="text-neutral-400">C(e): {(seg.segment_confidence * 100).toFixed(1)}%</span>
                              {seg.is_disputed && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 text-[10px]">
                                  Disputed
                                </span>
                              )}
                            </div>
                          </div>

                          {seg.evidence.length > 0 && (
                            <div className="mt-2 text-neutral-300 font-sans text-xs bg-graphite-950 p-2.5 rounded border border-graphite-850">
                              <p className="italic text-amber-200/90 mb-1">"{seg.evidence[0].quote}"</p>
                              <div className="flex items-center justify-between text-[10px] text-neutral-500 font-mono">
                                <button
                                  onClick={() => onSelectDocument(seg.evidence[0].document_id)}
                                  className="text-amber-400 hover:underline uppercase"
                                >
                                  {seg.evidence[0].document_id} (Page {seg.evidence[0].page ?? 1})
                                </button>
                                <span>Offset: [{seg.evidence[0].char_offset_start}:{seg.evidence[0].char_offset_end}]</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activePlan && selectedTargetForAblation && (
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
