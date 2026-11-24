import React, { useEffect, useState } from 'react';
import { Claim, Entity, HealthData, IngestionJob, LLMStatus, ReasoningResult, StructuredQueryPlan } from './types';
import { api } from './services/api';
import { Header } from './components/Header';
import { InvestigationWorkspace } from './components/InvestigationWorkspace';
import { KnowledgeGraphExplorer } from './components/KnowledgeGraphExplorer';
import { SourceVault } from './components/SourceVault';
import { EntityDetailModal } from './components/EntityDetailModal';
import { ClaimDetailModal } from './components/ClaimDetailModal';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'workspace' | 'graph' | 'vault'>('workspace');
  const [health, setHealth] = useState<HealthData | null>(null);
  const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [vaultDocId, setVaultDocId] = useState<string | null>(null);
  const [activeJob, setActiveJob] = useState<IngestionJob | null>(null);
  const [lastRefreshTimestamp, setLastRefreshTimestamp] = useState<number>(Date.now());

  const refreshAll = async () => {
    try {
      const [h, ents] = await Promise.all([api.getHealth(), api.getEntities()]);
      setHealth(h);
      setEntities(ents);
      setLastRefreshTimestamp(Date.now());
    } catch (err) {
      console.error('Error refreshing telemetry after ingestion:', err);
    }
  };

  useEffect(() => {
    // Initial telemetry fetch
    refreshAll();
    api
      .getLLMStatus()
      .then((s) => setLlmStatus(s))
      .catch((err) => console.error('LLM status fetch error:', err));
  }, []);

  const handleSelectDocument = (docId: string) => {
    setVaultDocId(docId);
    setActiveTab('vault');
  };

  const handleExecuteQuery = async (plan: StructuredQueryPlan): Promise<ReasoningResult> => {
    return await api.executeQuery(plan);
  };

  const handleIngestionComplete = (_docId?: string, _result?: any) => {
    refreshAll();
  };

  return (
    <div className="min-h-screen bg-graphite-950 text-neutral-200 flex flex-col font-sans">
      <Header
        health={health}
        llmStatus={llmStatus}
        activeJob={activeJob}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'workspace' && (
          <InvestigationWorkspace
            entities={entities}
            llmStatus={llmStatus}
            onSelectEntity={(ent) => setSelectedEntity(ent)}
            onSelectClaim={(clm) => setSelectedClaim(clm)}
            onSelectDocument={handleSelectDocument}
            onNavigateToGraph={() => setActiveTab('graph')}
            onExecuteQuery={handleExecuteQuery}
          />
        )}

        {activeTab === 'graph' && (
          <KnowledgeGraphExplorer
            onSelectEntity={(ent) => setSelectedEntity(ent)}
            onSelectClaim={(clm) => setSelectedClaim(clm)}
            onSelectDocument={handleSelectDocument}
            lastRefreshTimestamp={lastRefreshTimestamp}
          />
        )}

        {activeTab === 'vault' && (
          <SourceVault
            initialDocumentId={vaultDocId}
            llmStatus={llmStatus}
            onIngestionComplete={handleIngestionComplete}
            onActiveJobChange={setActiveJob}
          />
        )}
      </main>

      {/* Modals */}
      <EntityDetailModal entity={selectedEntity} onClose={() => setSelectedEntity(null)} />
      <ClaimDetailModal
        claim={selectedClaim}
        onClose={() => setSelectedClaim(null)}
        onSelectDocument={handleSelectDocument}
      />
    </div>
  );
};

export default App;
