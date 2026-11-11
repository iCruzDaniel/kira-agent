"""Errores de negocio con códigos estables para las tools."""

from __future__ import annotations


class KiraError(Exception):
    code = "error"


class ValidationError(KiraError):
    code = "validation_error"


class NotFoundError(KiraError):
    code = "not_found"


class ConflictError(KiraError):
    code = "conflict"


class PolicyError(KiraError):
    code = "policy_error"
