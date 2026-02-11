import json
import tempfile
import unittest
from pathlib import Path

from pydantic import ValidationError

from app.refactor_helpers import (
    ProductBase,
    build_listing_prompt,
    build_result_record,
    format_validation_error,
    load_json_file,
    normalize_string_list,
    parse_listing_response,
    safe_json_loads,
    strip_non_empty,
    validate_year_range,
)


def sample_product() -> ProductBase:
    return ProductBase(
        id=101,
        gender="Men",
        masterCategory="Apparel",
        subCategory="Topwear",
        articleType="Shirts",
        baseColour="Navy Blue",
        season="Summer",
        year=2012.0,
        usage="Casual",
        productDisplayName="Turtle Check Men Navy Blue Shirt",
    )


class TestRefactorHelpers(unittest.TestCase):
    def test_strip_non_empty(self) -> None:
        self.assertEqual(strip_non_empty("  hi  "), "hi")
        with self.assertRaises(ValueError):
            strip_non_empty("   ")

    def test_validate_year_range(self) -> None:
        self.assertEqual(validate_year_range(None), None)
        self.assertEqual(validate_year_range(2000), 2000)
        with self.assertRaises(ValueError):
            validate_year_range(3025)

    def test_load_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "test.json"
            p.write_text(json.dumps({"a": 1}), encoding="utf-8")
            self.assertEqual(load_json_file(p), {"a": 1})

    def test_safe_json_loads(self) -> None:
        self.assertEqual(safe_json_loads('{"ok": true}'), {"ok": True})
        self.assertEqual(safe_json_loads('prefix {"ok": true} suffix'), {"ok": True})
        with self.assertRaises(json.JSONDecodeError):
            safe_json_loads("not json")

    def test_build_listing_prompt(self) -> None:
        prompt = build_listing_prompt(sample_product())
        self.assertIn("Turtle Check Men Navy Blue Shirt", prompt)
        self.assertIn("Output JSON schema", prompt)

    def test_parse_listing_response(self) -> None:
        text = json.dumps(
            {
                "title": "Navy Casual Shirt",
                "description": "A lightweight shirt for daily wear in warm weather. It is comfortable and versatile.",
                "features": ["Breathable fabric", "Classic fit", "Button closure"],
                "keywords": ["shirt", "navy", "casual"],
            }
        )
        parsed = parse_listing_response(text)
        self.assertEqual(parsed["title"], "Navy Casual Shirt")
        self.assertEqual(len(parsed["features"]), 3)

    def test_parse_listing_response_invalid(self) -> None:
        bad_text = json.dumps(
            {
                "title": "Bad",
                "description": "too short",
                "features": ["only one"],
                "keywords": [],
            }
        )
        with self.assertRaises(ValidationError):
            parse_listing_response(bad_text)

    def test_format_validation_error(self) -> None:
        try:
            parse_listing_response(
                json.dumps(
                    {
                        "title": "Bad",
                        "description": "too short",
                        "features": ["one"],
                        "keywords": [],
                    }
                )
            )
            self.fail("Expected ValidationError")
        except ValidationError as error:
            formatted = format_validation_error(error)
            self.assertEqual(formatted["error"], "validation_error")
            self.assertTrue(len(formatted["details"]) >= 1)

    def test_normalize_string_list(self) -> None:
        self.assertEqual(normalize_string_list([" a ", "", "b"]), ["a", "b"])
        with self.assertRaises(ValueError):
            normalize_string_list("not-a-list")  # type: ignore[arg-type]

    def test_build_result_record(self) -> None:
        product = sample_product()
        listing = {
            "title": "Navy Casual Shirt",
            "description": "A lightweight shirt for daily wear in warm weather. It is comfortable and versatile.",
            "features": ["Breathable fabric", "Classic fit", "Button closure"],
            "keywords": ["shirt", "navy", "casual"],
        }
        record = build_result_record(0, product, listing)
        self.assertEqual(record["id"], 101)
        self.assertEqual(record["title"], "Navy Casual Shirt")


if __name__ == "__main__":
    unittest.main()
