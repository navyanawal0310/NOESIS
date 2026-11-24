import {
  AblationReport,
  Claim,
  Document,
  DocumentStatusResponse,
  DocumentUploadResponse,
  Entity,
  Evidence,
  GroundedAnswer,
  GraphPayload,
  HealthData,
  LLMStatus,
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

  async getLLMStatus(): Promise<LLMStatus> {
    const res = await fetch(`${API_BASE}/llm/status`);
    if (!res.ok) throw new Error(`LLM status check failed: ${res.statusText}`);
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

  async uploadDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Document upload failed: ${res.statusText}`);
    }
    return res.json();
  },

  async ingestDocument(docId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/documents/${docId}/ingest`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Document ingestion failed: ${res.statusText}`);
    }
    return res.json();
  },

  async getDocumentStatus(docId: string): Promise<DocumentStatusResponse> {
    const res = await fetch(`${API_BASE}/documents/${docId}/status`);
    if (!res.ok) throw new Error(`Fetch document status ${docId} failed`);
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Query execution failed: ${res.statusText}`);
    }
    return res.json();
  },

  async executeNaturalQuery(
    question: string,
    maxHops: number = 3,
    useLlmSynthesis: boolean = false
  ): Promise<GroundedAnswer> {
    const res = await fetch(`${API_BASE}/query/natural`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        max_hops: maxHops,
        use_llm_synthesis: useLlmSynthesis,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `Natural query failed: ${res.statusText}`);
    }
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
