import React, { useEffect, useState } from 'react';
import { Claim, Entity, HealthData, ReasoningResult, StructuredQueryPlan } from './types';
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
  const [entities, setEntities] = useState<Entity[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<Claim | null>(null);
  const [vaultDocId, setVaultDocId] = useState<string | null>(null);

  useEffect(() => {
    // Initial telemetry fetch
    api
      .getHealth()
      .then((h) => setHealth(h))
      .catch((err) => console.error('Health fetch error:', err));

    api
      .getEntities()
      .then((ents) => setEntities(ents))
      .catch((err) => console.error('Entities fetch error:', err));
  }, []);

  const handleSelectDocument = (docId: string) => {
    setVaultDocId(docId);
    setActiveTab('vault');
  };

  const handleExecuteQuery = async (plan: StructuredQueryPlan): Promise<ReasoningResult> => {
    return await api.executeQuery(plan);
  };

  return (
    <div className="min-h-screen bg-graphite-950 text-neutral-200 flex flex-col font-sans">
      <Header health={health} activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'workspace' && (
          <InvestigationWorkspace
            entities={entities}
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
          />
        )}

        {activeTab === 'vault' && <SourceVault initialDocumentId={vaultDocId} />}
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
