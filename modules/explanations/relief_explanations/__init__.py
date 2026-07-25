from .models import ExplanationV1
from .provider import ExplanationProvider
from .template_provider import TemplateExplanationProvider


def get_default_explanation_provider() -> ExplanationProvider:
    """Today this is always the template provider — swapping in a
    LangChain-backed one (Section 63) once that infrastructure exists is a
    one-line change here, not a caller-side change, since both implement
    ExplanationProvider."""
    return TemplateExplanationProvider()


__all__ = [
    "ExplanationV1",
    "ExplanationProvider",
    "TemplateExplanationProvider",
    "get_default_explanation_provider",
]
