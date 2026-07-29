import re
import logging
from datetime import datetime, timezone

from Rag_backend.graph.state import State
from Rag_backend.guardrails.Pii import redact_pii_layered

logger = logging.getLogger(__name__)

CITATION_RE = re.compile(r"\[(\d+)\]")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def sentence_needs_redaction(sentence: str, citations: dict) -> bool:
    """Redact if the sentence cites any 'shared' chunk, or cites nothing
    at all (unattributed content defaults to redact — safer)."""
    cited_nums = [int(n) for n in CITATION_RE.findall(sentence)]
    if not cited_nums:
        return True
    return any(citations.get(n, {}).get("source_collection") == "shared" for n in cited_nums)


def PII(state: State):
    """
    Reads draft_answer, citations
    writes final_answer
    """
    node_name = "pii_node"
    started_at = datetime.now(timezone.utc)
    logger.info(f"[{node_name}] started")

    try:
        answer = state['draft_answer']
        citations = state.get('citations') or {}

        sentences = SENTENCE_RE.split(answer)
        processed = []
        withheld_count = 0

        for s in sentences:
            if not sentence_needs_redaction(s, citations):
                processed.append(s)
                continue

            redacted, method = redact_pii_layered(s)
            if redacted is None:
                processed.append("[content withheld — could not verify this excerpt was safe to show]")
                withheld_count += 1
            else:
                processed.append(redacted)
                if method != "presidio":
                    logger.warning(f"[{node_name}] used {method} for one sentence — Presidio failed")

        final_answer = " ".join(processed)

        trace_entry = build_trace_entry(
            node=node_name, event="success", started_at=started_at,
            details={"sentence_count": len(sentences), "withheld_count": withheld_count},
        )

        return {
            **state,
            "final_answer": final_answer,
            "trace_log": state['trace_log'] + [trace_entry],
        }

    except Exception as e:
      
        logger.error(f"[{node_name}] error has occurred | {e}")

        trace_entry = build_trace_entry(
            node=node_name, event="failed", started_at=started_at,
            details={"error": str(e)},
        )

        return {
            **state,
            "final_answer": None,
            "trace_log": state['trace_log'] + [trace_entry],
            "exit_stage": "pii_node_error",
            "exit_message": "we ran into an issue processing your request. Please try again.",
        }


def build_trace_entry(node, event, started_at, details=None):
    completed_at = datetime.now(timezone.utc)
    return {
        "node": node, "event": event,
        "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(),
        "elapsed_ms": int((completed_at - started_at).total_seconds() * 1000),
        "detail": details or {},
    }