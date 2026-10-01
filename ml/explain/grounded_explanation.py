"""Turn SHAP drivers into a grounded plain-English explanation.

Only feature names and signed SHAP contributions are sent to an optional LLM;
identifiers, names, and raw application payloads never leave this process.
"""

from __future__ import annotations

import json
import os
import urllib.request


def _top_drivers(shap_drivers: list[dict], top_n: int = 5) -> list[dict]:
    return sorted(
        shap_drivers,
        key=lambda item: abs(float(item.get("contribution", 0))),
        reverse=True,
    )[:top_n]


def build_prompt(shap_drivers: list[dict]) -> str:
    """Build an LLM prompt containing only top feature names and signed
    values."""
    drivers = _top_drivers(shap_drivers)
    lines = [
        f"- {item['feature']}: {float(item.get('contribution', 0)):+.4f}"
        for item in drivers
    ]
    return (
        "Explain this model result in two concise sentences using only the "
        "listed feature names and signed SHAP contributions. Do not invent "
        "facts, personal details, causes, or features. Mention that this is "
        "a statistical explanation.\n"
        + "\n".join(lines)
    )


def call_llm(prompt: str) -> str | None:
    """Call an optional OpenAI-compatible endpoint, returning None if
    unset/failing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    endpoint = os.environ.get(
        "LLM_API_URL", "https://api.openai.com/v1/chat/completions"
    )
    payload = json.dumps(
        {
            "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 180,
        }
    ).encode()
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read().decode())
        return body["choices"][0]["message"]["content"].strip()
    except (
        OSError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None


def assert_grounded(
    llm_response: str | None, shap_drivers: list[dict]
) -> bool:
    """Require the response to mention both of the top two real driver
    names."""
    if not llm_response:
        return False
    response = llm_response.casefold()
    top = _top_drivers(shap_drivers, top_n=2)
    return bool(top) and all(
        str(item["feature"]).casefold() in response for item in top
    )


def generate_template_explanation(shap_drivers: list[dict]) -> str:
    """Create a deterministic explanation directly from SHAP values."""
    drivers = _top_drivers(shap_drivers, top_n=3)
    if not drivers:
        return (
            "No SHAP drivers were available for this statistical explanation."
        )
    sentences = []
    for item in drivers:
        direction = (
            "increased"
            if float(item.get("contribution", 0)) >= 0
            else "decreased"
        )
        sentences.append(
            f"{item['feature']} {direction} the model output (SHAP {float(
                    item.get(
                        'contribution',
                        0)):+.4f})."
        )
    return (
        "System-generated explanation based only on the recorded SHAP"
        " drivers: "
        + " ".join(sentences)
    )


def explain(shap_drivers: list[dict]) -> dict:
    """Generate an LLM explanation only when it passes the SHAP grounding
    check."""
    response = call_llm(build_prompt(shap_drivers))
    drivers = _top_drivers(shap_drivers)
    if assert_grounded(response, shap_drivers):
        return {
            "text": response,
            "source": "llm",
            "grounded_in": [item["feature"] for item in drivers],
        }
    return {
        "text": generate_template_explanation(shap_drivers),
        "source": "template",
        "grounded_in": [item["feature"] for item in drivers],
    }
