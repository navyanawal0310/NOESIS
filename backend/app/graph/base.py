"""Base Graph Repository Abstract Interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.ontology.models import Claim, Document, Entity, Evidence


class BaseGraphRepository(ABC):
    """Abstract base class defining the contract for graph storage backends."""

    @abstractmethod
    def get_storage_mode(self) -> str:
        """Returns the storage identifier ('neo4j' or 'in_memory')."""
        pass

    @abstractmethod
    def is_healthy(self) -> bool:
        """Checks if the storage backend is active and reachable."""
        pass

    @abstractmethod
    def add_entity(self, entity: Entity) -> Entity:
        """Idempotently adds or updates an entity."""
        pass

    @abstractmethod
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieves an entity by its identifier."""
        pass

    @abstractmethod
    def list_entities(self, type_filter: Optional[str] = None) -> List[Entity]:
        """Lists all entities, optionally filtered by type."""
        pass

    @abstractmethod
    def add_claim(self, claim: Claim) -> Claim:
        """Idempotently adds or updates a claim."""
        pass

    @abstractmethod
    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Retrieves a claim by its fingerprint ID."""
        pass

    @abstractmethod
    def list_claims(
        self,
        subject_id: Optional[str] = None,
        predicate: Optional[str] = None,
        object_id: Optional[str] = None,
    ) -> List[Claim]:
        """Queries claims by optional subject, predicate, or object filters."""
        pass

    @abstractmethod
    def add_evidence(self, evidence: Evidence) -> Evidence:
        """Stores an evidence record and links it to its claim."""
        pass

    @abstractmethod
    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieves an evidence record by its ID."""
        pass

    @abstractmethod
    def get_evidence_for_claim(self, claim_id: str) -> List[Evidence]:
        """Retrieves all supporting evidence records for a given claim."""
        pass

    @abstractmethod
    def add_document(self, document: Document) -> Document:
        """Stores a source document record."""
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieves a document by its ID."""
        pass

    @abstractmethod
    def list_documents(self) -> List[Document]:
        """Lists all ingested documents."""
        pass

    @abstractmethod
    def add_contradiction(self, claim_id_1: str, claim_id_2: str) -> None:
        """Registers a bidirectional CONTRADICTS relationship between two claims."""
        pass

    @abstractmethod
    def get_contradictions(self) -> List[Tuple[Claim, Claim]]:
        """Returns all pairs of contradictory claims."""
        pass

    @abstractmethod
    def get_adjacent_claims(
        self,
        entity_id: str,
        direction: str = "outgoing",
        predicate: Optional[str] = None,
    ) -> List[Tuple[Claim, Entity]]:
        """Retrieves claims adjacent to an entity along with the connected target entity.

        Args:
            entity_id: Starting entity ID.
            direction: 'outgoing' (entity is subject), 'incoming' (entity is object), or 'both'.
            predicate: Optional predicate name filter.

        Returns:
            List of (Claim, ConnectedEntity) tuples.
        """
        pass

    @abstractmethod
    def get_full_graph(self) -> Dict[str, Any]:
        """Returns the full graph representation with nodes and edges."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clears all stored graph data."""
        pass
