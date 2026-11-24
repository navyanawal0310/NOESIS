import React from 'react';
import { Database, ShieldCheck, Activity, Terminal, GitBranch, Layers, Cpu } from 'lucide-react';
import { HealthData, LLMStatus } from '../types';

interface HeaderProps {
  health: HealthData | null;
  llmStatus?: LLMStatus | null;
  activeTab: 'workspace' | 'graph' | 'vault';
  setActiveTab: (tab: 'workspace' | 'graph' | 'vault') => void;
}

export const Header: React.FC<HeaderProps> = ({ health, llmStatus, activeTab, setActiveTab }) => {
  return (
    <header className="border-b border-graphite-800 bg-graphite-900/90 backdrop-blur px-6 py-3 sticky top-0 z-40">
      <div className="flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded border border-amber-500/40 bg-amber-500/10 flex items-center justify-center">
              <Terminal className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono font-bold tracking-wider text-neutral-100 text-lg">NOESIS</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-graphite-800 text-amber-400 border border-amber-500/30">
                  v{health?.version || '1.0.0'}
                </span>
              </div>
              <p className="text-[11px] text-neutral-400 font-mono tracking-tight hidden sm:block">
                Neural-Ontological Evidence Synthesis & Inference System
              </p>
            </div>
          </div>

          <div className="h-6 w-px bg-graphite-800 hidden md:block" />

          {/* Navigation Tabs */}
          <nav className="flex space-x-1">
            <button
              onClick={() => setActiveTab('workspace')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                activeTab === 'workspace'
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/40'
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-graphite-800/60 border border-transparent'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Workspace</span>
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                activeTab === 'graph'
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/40'
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-graphite-800/60 border border-transparent'
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>Graph Explorer</span>
            </button>
            <button
              onClick={() => setActiveTab('vault')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded text-xs font-mono transition-colors ${
                activeTab === 'vault'
                  ? 'bg-amber-500/15 text-amber-400 border border-amber-500/40'
                  : 'text-neutral-400 hover:text-neutral-200 hover:bg-graphite-800/60 border border-transparent'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Source Vault</span>
            </button>
          </nav>
        </div>

        {/* Telemetry Badges */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          {/* LLM Status Indicator */}
          <div
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded border ${
              llmStatus?.available
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
            }`}
            title={llmStatus?.details || (llmStatus?.available ? 'Local LLM operational' : 'Ollama daemon offline')}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span className="text-neutral-400">LLM:</span>
            <span>
              {llmStatus?.available ? `${llmStatus.configured_model} (Online)` : 'Offline'}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-graphite-850 border border-graphite-800">
            <Database className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-neutral-400">Mode:</span>
            <span className="text-amber-400 font-semibold">{health?.storage_mode || 'connecting...'}</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-graphite-850 border border-graphite-800 hidden lg:flex">
            <span className="text-neutral-400">Entities:</span>
            <span className="text-neutral-200">{health?.total_entities ?? 0}</span>
            <span className="text-neutral-600">|</span>
            <span className="text-neutral-400">Claims:</span>
            <span className="text-neutral-200">{health?.total_claims ?? 0}</span>
          </div>

          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Lexically Grounded</span>
          </div>
        </div>
      </div>
    </header>
  );
};
