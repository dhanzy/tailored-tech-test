import hashlib
import json
import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from cache_service.models import Payload, TransformedString
from cache_service.schemas import PayloadRequest
from cache_service.transformer import Transformer

logger = logging.getLogger(__name__)

SEPARATOR = ", "


def payload_id(request: PayloadRequest) -> str:
    """Deterministic id, so identical requests resolve to the same payload.

    JSON encoding keeps the two lists distinguishable (["a"], ["b"] vs
    ["a", "b"], []) which naive concatenation would not.
    """
    canonical = json.dumps([request.list_1, request.list_2], ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def create_payload(session: Session, request: PayloadRequest, transform: Transformer) -> str:
    """Generate (or reuse) the payload for ``request`` and return its id."""
    pid = payload_id(request)
    if session.get(Payload, pid) is not None:
        logger.info("payload cache hit id=%s", pid[:12])
        return pid
    logger.info("payload cache miss id=%s", pid[:12])

    transformed = _transform_all(session, {*request.list_1, *request.list_2}, transform)
    # zip pairs the lists element-wise; the inner loop flattens each pair in order.
    output = SEPARATOR.join(
        transformed[s] for pair in zip(request.list_1, request.list_2, strict=True) for s in pair
    )
    _insert_ignoring_duplicates(session, [Payload(id=pid, output=output)])
    return pid


def read_payload(session: Session, pid: str) -> str | None:
    payload = session.get(Payload, pid)
    return payload.output if payload else None


def _transform_all(session: Session, strings: set[str], transform: Transformer) -> dict[str, str]:
    """Map every string to its transformed value, calling ``transform`` only on cache misses."""
    if not strings:
        return {}

    cached = session.exec(
        select(TransformedString).where(col(TransformedString.source).in_(strings))
    ).all()

    results = {row.source: row.result for row in cached}
    fresh = {s: transform(s) for s in strings - results.keys()}
    # Counts only: the strings are caller data and may be sensitive.
    logger.info(
        "string cache: %d hits, %d misses (transformer called %d times)",
        len(results),
        len(fresh),
        len(fresh),
    )
    _insert_ignoring_duplicates(
        session, [TransformedString(source=s, result=r) for s, r in fresh.items()]
    )
    return results | fresh


def _insert_ignoring_duplicates(
    session: Session, rows: list[Payload] | list[TransformedString]
) -> None:
    """Persist rows, tolerating a concurrent request having stored the same ones.

    Rows are deterministic functions of their key, so losing the race to an
    identical row is harmless and must not fail the request.
    """
    if not rows:
        return
    session.add_all(rows)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        for row in rows:
            session.merge(row)
        session.commit()
