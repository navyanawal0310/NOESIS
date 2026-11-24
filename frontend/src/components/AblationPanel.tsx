import React, { useState } from 'react';
import { ShieldCheck, Flame, RefreshCw, AlertOctagon } from 'lucide-react';
import { AblationReport, StructuredQueryPlan } from '../types';
import { api } from '../services/api';

interface AblationPanelProps {
  queryPlan: StructuredQueryPlan;
  targetEntityId: string;
  targetEntityName: string;
}

export const AblationPanel: React.FC<AblationPanelProps> = ({
  queryPlan,
  targetEntityId,
  targetEntityName,
}) => {
  const [report, setReport] = useState<AblationReport | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const runAblationTest = async () => {
    setLoading(true);
    try {
      const res = await api.runCounterfactual(queryPlan, targetEntityId);
      setReport(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-graphite-900 border border-graphite-800 rounded-lg p-4 font-mono shadow-md mt-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Flame className="w-4 h-4 text-amber-500" />
          <h4 className="text-xs font-semibold text-neutral-100 uppercase tracking-wider">
            Counterfactual Evidence Ablation (FR-09)
          </h4>
        </div>
        <button
          onClick={runAblationTest}
          disabled={loading}
          className="flex items-center space-x-1.5 px-3 py-1 rounded bg-graphite-800 hover:bg-graphite-700 text-amber-400 border border-graphite-700 text-xs transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span>{loading ? 'Simulating Ablation...' : 'Run Source Removal Test'}</span>
        </button>
      </div>

      <p className="text-[11px] text-neutral-400 font-sans mb-3 leading-relaxed">
        Temporarily excludes individual supporting source documents to evaluate whether the conclusion for{' '}
        <strong className="text-neutral-200">{targetEntityName}</strong> survives or collapses.
      </p>

      {report && (
        <div className="space-y-3 text-xs bg-graphite-950 p-3.5 rounded border border-graphite-800">
          <div className="flex items-center justify-between">
            <span className="text-neutral-400">Robustness Score R(a):</span>
            <span
              className={`font-bold px-2 py-0.5 rounded text-xs border ${
                report.robustness_score < 0.5
                  ? 'bg-rose-500/10 border-rose-500/40 text-rose-400'
                  : 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400'
              }`}
            >
              {(report.robustness_score * 100).toFixed(0)}% Survival
            </span>
          </div>

          {/* Critical Sources Warning */}
          {report.critical_sources.length > 0 && (
            <div className="p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300">
              <div className="flex items-center space-x-1.5 font-semibold text-xs mb-1">
                <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
                <span>Single Point of Evidentiary Failure</span>
              </div>
              <p className="text-[11px] font-sans">
                Conclusion depends entirely on: <strong className="text-rose-200">{report.critical_sources.join(', ')}</strong>.
                If removed, this reasoning path ceases to exist.
              </p>
            </div>
          )}

          {/* Redundant Sources Notice */}
          {report.redundant_sources.length > 0 && (
            <div className="p-2.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              <div className="flex items-center space-x-1.5 font-semibold text-xs mb-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Redundantly Supported</span>
              </div>
              <p className="text-[11px] font-sans">
                Conclusion survives removal of: {report.redundant_sources.join(', ')} due to independent corroborating documents.
              </p>
            </div>
          )}

          {/* Detailed Ablation Table */}
          <div className="pt-2">
            <span className="text-[10px] text-neutral-500 uppercase block mb-1">Source Removal Simulation Log</span>
            <div className="space-y-1">
              {report.ablation_results.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-1 px-2 rounded bg-graphite-900 border border-graphite-800 text-[11px]"
                >
                  <span className="text-neutral-300">Excluding {item.excluded_document_id}:</span>
                  <span
                    className={`font-semibold ${
                      item.conclusion_survived ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {item.conclusion_survived ? '✓ Conclusion Maintained' : '✗ Conclusion Blocked'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
