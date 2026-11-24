"""Neo4j Persistent Graph Store Repository."""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.config import settings
from backend.app.graph.base import BaseGraphRepository
from backend.app.ontology.models import Claim, Document, Entity, EntityType, Evidence, Polarity

logger = logging.getLogger("noesis.graph.neo4j")


class Neo4jGraphRepository(BaseGraphRepository):
    """Neo4j Community persistent graph store using the official Bolt driver."""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self._driver = None
        self._initialize_driver()

    def _initialize_driver(self):
        try:
            from neo4j import GraphDatabase
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
            self._initialize_schema()
            logger.info("Connected to Neo4j successfully at %s", self.uri)
        except Exception as e:
            logger.warning("Neo4j driver connection failed: %s", str(e))
            self._driver = None

    def _initialize_schema(self):
        """Idempotently sets up uniqueness constraints and indexes."""
        if not self._driver:
            return
        queries = [
            "CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT claim_id_unique IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.id IS UNIQUE",
            "CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE INDEX entity_canonical_name IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name)",
            "CREATE INDEX claim_predicate IF NOT EXISTS FOR (c:Claim) ON (c.predicate)",
        ]
        with self._driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    logger.debug("Constraint/Index notice: %s", e)

    def get_storage_mode(self) -> str:
        return "neo4j"

    def is_healthy(self) -> bool:
        if not self._driver:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self):
        if self._driver:
            self._driver.close()

    def clear(self) -> None:
        if not self._driver:
            return
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def add_entity(self, entity: Entity) -> Entity:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        query = """
        MERGE (e:Entity {id: $id})
        SET e.canonical_name = $canonical_name,
            e.type = $type,
            e.aliases = $aliases,
            e.description = $description
        RETURN e.id
        """
        with self._driver.session() as session:
            session.run(
                query,
                id=entity.id,
                canonical_name=entity.canonical_name,
                type=entity.type.value,
                aliases=entity.aliases,
                description=entity.description or "",
            )
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        if not self._driver:
            return None
        query = "MATCH (e:Entity {id: $id}) RETURN e"
        with self._driver.session() as session:
            record = session.run(query, id=entity_id).single()
            if not record:
                return None
            props = record["e"]
            return Entity(
                id=props["id"],
                canonical_name=props["canonical_name"],
                type=EntityType(props["type"]),
                aliases=props.get("aliases", []),
                description=props.get("description", ""),
            )

    def list_entities(self, type_filter: Optional[str] = None) -> List[Entity]:
        if not self._driver:
            return []
        if type_filter:
            query = "MATCH (e:Entity {type: $type}) RETURN e"
            params = {"type": type_filter.upper()}
        else:
            query = "MATCH (e:Entity) RETURN e"
            params = {}

        results = []
        with self._driver.session() as session:
            records = session.run(query, **params)
            for r in records:
                props = r["e"]
                results.append(
                    Entity(
                        id=props["id"],
                        canonical_name=props["canonical_name"],
                        type=EntityType(props["type"]),
                        aliases=props.get("aliases", []),
                        description=props.get("description", ""),
                    )
                )
        return results

    def add_claim(self, claim: Claim) -> Claim:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        query = """
        MERGE (s:Entity {id: $subject_id})
        MERGE (o:Entity {id: $object_id})
        MERGE (c:Claim {id: $id})
        SET c.predicate = $predicate,
            c.polarity = $polarity,
            c.temporal_scope = $temporal_scope,
            c.confidence = $confidence,
            c.subject_id = $subject_id,
            c.object_id = $object_id
        MERGE (s)-[:SUBJECT_OF]->(c)
        MERGE (c)-[:OBJECT]->(o)
        RETURN c.id
        """
        with self._driver.session() as session:
            session.run(
                query,
                id=claim.id,
                subject_id=claim.subject_id,
                object_id=claim.object_id,
                predicate=claim.predicate.upper(),
                polarity=claim.polarity.value,
                temporal_scope=claim.temporal_scope or "",
                confidence=claim.confidence,
            )
        return claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        if not self._driver:
            return None
        query = """
        MATCH (c:Claim {id: $id})
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(ev:Evidence)
        OPTIONAL MATCH (c)-[:CONTRADICTS]-(contra:Claim)
        RETURN c, collect(DISTINCT ev.id) AS ev_ids, collect(DISTINCT contra.id) AS contra_ids
        """
        with self._driver.session() as session:
            record = session.run(query, id=claim_id).single()
            if not record:
                return None
            props = record["c"]
            return Claim(
                id=props["id"],
                subject_id=props["subject_id"],
                predicate=props["predicate"],
                object_id=props["object_id"],
                polarity=Polarity(props["polarity"]),
                temporal_scope=props.get("temporal_scope") or None,
                confidence=props.get("confidence", 1.0),
                evidence_ids=record["ev_ids"],
                contradiction_ids=record["contra_ids"],
            )

    def list_claims(
        self,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> List[Claim]:
        if not self._driver:
            return []
        conditions = []
        params = {}
        if subject_id:
            conditions.append("c.subject_id = $subject_id")
            params["subject_id"] = subject_id
        if predicate:
            conditions.append("c.predicate = $predicate")
            params["predicate"] = predicate.upper()
        if object_id:
            conditions.append("c.object_id = $object_id")
            params["object_id"] = object_id

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"""
        MATCH (c:Claim)
        {where_clause}
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(ev:Evidence)
        OPTIONAL MATCH (c)-[:CONTRADICTS]-(contra:Claim)
        RETURN c, collect(DISTINCT ev.id) AS ev_ids, collect(DISTINCT contra.id) AS contra_ids
        """
        results = []
        with self._driver.session() as session:
            for record in session.run(query, **params):
                props = record["c"]
                results.append(
                    Claim(
                        id=props["id"],
                        subject_id=props["subject_id"],
                        predicate=props["predicate"],
                        object_id=props["object_id"],
                        polarity=Polarity(props["polarity"]),
                        temporal_scope=props.get("temporal_scope") or None,
                        confidence=props.get("confidence", 1.0),
                        evidence_ids=record["ev_ids"],
                        contradiction_ids=record["contra_ids"],
                    )
                )
        return results

    def add_evidence(self, evidence: Evidence) -> Evidence:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        query = """
        MERGE (c:Claim {id: $claim_id})
        MERGE (d:Document {id: $document_id})
        MERGE (ev:Evidence {id: $id})
        SET ev.quote = $quote,
            ev.page = $page,
            ev.char_offset_start = $start,
            ev.char_offset_end = $end,
            ev.confidence = $confidence,
            ev.claim_id = $claim_id,
            ev.document_id = $document_id
        MERGE (c)-[:SUPPORTED_BY]->(ev)
        MERGE (ev)-[:FROM_DOCUMENT]->(d)
        RETURN ev.id
        """
        with self._driver.session() as session:
            session.run(
                query,
                id=evidence.id,
                claim_id=evidence.claim_id,
                document_id=evidence.document_id,
                quote=evidence.quote,
                page=evidence.page or 1,
                start=evidence.char_offset_start,
                end=evidence.char_offset_end,
                confidence=evidence.confidence,
            )
        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        if not self._driver:
            return None
        query = "MATCH (ev:Evidence {id: $id}) RETURN ev"
        with self._driver.session() as session:
            record = session.run(query, id=evidence_id).single()
            if not record:
                return None
            props = record["ev"]
            return Evidence(
                id=props["id"],
                claim_id=props["claim_id"],
                document_id=props["document_id"],
                quote=props["quote"],
                page=props.get("page", 1),
                char_offset_start=props["char_offset_start"],
                char_offset_end=props["char_offset_end"],
                confidence=props.get("confidence", 1.0),
            )

    def get_evidence_for_claim(self, claim_id: str) -> List[Evidence]:
        if not self._driver:
            return []
        query = "MATCH (:Claim {id: $claim_id})-[:SUPPORTED_BY]->(ev:Evidence) RETURN ev"
        results = []
        with self._driver.session() as session:
            for record in session.run(query, claim_id=claim_id):
                props = record["ev"]
                results.append(
                    Evidence(
                        id=props["id"],
                        claim_id=props["claim_id"],
                        document_id=props["document_id"],
                        quote=props["quote"],
                        page=props.get("page", 1),
                        char_offset_start=props["char_offset_start"],
                        char_offset_end=props["char_offset_end"],
                        confidence=props.get("confidence", 1.0),
                    )
                )
        return results

    def add_document(self, document: Document) -> Document:
        if not self._driver:
            raise RuntimeError("Neo4j driver not connected")
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.source_type = $source_type,
            d.publication_date = $pub_date,
            d.source_uri = $source_uri,
            d.content_hash = $content_hash,
            d.ingestion_timestamp = $ingest_time,
            d.raw_text = $raw_text
        RETURN d.id
        """
        with self._driver.session() as session:
            session.run(
                query,
                id=document.id,
                title=document.title,
                source_type=document.source_type,
                pub_date=document.publication_date or "",
                source_uri=document.source_uri or "",
                content_hash=document.content_hash,
                ingest_time=document.ingestion_timestamp,
                raw_text=document.raw_text,
            )
        return document

    def get_document(self, document_id: str) -> Optional[Document]:
        if not self._driver:
            return None
        query = "MATCH (d:Document {id: $id}) RETURN d"
        with self._driver.session() as session:
            record = session.run(query, id=document_id).single()
            if not record:
                return None
            props = record["d"]
            return Document(
                id=props["id"],
                title=props["title"],
                source_type=props.get("source_type", "synthetic"),
                publication_date=props.get("publication_date") or None,
                source_uri=props.get("source_uri") or None,
                content_hash=props["content_hash"],
                ingestion_timestamp=props["ingestion_timestamp"],
                raw_text=props["raw_text"],
            )

    def list_documents(self) -> List[Document]:
        if not self._driver:
            return []
        query = "MATCH (d:Document) RETURN d"
        results = []
        with self._driver.session() as session:
            for record in session.run(query):
                props = record["d"]
                results.append(
                    Document(
                        id=props["id"],
                        title=props["title"],
                        source_type=props.get("source_type", "synthetic"),
                        publication_date=props.get("publication_date") or None,
                        source_uri=props.get("source_uri") or None,
                        content_hash=props["content_hash"],
                        ingestion_timestamp=props["ingestion_timestamp"],
                        raw_text=props["raw_text"],
                    )
                )
        return results

    def add_contradiction(self, claim_id_1: str, claim_id_2: str) -> None:
        if not self._driver:
            return
        query = """
        MERGE (c1:Claim {id: $c1})
        MERGE (c2:Claim {id: $c2})
        MERGE (c1)-[:CONTRADICTS]->(c2)
        MERGE (c2)-[:CONTRADICTS]->(c1)
        """
        with self._driver.session() as session:
            session.run(query, c1=claim_id_1, c2=claim_id_2)

    def get_contradictions(self) -> List[Tuple[Claim, Claim]]:
        if not self._driver:
            return []
        query = """
        MATCH (c1:Claim)-[:CONTRADICTS]->(c2:Claim)
        WHERE c1.id < c2.id
        RETURN c1, c2
        """
        results = []
        with self._driver.session() as session:
            for r in session.run(query):
                p1 = r["c1"]
                p2 = r["c2"]
                c1 = Claim(
                    id=p1["id"],
                    subject_id=p1["subject_id"],
                    predicate=p1["predicate"],
                    object_id=p1["object_id"],
                    polarity=Polarity(p1["polarity"]),
                    temporal_scope=p1.get("temporal_scope") or None,
                    confidence=p1.get("confidence", 1.0),
                )
                c2 = Claim(
                    id=p2["id"],
                    subject_id=p2["subject_id"],
                    predicate=p2["predicate"],
                    object_id=p2["object_id"],
                    polarity=Polarity(p2["polarity"]),
                    temporal_scope=p2.get("temporal_scope") or None,
                    confidence=p2.get("confidence", 1.0),
                )
                results.append((c1, c2))
        return results

    def get_adjacent_claims(
        self,
        entity_id: str,
        direction: str = "outgoing",
        predicate: Optional[str] = None,
    ) -> List[Tuple[Claim, Entity]]:
        if not self._driver:
            return []
        results = []
        pred_filter = "AND c.predicate = $predicate" if predicate else ""
        params = {"entity_id": entity_id}
        if predicate:
            params["predicate"] = predicate.upper()

        if direction in ("outgoing", "both"):
            q_out = f"""
            MATCH (e:Entity {id: $entity_id})-[:SUBJECT_OF]->(c:Claim)-[:OBJECT]->(target:Entity)
            WHERE 1=1 {pred_filter}
            RETURN c, target
            """
            with self._driver.session() as session:
                for r in session.run(q_out, **params):
                    cp = r["c"]
                    tp = r["target"]
                    claim = Claim(
                        id=cp["id"],
                        subject_id=cp["subject_id"],
                        predicate=cp["predicate"],
                        object_id=cp["object_id"],
                        polarity=Polarity(cp["polarity"]),
                        temporal_scope=cp.get("temporal_scope") or None,
                        confidence=cp.get("confidence", 1.0),
                    )
                    target = Entity(
                        id=tp["id"],
                        canonical_name=tp["canonical_name"],
                        type=EntityType(tp["type"]),
                        aliases=tp.get("aliases", []),
                        description=tp.get("description", ""),
                    )
                    results.append((claim, target))

        if direction in ("incoming", "both"):
            q_in = f"""
            MATCH (source:Entity)-[:SUBJECT_OF]->(c:Claim)-[:OBJECT]->(e:Entity {id: $entity_id})
            WHERE 1=1 {pred_filter}
            RETURN c, source
            """
            with self._driver.session() as session:
                for r in session.run(q_in, **params):
                    cp = r["c"]
                    sp = r["source"]
                    claim = Claim(
                        id=cp["id"],
                        subject_id=cp["subject_id"],
                        predicate=cp["predicate"],
                        object_id=cp["object_id"],
                        polarity=Polarity(cp["polarity"]),
                        temporal_scope=cp.get("temporal_scope") or None,
                        confidence=cp.get("confidence", 1.0),
                    )
                    source = Entity(
                        id=sp["id"],
                        canonical_name=sp["canonical_name"],
                        type=EntityType(sp["type"]),
                        aliases=sp.get("aliases", []),
                        description=sp.get("description", ""),
                    )
                    results.append((claim, source))

        return results

    def get_full_graph(self) -> Dict[str, Any]:
        """Fetches full graph elements directly from Neo4j."""
        if not self._driver:
            return {"storage_mode": "neo4j (unreachable)", "elements": {"nodes": [], "edges": []}}

        nodes = []
        edges = []
        with self._driver.session() as session:
            # Entities
            for r in session.run("MATCH (e:Entity) RETURN e"):
                ep = r["e"]
                nodes.append({
                    "data": {
                        "id": ep["id"],
                        "label": ep["canonical_name"],
                        "type": "Entity",
                        "entity_type": ep["type"],
                        "description": ep.get("description", ""),
                        "aliases": ep.get("aliases", []),
                    }
                })
            # Claims
            for r in session.run("MATCH (c:Claim) RETURN c"):
                cp = r["c"]
                nodes.append({
                    "data": {
                        "id": cp["id"],
                        "label": f"{cp['predicate']} ({cp['polarity']})",
                        "type": "Claim",
                        "predicate": cp["predicate"],
                        "polarity": cp["polarity"],
                        "temporal_scope": cp.get("temporal_scope", ""),
                        "confidence": cp.get("confidence", 1.0),
                    }
                })
                edges.append({
                    "data": {
                        "id": f"{cp['subject_id']}_subj_{cp['id']}",
                        "source": cp["subject_id"],
                        "target": cp["id"],
                        "label": "SUBJECT_OF",
                        "rel_type": "SUBJECT_OF",
                    }
                })
                edges.append({
                    "data": {
                        "id": f"{cp['id']}_obj_{cp['object_id']}",
                        "source": cp["id"],
                        "target": cp["object_id"],
                        "label": "OBJECT",
                        "rel_type": "OBJECT",
                    }
                })
            # Documents
            for r in session.run("MATCH (d:Document) RETURN d"):
                dp = r["d"]
                nodes.append({
                    "data": {
                        "id": dp["id"],
                        "label": dp["title"],
                        "type": "Document",
                        "source_type": dp.get("source_type", "synthetic"),
                        "content_hash": dp["content_hash"],
                    }
                })
            # Evidence
            for r in session.run("MATCH (ev:Evidence) RETURN ev"):
                evp = r["ev"]
                nodes.append({
                    "data": {
                        "id": evp["id"],
                        "label": f"Quote [{evp['char_offset_start']}:{evp['char_offset_end']}]",
                        "type": "Evidence",
                        "quote": evp["quote"],
                        "page": evp.get("page", 1),
                        "offsets": [evp["char_offset_start"], evp["char_offset_end"]],
                        "confidence": evp.get("confidence", 1.0),
                    }
                })
                edges.append({
                    "data": {
                        "id": f"{evp['claim_id']}_supp_{evp['id']}",
                        "source": evp["claim_id"],
                        "target": evp["id"],
                        "label": "SUPPORTED_BY",
                        "rel_type": "SUPPORTED_BY",
                    }
                })
                edges.append({
                    "data": {
                        "id": f"{evp['id']}_from_{evp['document_id']}",
                        "source": evp["id"],
                        "target": evp["document_id"],
                        "label": "FROM_DOCUMENT",
                        "rel_type": "FROM_DOCUMENT",
                    }
                })
            # Contradictions
            for r in session.run("MATCH (c1:Claim)-[:CONTRADICTS]->(c2:Claim) WHERE c1.id < c2.id RETURN c1.id, c2.id"):
                edges.append({
                    "data": {
                        "id": f"{r['c1.id']}_contra_{r['c2.id']}",
                        "source": r["c1.id"],
                        "target": r["c2.id"],
                        "label": "CONTRADICTS",
                        "rel_type": "CONTRADICTS",
                    }
                })

        return {
            "storage_mode": self.get_storage_mode(),
            "elements": {"nodes": nodes, "edges": edges},
        }
