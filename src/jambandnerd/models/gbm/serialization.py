"""GBM predictor serialization — delegates to Deal serializer (same output shape)."""

from jambandnerd.models.deal.serialization import (
    serialize_predictions as serialize_gbm_predictions,
)

__all__ = ["serialize_gbm_predictions"]
