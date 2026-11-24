"""Plain-language service cards built from the live catalogue.

A card is everything a model (large or small) needs to choose and connect a
service: what it is for, when to use it, what it consumes and produces, and
which settings can be adjusted. Providers can write their own description in
``interface_contract["design"] = {"purpose": ..., "use_when": ..., "keywords": [...]}``;
otherwise a curated description for known operations, then the catalogue
description, is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.service import Service
from app.services.service_settings import get_definition

START_TYPE = "Workflow Start"
END_TYPE = "Workflow Output"

# Curated plain-language descriptions for operations already in the catalogue.
CURATED: dict[str, dict[str, str]] = {
    "BuildRunConfig": {
        "purpose": "Turns a plain-language district-heating request into a structured run configuration (Danish node, uses a local language model).",
        "use_when": "Start of a district-heating network design workflow; before topology generation.",
    },
    "GenerateTopology": {
        "purpose": "Generates candidate district-heating network topologies from a run configuration.",
        "use_when": "After the run configuration; before rendering the topologies.",
    },
    "RenderTopologies": {
        "purpose": "Draws generated network topologies as SVG images for review.",
        "use_when": "End of a district-heating workflow, to visualise candidate networks.",
    },
    "ConfigureAndSynthesize": {
        "purpose": "Creates a reproducible synthetic electricity grid scenario (Dutch node) for benchmarking.",
        "use_when": "Start of a grid benchmarking workflow when real grid data is not available.",
    },
    "RunBenchmark": {
        "purpose": "Runs a reproducible benchmark of AI/control approaches on a prepared grid scenario and reports KPIs.",
        "use_when": "After a synthetic grid scenario has been prepared.",
    },
    "ProvideData": {
        "purpose": "Prepares German grid and time-series data for generating load and generation profiles.",
        "use_when": "Start of a German time-series (chronics) workflow.",
    },
    "GenerateChronics": {
        "purpose": "Generates electricity load and production time series (chronics) with the VILLASnode simulator.",
        "use_when": "After grid data has been provided; produces CSV time series.",
    },
    "FormatOutput": {
        "purpose": "Checks generated time-series CSV files and produces a validation summary.",
        "use_when": "End of the German time-series workflow.",
    },
    "ExecuteQuery": {
        "purpose": "Loads energy data from a CSV file or a database query (Portuguese node) as the starting dataset.",
        "use_when": "Start of the Portuguese synthetic-data workflow.",
    },
    "ApplyFunction": {
        "purpose": "Applies feature-engineering functions from a knowledge store to prepare data for model training.",
        "use_when": "After loading data and before training a model.",
    },
    "TrainModel": {
        "purpose": "Trains a DoppelGANger (DGAN) generative model on prepared time-series data.",
        "use_when": "After feature engineering; before generating synthetic data.",
    },
    "GenerateData": {
        "purpose": "Generates data records for a downstream analysis step (synthetic data from a trained model, or simulated energy readings).",
        "use_when": "After model training or configuration; before analysis or reporting.",
    },
    "GetConfiguration": {
        "purpose": "Provides the run configuration (for example how many records to generate) for an energy-data pipeline.",
        "use_when": "First step of the energy analysis pipeline.",
    },
    "AnalyzeData": {
        "purpose": "Analyses household energy readings: flags unusual consumption (anomalies) and scores efficiency.",
        "use_when": "After data generation; before writing a report.",
    },
    "GenerateReport": {
        "purpose": "Writes a readable report (summary, per-household analysis, recommendations) from analysis results.",
        "use_when": "End of the energy analysis pipeline.",
    },
}

EXCLUDED_DESCRIPTION_PREFIXES = ("test only", "compatibility alias")


@dataclass
class ServiceCard:
    id: str
    name: str
    provider: str
    node: str | None
    category: str
    operation: str
    purpose: str
    use_when: str
    input_type: str
    output_type: str
    keywords: list[str] = field(default_factory=list)
    settings: dict[str, Any] | None = None  # normalised settings declaration
    container_name: str = ""

    @property
    def is_start(self) -> bool:
        return self.input_type == START_TYPE

    @property
    def is_end(self) -> bool:
        return self.output_type == END_TYPE

    def prompt_line(self) -> dict[str, Any]:
        """Compact representation sent to the model."""
        line: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "purpose": self.purpose,
            "use_when": self.use_when,
            "input_type": self.input_type,
            "output_type": self.output_type,
        }
        if self.settings:
            line["settings"] = {
                name: {k: v for k, v in prop.items() if k in ("type", "title", "description", "default", "minimum", "maximum", "enum", "unit")}
                for name, prop in self.settings["schema"]["properties"].items()
            }
            line["settings_channel"] = self.settings["channel"]
        else:
            line["settings"] = "fixed"
        return line


def _eligible(service: Service) -> bool:
    if (service.status or "").lower() != "approved":
        return False
    if (service.lifecycle_status or "active").lower() in ("archived", "deprecated"):
        return False
    description = (service.description or "").strip().lower()
    return not description.startswith(EXCLUDED_DESCRIPTION_PREFIXES)


def card_for(service: Service) -> ServiceCard:
    contract = service.interface_contract if isinstance(service.interface_contract, dict) else {}
    design = contract.get("design") if isinstance(contract.get("design"), dict) else {}
    curated = CURATED.get(service.operation_name or "", {})
    return ServiceCard(
        id=service.id,
        name=service.name,
        provider=service.provider,
        node=service.owner_node,
        category=service.category,
        operation=service.operation_name or "",
        purpose=design.get("purpose") or curated.get("purpose") or (service.description or service.name),
        use_when=design.get("use_when") or curated.get("use_when") or "",
        input_type=service.input_type,
        output_type=service.output_type,
        keywords=[str(k) for k in design.get("keywords", []) if isinstance(k, (str, int))],
        settings=get_definition(service),
        container_name=service.container_name or "",
    )


def build_catalogue(db: Session) -> list[ServiceCard]:
    services = db.query(Service).all()
    return [card_for(s) for s in services if _eligible(s)]


_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if len(w) > 2}


def relevance(card: ServiceCard, query: str) -> float:
    """Keyword overlap score; the hook where embeddings can replace keywords."""
    q = _words(query)
    if not q:
        return 0.0
    text = " ".join([card.name, card.purpose, card.use_when, card.provider, card.category, *card.keywords])
    return len(q & _words(text)) / len(q)


def select_cards(cards: list[ServiceCard], query: str, limit: int = 60) -> list[ServiceCard]:
    """Return the cards to show the model; all of them while the catalogue is small."""
    if len(cards) <= limit:
        return cards
    return sorted(cards, key=lambda c: relevance(c, query), reverse=True)[:limit]
