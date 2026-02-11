from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


YEAR_MIN = 1900
YEAR_MAX = 2100


# Shared validation helpers

def strip_non_empty(value: str) -> str:
    """Trim string and enforce non-empty content."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


def validate_year_range(value: Optional[float]) -> Optional[float]:
    """Validate optional year range used across product schemas."""
    if value is None:
        return None
    if value < YEAR_MIN or value > YEAR_MAX:
        raise ValueError(f"year must be between {YEAR_MIN} and {YEAR_MAX}")
    return value


# Models
class ProductBase(BaseModel):
    """Shared product schema used for input row and JSON-file validation."""

    model_config = ConfigDict(extra="forbid")

    id: int
    gender: str = Field(..., min_length=1)
    masterCategory: str = Field(..., min_length=1)
    subCategory: str = Field(..., min_length=1)
    articleType: str = Field(..., min_length=1)
    baseColour: str = Field(..., min_length=1)
    season: str = Field(..., min_length=1)
    year: Optional[float] = None
    usage: str = Field(..., min_length=1)
    productDisplayName: str = Field(..., min_length=1)

    @field_validator(
        "gender",
        "masterCategory",
        "subCategory",
        "articleType",
        "baseColour",
        "season",
        "usage",
        "productDisplayName",
    )
    @classmethod
    def _strip_required_strings(cls, value: str) -> str:
        return strip_non_empty(value)

    @field_validator("year")
    @classmethod
    def _validate_year(cls, value: Optional[float]) -> Optional[float]:
        return validate_year_range(value)


class ListingOutput(BaseModel):
    """Validated shape of generated listing response."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=20)
    features: List[str] = Field(..., min_length=3, max_length=10)
    keywords: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("title", "description")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return strip_non_empty(value)

    @field_validator("features", "keywords")
    @classmethod
    def _normalize_lists(cls, value: List[Any]) -> List[str]:
        return normalize_string_list(value)


# JSON helpers

def load_json_file(path: Path) -> Dict[str, Any]:
    """Read JSON from disk with UTF-8 decoding."""
    return json.loads(path.read_text(encoding="utf-8"))


def safe_json_loads(text: str) -> Dict[str, Any]:
    """Strict JSON parse with fallback extraction of first JSON object block."""
    cleaned = text.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(cleaned[start : end + 1])

    raise json.JSONDecodeError("No JSON object found", cleaned, 0)


def format_validation_error(error: ValidationError) -> Dict[str, Any]:
    """Convert Pydantic ValidationError into client-friendly error payload."""
    return {
        "error": "validation_error",
        "details": [
            {
                "field": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ],
    }


# Prompt/response helpers

def build_listing_prompt(product: ProductBase) -> str:
    """Build listing prompt from product metadata."""
    year_text = str(int(product.year)) if product.year is not None else "N/A"

    return f"""
You are an expert ecommerce copywriter for fashion products.
Return valid JSON only. No markdown, no extra text.

Product data:
- id: {product.id}
- name: {product.productDisplayName}
- gender: {product.gender}
- masterCategory: {product.masterCategory}
- subCategory: {product.subCategory}
- articleType: {product.articleType}
- baseColour: {product.baseColour}
- season: {product.season}
- year: {year_text}
- usage: {product.usage}

Output JSON schema:
{{
  "title": "string",
  "description": "string",
  "features": ["string", "string", "string"],
  "keywords": ["string"]
}}

Rules:
- Output must be valid JSON
- Title should include key product attributes (type, color, usage)
- Description should be 2 to 4 sentences
- Features must be 3 to 10 bullet-style strings
- Keywords should include search-friendly terms (type, color, season, gender, usage)
""".strip()


def parse_listing_response(raw_text: str) -> Dict[str, Any]:
    """Parse and validate model response text against ListingOutput schema."""
    parsed = safe_json_loads(raw_text)
    listing = ListingOutput.model_validate(parsed)
    return listing.model_dump()


# Output formatting helpers

def normalize_string_list(value: Iterable[Any]) -> List[str]:
    """Normalize list-like strings by stripping and dropping empty entries."""
    if not isinstance(value, list):
        raise ValueError("must be a list")

    output: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("all items must be strings")
        cleaned = item.strip()
        if cleaned:
            output.append(cleaned)
    return output


def build_result_record(index: Any, product: ProductBase, listing: Mapping[str, Any]) -> Dict[str, Any]:
    """Create output row in one place to avoid repeated dict-building logic."""
    return {
        "index": index,
        "id": product.id,
        "productDisplayName": product.productDisplayName,
        "gender": product.gender,
        "masterCategory": product.masterCategory,
        "subCategory": product.subCategory,
        "articleType": product.articleType,
        "baseColour": product.baseColour,
        "season": product.season,
        "year": product.year,
        "usage": product.usage,
        "title": listing["title"],
        "description": listing["description"],
        "features": listing["features"],
        "keywords": listing["keywords"],
    }
