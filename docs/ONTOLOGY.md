# NOESIS Evidence-Centric Ontology Specification

## 1. Core Ontological Schema

The NOESIS ontology is specifically engineered to model scientific and investigative claims while preserving full provenance and handling contradictions.

### Node Definitions

#### 1. `Entity`
Represents an identified domain concept, agent, or artifact.
- `id` (`str`): Unique canonical identifier (e.g., `ent_dr_alyssa_vance`).
- `canonical_name` (`str`): Standardized human-readable label (e.g., `"Dr. Alyssa Vance"`).
- `type` (`str`): Entity category (`PERSON`, `ORGANIZATION`, `TECHNOLOGY`, `PROJECT`, `PUBLICATION`, `LOCATION`).
- `aliases` (`List[str]`): Recognized synonyms or alternate names.
- `metadata` (`Dict[str, Any]`): Optional auxiliary properties.

#### 2. `Claim`
Represents a discrete propositional assertion relating two entities.
- `id` (`str`): Deterministic SHA-256 fingerprint.
- `subject_id` (`str`): Identifier of the subject `Entity`.
- `predicate` (`str`): Canonical relationship type (`FOUNDED`, `WORKED_ON`, `DEVELOPED`, `EMPLOYED_BY`, `COLLABORATED_WITH`, `AUTHORED`, `PUBLISHED`, `ACQUIRED`, `FUNDED`, `LOCATED_IN`, `USES`).
- `object_id` (`str`): Identifier of the object `Entity`.
- `polarity` (`str`): Assertion status: `"affirmed"` (positive assertion) or `"negated"` (explicit denial/refutation).
- `temporal_scope` (`Optional[str]`): Time period during which the assertion applies (e.g., `"2021-2023"`).
- `confidence` (`float`): Calculated support score in $[0.0, 1.0]$.
- `evidence_ids` (`List[str]`): List of supporting `Evidence` identifiers.

#### 3. `Evidence`
Represents an empirical grounding record tying a claim to a source text passage.
- `id` (`str`): Unique evidence identifier (e.g., `ev_doc001_01`).
- `claim_id` (`str`): Identifier of the substantiated `Claim`.
- `document_id` (`str`): Identifier of the source `Document`.
- `quote` (`str`): Exact verbatim text extracted from the document.
- `page` (`Optional[int]`): Source page number if applicable.
- `chunk_id` (`Optional[str]`): Text chunk identifier.
- `char_offset_start` (`int`): Starting character offset in the document's raw text.
- `char_offset_end` (`int`): Ending character offset in the document's raw text.
- `confidence` (`float`): Quality indicator of the extraction.

#### 4. `Document`
Represents the provenance origin of evidence.
- `id` (`str`): Unique document identifier (e.g., `DOC_001`).
- `title` (`str`): Document title.
- `source_type` (`str`): Format/origin (`"txt"`, `"pdf"`, `"synthetic"`).
- `publication_date` (`Optional[str]`): ISO date string.
- `source_uri` (`Optional[str]`): Reference URI.
- `content_hash` (`str`): SHA-256 digest of the entire raw text.
- `raw_text` (`str`): Complete unedited text content.
- `metadata` (`Dict[str, Any]`): Additional context (e.g., synthetic tags).

---

## 2. Relationships

```
(Entity)    --[:SUBJECT_OF]--------> (Claim)
(Claim)     --[:OBJECT]------------> (Entity)
(Claim)     --[:SUPPORTED_BY]------> (Evidence)
(Evidence)  --[:FROM_DOCUMENT]-----> (Document)
(Claim)     --[:CONTRADICTS]-------> (Claim)
```

---

## 3. Deterministic Claim Fingerprinting

To avoid duplicate representations of identical factual assertions across disparate documents, claim IDs are deterministically generated via SHA-256:

$$\text{payload} = \text{lower}(s) + \text{"|"} + \text{upper}(p) + \text{"|"} + \text{lower}(o) + \text{"|"} + \text{lower}(\text{pol}) + \text{"|"} + (\text{temp} \text{ or } \text{""})$$
$$\text{id} = \text{"clm\_"} + \text{SHA256}(\text{payload})[:16]$$

This ensures that repeated extraction across documents resolves to the exact same Claim node, aggregating multiple `Evidence` links automatically.

---

## 4. Contradiction Model

Two claims $C_1$ and $C_2$ are marked with `CONTRADICTS` if:
1. They share identical $(s, p, o)$ and overlapping `temporal_scope`, but one has `polarity = "affirmed"` and the other `polarity = "negated"`.
2. They represent single-valued attributes (e.g., `HEADQUARTERED_IN`, `PRIMARY_DIRECTOR`) for the same subject and temporal window, but target divergent objects.
