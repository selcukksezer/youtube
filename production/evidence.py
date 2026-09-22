"""Evidence checks shared by research and publication.

Search results are discovery signals. A claim becomes publishable only when
supporting records contain verified retrieval, a matching content hash, an
HTTPS source, and an in-context assessment quote. Independence is checked at
both publisher and registrable-domain levels; an adapter flag never skips
these checks.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from urllib.parse import urlsplit

_RETRIEVED_STATES = {"retrieved", "verified"}
_WIKIMEDIA_DOMAINS = {
    "wikipedia.org", "wikidata.org", "wikimedia.org",
    "wikimediafoundation.org", "mediawiki.org",
}
_SECOND_LEVEL_SUFFIXES = {
    "ac.uk", "co.uk", "gov.uk", "org.uk", "com.au", "net.au",
    "org.au", "co.jp", "co.nz", "co.za",
}


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _host(url: Any) -> str:
    host = (urlsplit(str(url or "")).hostname or "").casefold().strip(".")
    return host.removeprefix("www.")


def _is_wikimedia_host(host: str) -> bool:
    return any(host == domain or host.endswith("." + domain) for domain in _WIKIMEDIA_DOMAINS)


def domain_group(record: Mapping[str, Any]) -> str:
    """Return a stable registrable-domain/ownership group for an evidence row."""
    host = _host(record.get("url"))
    if not host:
        return ""
    if _is_wikimedia_host(host):
        # Wikipedia, Wikidata and Wikimedia have one ownership group.
        return "wikimedia"
    labels = [label for label in host.split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    suffix = ".".join(labels[-2:])
    if suffix in _SECOND_LEVEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _identity(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def publisher_group(record: Mapping[str, Any]) -> str:
    """Return publisher group; Wikimedia hosts are always one group."""
    domain = domain_group(record)
    if domain == "wikimedia":
        return domain
    return _identity(record.get("publisher")) or domain


def _valid_url(value: Any) -> bool:
    parsed = urlsplit(str(value or ""))
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname)


def validate_claim_record(record: Mapping[str, Any]) -> List[str]:
    """Return deterministic structural errors for one claim record."""
    errors: List[str] = []
    claim_id = normalize_text(record.get("claim_id"))
    if not claim_id:
        errors.append("missing_claim_id")
    if len(normalize_text(record.get("text"))) < 8:
        errors.append("claim_text_too_short:" + (claim_id or "unknown"))
    evidence_ids = record.get("evidence_ids") or []
    if not isinstance(evidence_ids, (list, tuple)):
        errors.append("invalid_evidence_ids:" + (claim_id or "unknown"))
    elif len(evidence_ids) != len(set(str(item) for item in evidence_ids)):
        errors.append("duplicate_claim_evidence_ids:" + (claim_id or "unknown"))
    return errors


def validate_evidence_record(record: Mapping[str, Any]) -> List[str]:
    """Return structural errors before a record is used as evidence."""
    errors: List[str] = []
    source_id = normalize_text(record.get("source_id"))
    if not source_id:
        errors.append("missing_source_id")
    if len(normalize_text(record.get("title"))) < 3:
        errors.append("source_title_too_short:" + (source_id or "unknown"))
    if not _valid_url(record.get("url")):
        errors.append("source_url_must_be_https:" + (source_id or "unknown"))
    if not domain_group(record):
        errors.append("source_domain_missing:" + (source_id or "unknown"))
    if not normalize_text(record.get("excerpt")):
        errors.append("source_excerpt_missing:" + (source_id or "unknown"))
    return errors


def _assessment_supports(source: Mapping[str, Any], claim: Mapping[str, Any], content: str) -> bool:
    expected_claim_hash = text_hash(str(claim.get("text") or ""))
    normalized_content = normalize_text(content)
    for assessment in source.get("assessments") or []:
        if not isinstance(assessment, Mapping):
            continue
        quote = normalize_text(assessment.get("quote"))
        if (
            str(assessment.get("claim_id") or "") == str(claim.get("claim_id") or "")
            and str(assessment.get("verdict") or "").casefold() == "supports"
            and str(assessment.get("claim_sha256") or "") == expected_claim_hash
            and len(quote) >= 20
            and quote in normalized_content
        ):
            return True
    return False


def _record_is_publishable(source: Mapping[str, Any], claim: Mapping[str, Any]) -> Tuple[bool, str]:
    source_id = normalize_text(source.get("source_id")) or "unknown"
    structural = validate_evidence_record(source)
    if structural:
        return False, structural[0]
    if normalize_text(source.get("retrieval_status")).casefold() not in _RETRIEVED_STATES:
        return False, "source_not_retrieved:" + source_id
    try:
        retrieved_at = datetime.fromisoformat(str(source.get("retrieved_at") or "").replace("Z", "+00:00"))
        if retrieved_at.tzinfo is None or retrieved_at > datetime.now(timezone.utc):
            return False, "source_retrieval_date_invalid:" + source_id
    except (TypeError, ValueError):
        return False, "source_retrieval_date_missing:" + source_id
    content = normalize_text(source.get("excerpt"))
    digest = text_hash(content)
    if str(source.get("content_sha256") or "") != digest:
        return False, "source_content_hash_mismatch:" + source_id
    if not _assessment_supports(source, claim, content):
        return False, "source_claim_assessment_missing:" + source_id
    return True, ""


def _independent_group_count(sources: List[Mapping[str, Any]]) -> int:
    """Merge common owners/domains/content, including transitive ownership."""
    parents: Dict[str, str] = {}

    def root(node: str) -> str:
        parents.setdefault(node, node)
        while node != parents[node]:
            parents[node] = parents[parents[node]]
            node = parents[node]
        return node

    nodes = []
    for source in sources:
        identities = (
            "publisher:" + publisher_group(source),
            "domain:" + domain_group(source),
            "content:" + text_hash(str(source.get("excerpt") or "")),
        )
        head = root(identities[0])
        for identity in identities[1:]:
            parents[root(identity)] = head
        nodes.append(identities[0])
    return len({root(node) for node in nodes})


def evaluate_evidence(brief: Mapping[str, Any]) -> Dict[str, Any]:
    """Evaluate every factual claim in a research brief.

    ``trusted_adapter`` is retained as a compatibility field in incoming
    briefs, but deliberately has no effect on the decision.
    """
    brief = brief or {}
    evidence = brief.get("evidence") or []
    claims = brief.get("claims") or []
    errors: List[str] = []
    if not isinstance(evidence, Sequence) or isinstance(evidence, (str, bytes)):
        evidence = []
        errors.append("invalid_evidence_collection")
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        claims = []
        errors.append("invalid_claim_collection")
    source_ids = [normalize_text(row.get("source_id")) for row in evidence if isinstance(row, Mapping)]
    if len(source_ids) != len(evidence):
        errors.append("invalid_evidence_record")
    if len(source_ids) != len(set(source_ids)) or any(not source_id for source_id in source_ids):
        errors.append("duplicate_or_missing_source_id")
    records: Dict[str, Mapping[str, Any]] = {
        normalize_text(row.get("source_id")): row for row in evidence
        if isinstance(row, Mapping) and normalize_text(row.get("source_id"))
    }
    if not claims:
        errors.append("no_claim_records")
    claim_ids = [normalize_text(row.get("claim_id")) for row in claims if isinstance(row, Mapping)]
    if len(claim_ids) != len(set(claim_ids)) or any(not claim_id for claim_id in claim_ids):
        errors.append("duplicate_or_missing_claim_id")

    evaluated: List[Dict[str, Any]] = []
    for original in claims:
        claim = dict(original) if isinstance(original, Mapping) else {}
        claim_id = normalize_text(claim.get("claim_id")) or "unknown"
        errors.extend(validate_claim_record(claim))
        # Opinion/creative framing does not require factual source support.
        if claim.get("factual", True) is False:
            claim["status"] = "not_applicable"
            claim["evidence_ids"] = []
            claim["independent_source_count"] = 0
            evaluated.append(claim)
            continue

        supported_sources: List[Mapping[str, Any]] = []
        seen_hashes = set()
        supported: List[str] = []
        claim_reasons: List[str] = []
        candidate_ids = claim.get("evidence_ids") or []
        candidate_ids = candidate_ids if isinstance(candidate_ids, (list, tuple)) else []
        for source_id in dict.fromkeys(str(item) for item in candidate_ids):
            source = records.get(source_id)
            if source is None:
                claim_reasons.append("missing_source:" + source_id)
                continue
            valid, reason = _record_is_publishable(source, claim)
            if not valid:
                claim_reasons.append(reason)
                continue
            publisher = publisher_group(source)
            domain = domain_group(source)
            if not publisher or not domain:
                claim_reasons.append("source_independence_group_missing:" + source_id)
                continue
            digest = text_hash(str(source.get("excerpt") or ""))
            if digest in seen_hashes:
                claim_reasons.append("copied_content:" + source_id)
            seen_hashes.add(digest)
            supported_sources.append(source)
            supported.append(source_id)

        independent_count = _independent_group_count(supported_sources)
        claim["status"] = "verified" if independent_count >= 2 else "unverified"
        claim["evidence_ids"] = supported
        claim["independent_source_count"] = independent_count
        if claim["status"] != "verified":
            errors.append("unsupported_claim:" + claim_id)
            errors.extend(claim_reasons)
        evaluated.append(claim)

    errors = list(dict.fromkeys(errors))
    ready = bool(evaluated) and not errors and all(
        claim.get("status") in {"verified", "not_applicable"} for claim in evaluated
    )
    return {
        "ready": ready,
        "claims": evaluated,
        "errors": errors,
        "action": "ALLOW" if ready else "GATE",
        "reason": "verified_claim_evidence" if ready else (
            "evidence_insufficient_two_independent_publisher_and_domain_groups_required"
        ),
        "trusted_adapter_ignored": bool(brief.get("trusted_adapter")),
    }
