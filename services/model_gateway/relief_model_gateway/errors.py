from __future__ import annotations


class ModelServiceUnavailableError(Exception):
    """Raised whenever ReliefFM can't be reached — not configured
    (RELIEFFM_INFERENCE_URL unset, the normal state until Plan One ships
    services/model_inference), a connection failure, a timeout, or a non-2xx
    response. Callers decide what to do next (Section 39's permanent
    fallback rule: the platform must work before ReliefFM is connected) —
    this module never silently substitutes another provider itself."""
