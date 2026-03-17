"""Data transformations package for feature engineering.

Provides band-agnostic transformations for show indices, gaps, and other
model features required by prediction algorithms.

Core components:
- gaps: Feature generation pipeline with gap analysis and model data containers
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gaps import ModelData, generate_model_data

__all__ = [
    "ModelData",
    "generate_model_data",
    "gaps",
]
