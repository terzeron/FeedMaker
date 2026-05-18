#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `pydantic`.

Purpose
-------
Pin the pydantic surface used by `backend/main.py`'s LoginRequest model.
A pydantic upgrade (e.g. 2.x → 3.x) that drops EmailStr, renames the
@field_validator decorator, or changes ValidationError semantics will
break the auth endpoint -- this test catches it at CI time.

Reference call sites (production code):
    backend/main.py:19      from pydantic import BaseModel, EmailStr, field_validator
    backend/main.py:117-131 class LoginRequest(BaseModel):
                                email: EmailStr
                                profile_picture_url: Optional[str] = None
                                @field_validator("profile_picture_url")
                                @classmethod
                                def validate_picture_url_scheme(cls, v):
                                    ...
                                    raise ValueError("...")
"""

import unittest
from typing import Optional

from pydantic import BaseModel, EmailStr, ValidationError, field_validator


# Mirror of backend/main.py's LoginRequest, kept local so the learning test
# doesn't depend on the production module importing successfully.
class _LoginLike(BaseModel):
    email: EmailStr
    name: str
    access_token: str
    profile_picture_url: Optional[str] = None

    @field_validator("profile_picture_url")
    @classmethod
    def validate_picture_url_scheme(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        lower = v.lower().lstrip()
        if lower.startswith("javascript:") or lower.startswith("data:"):
            raise ValueError("profile_picture_url scheme not allowed")
        return v


# -----------------------------------------------------------------------------
# 1. Import surface
# -----------------------------------------------------------------------------


class PydanticImportSurfaceTest(unittest.TestCase):
    """Pin imports backend/main.py:19 relies on."""

    def test_base_model_is_a_class(self) -> None:
        self.assertTrue(isinstance(BaseModel, type))

    def test_email_str_is_a_type_constructor(self) -> None:
        # EmailStr is a typing alias / annotated str -- callable as a class for
        # validation purposes.
        self.assertTrue(EmailStr is not None)

    def test_field_validator_is_a_callable_decorator_factory(self) -> None:
        self.assertTrue(callable(field_validator))

    def test_validation_error_is_an_exception(self) -> None:
        self.assertTrue(issubclass(ValidationError, Exception))


# -----------------------------------------------------------------------------
# 2. BaseModel construction with valid data
# -----------------------------------------------------------------------------


class BaseModelConstructionTest(unittest.TestCase):
    """Pin BaseModel(...) keyword construction and field access."""

    def test_valid_payload_constructs_and_exposes_fields(self) -> None:
        m = _LoginLike(email="user@example.com", name="Alice", access_token="t-123", profile_picture_url=None)
        self.assertEqual(m.email, "user@example.com")
        self.assertEqual(m.name, "Alice")
        self.assertEqual(m.access_token, "t-123")
        self.assertIsNone(m.profile_picture_url)

    def test_optional_field_with_default_can_be_omitted(self) -> None:
        # profile_picture_url has default None in production.
        m = _LoginLike(email="user@example.com", name="A", access_token="t")
        self.assertIsNone(m.profile_picture_url)


# -----------------------------------------------------------------------------
# 3. EmailStr validation rejects malformed addresses
# -----------------------------------------------------------------------------


class EmailStrValidationTest(unittest.TestCase):
    """Pin: EmailStr rejects strings that aren't RFC-style emails."""

    def test_invalid_email_raises_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            _LoginLike(email="not-an-email", name="A", access_token="t")

    def test_valid_email_with_dots_and_subdomain(self) -> None:
        m = _LoginLike(email="first.last@mail.example.com", name="A", access_token="t")
        self.assertEqual(m.email, "first.last@mail.example.com")


# -----------------------------------------------------------------------------
# 4. field_validator decorator semantics
# -----------------------------------------------------------------------------


class FieldValidatorTest(unittest.TestCase):
    """Pin @field_validator decorator behavior used in production."""

    def test_validator_passes_value_through_for_safe_input(self) -> None:
        m = _LoginLike(email="u@example.com", name="A", access_token="t", profile_picture_url="https://cdn.example.com/me.jpg")
        self.assertEqual(m.profile_picture_url, "https://cdn.example.com/me.jpg")

    def test_validator_rejects_javascript_scheme(self) -> None:
        # The exact contract from main.py:128-130
        with self.assertRaises(ValidationError) as ctx:
            _LoginLike(email="u@example.com", name="A", access_token="t", profile_picture_url="javascript:alert(1)")
        # Validation error wraps the ValueError message.
        self.assertIn("scheme not allowed", str(ctx.exception))

    def test_validator_rejects_data_uri(self) -> None:
        with self.assertRaises(ValidationError):
            _LoginLike(email="u@example.com", name="A", access_token="t", profile_picture_url="data:image/png;base64,XXX")

    def test_validator_accepts_none_when_field_is_optional(self) -> None:
        # main.py:126-127 -- if v is None: return v
        m = _LoginLike(email="u@example.com", name="A", access_token="t", profile_picture_url=None)
        self.assertIsNone(m.profile_picture_url)


# -----------------------------------------------------------------------------
# 5. ValidationError exposes structured error info (fastapi relies on this)
# -----------------------------------------------------------------------------


class ValidationErrorShapeTest(unittest.TestCase):
    """Pin ValidationError.errors() shape that fastapi serializes to 422s."""

    def test_validation_error_has_errors_method_returning_list_of_dicts(self) -> None:
        try:
            _LoginLike(email="bad-email", name="A", access_token="t")
        except ValidationError as exc:
            errors = exc.errors()
            self.assertIsInstance(errors, list)
            self.assertGreater(len(errors), 0)
            self.assertIn("loc", errors[0])
            self.assertIn("msg", errors[0])
            self.assertIn("type", errors[0])
        else:
            self.fail("expected ValidationError")


if __name__ == "__main__":
    unittest.main()
