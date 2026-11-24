import {
  AblationReport,
  Claim,
  Document,
  Entity,
  Evidence,
  GraphPayload,
  HealthData,
  ReasoningResult,
  StructuredQueryPlan,
} from '../types';

const API_BASE = '/api/v1';

export const api = {
  async getHealth(): Promise<HealthData> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getGraph(): Promise<GraphPayload> {
    const res = await fetch(`${API_BASE}/graph`);
    if (!res.ok) throw new Error(`Fetch graph failed: ${res.statusText}`);
    return res.json();
  },

  async getDocuments(): Promise<Document[]> {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) throw new Error(`Fetch documents failed: ${res.statusText}`);
    return res.json();
  },

  async getDocument(id: string): Promise<Document> {
    const res = await fetch(`${API_BASE}/documents/${id}`);
    if (!res.ok) throw new Error(`Fetch document ${id} failed`);
    return res.json();
  },

  async getEntities(type?: string): Promise<Entity[]> {
    const url = type ? `${API_BASE}/entities?type=${encodeURIComponent(type)}` : `${API_BASE}/entities`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Fetch entities failed: ${res.statusText}`);
    return res.json();
  },

  async getEntity(id: string): Promise<Entity> {
    const res = await fetch(`${API_BASE}/entities/${id}`);
    if (!res.ok) throw new Error(`Fetch entity ${id} failed`);
    return res.json();
  },

  async getClaim(id: string): Promise<Claim> {
    const res = await fetch(`${API_BASE}/claims/${id}`);
    if (!res.ok) throw new Error(`Fetch claim ${id} failed`);
    return res.json();
  },

  async getClaimEvidence(claimId: string): Promise<Evidence[]> {
    const res = await fetch(`${API_BASE}/claims/${claimId}/evidence`);
    if (!res.ok) throw new Error(`Fetch evidence for claim ${claimId} failed`);
    return res.json();
  },

  async executeQuery(plan: StructuredQueryPlan): Promise<ReasoningResult> {
    const res = await fetch(`${API_BASE}/query/structured`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(plan),
    });
    if (!res.ok) throw new Error(`Query execution failed: ${res.statusText}`);
    return res.json();
  },

  async runCounterfactual(plan: StructuredQueryPlan, targetEntityId: string): Promise<AblationReport> {
    const res = await fetch(`${API_BASE}/counterfactual`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_plan: plan, target_entity_id: targetEntityId }),
    });
    if (!res.ok) throw new Error(`Counterfactual ablation failed: ${res.statusText}`);
    return res.json();
  },

  async getContradictions(): Promise<any> {
    const res = await fetch(`${API_BASE}/contradictions`);
    if (!res.ok) throw new Error(`Fetch contradictions failed: ${res.statusText}`);
    return res.json();
  },
};
