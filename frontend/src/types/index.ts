export type EntityType =
  | 'PERSON'
  | 'ORGANIZATION'
  | 'TECHNOLOGY'
  | 'PROJECT'
  | 'PUBLICATION'
  | 'LOCATION'
  | 'CONCEPT';

export type Polarity = 'affirmed' | 'negated';

export interface Entity {
  id: string;
  canonical_name: string;
  type: EntityType;
  aliases: string[];
  description?: string;
  metadata?: Record<string, any>;
}

export interface Evidence {
  id: string;
  claim_id: string;
  document_id: string;
  quote: string;
  page?: number;
  chunk_id?: string;
  char_offset_start: number;
  char_offset_end: number;
  confidence: number;
}

export interface Claim {
  id: string;
  subject_id: string;
  predicate: string;
  object_id: string;
  polarity: Polarity;
  temporal_scope?: string;
  confidence: number;
  evidence_ids: string[];
  contradiction_ids: string[];
}

export interface Document {
  id: string;
  title: string;
  source_type: string;
  publication_date?: string;
  source_uri?: string;
  content_hash: string;
  ingestion_timestamp: string;
  raw_text: string;
  metadata?: Record<string, any>;
}

export interface TraversalStep {
  predicate: string;
  direction: 'outgoing' | 'incoming' | 'both';
  target_type?: EntityType;
}

export interface StructuredQueryPlan {
  start_entity: string;
  steps: TraversalStep[];
  return_type?: EntityType;
  predicate_filter?: string;
  max_hops: number;
  excluded_document_ids?: string[];
}

export interface PathSegment {
  from_entity: Entity;
  claim: Claim;
  to_entity: Entity;
  direction: string;
  evidence: Evidence[];
  segment_confidence: number;
  is_disputed: boolean;
  contradictions: Claim[];
}

export interface ReasoningPath {
  segments: PathSegment[];
  terminal_entity: Entity;
  hop_count: number;
  path_confidence: number;
  supporting_document_ids: string[];
}

export interface ReasoningResult {
  query_id: string;
  status: 'success' | 'insufficient_evidence' | 'contradiction_detected';
  start_entity?: Entity;
  matching_entities: Entity[];
  paths: ReasoningPath[];
  hop_count: number;
  conflicting_claims: Claim[];
  evidence_records: Evidence[];
  execution_time_ms: number;
  confidence: number;
  robustness_score?: number;
  critical_documents: string[];
  explanation: string;
}

export interface HealthData {
  status: string;
  app_name: string;
  version: string;
  storage_mode: string;
  is_database_healthy: boolean;
  total_entities: number;
  total_claims: number;
  total_documents: number;
}

export interface GraphPayload {
  storage_mode: string;
  elements: {
    nodes: Array<{
      data: {
        id: string;
        label: string;
        type: 'Entity' | 'Claim' | 'Evidence' | 'Document';
        entity_type?: EntityType;
        predicate?: string;
        polarity?: string;
        [key: string]: any;
      };
    }>;
    edges: Array<{
      data: {
        id: string;
        source: string;
        target: string;
        label: string;
        rel_type: string;
      };
    }>;
  };
  stats?: {
    entities: number;
    claims: number;
    evidence: number;
    documents: number;
    contradictions: number;
  };
}

export interface AblationReport {
  target_entity_id: string;
  baseline_supported: boolean;
  total_supporting_documents: number;
  robustness_score: number;
  critical_sources: string[];
  redundant_sources: string[];
  ablation_results: Array<{
    excluded_document_id: string;
    conclusion_survived: boolean;
    active_paths_count: number;
  }>;
  summary: string;
}
