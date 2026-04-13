# Prediction Models

This section provides detailed documentation on the prediction models used in the JamBandNerd project.

## Overview

The project employs a modular, pluggable architecture for its prediction models, allowing for easy comparison and the addition of new models in the future. Each model is designed to be independent and can be run against the standardized data produced by the transformation pipeline.

### Current Models

- **[Notebook Model](./notebook.md)**: A frequency-based statistical model that prioritizes songs that have been played frequently in the last year.

- **[Deal Model](./deal.md)**: An explainable logistic ranking model trained on shared cross-band rotation features. It is promoted on the public website alongside Notebook.

### Historical Models

- **[CK+ Model](./ckplus.md)**: A retired gap-based model kept as historical reference because older prediction and accuracy artifacts still exist in Supabase.

### How to Add a New Model

To add a new prediction model to the project, follow the registry workflow:

1. **Create the Model Package**: Add a subdirectory in `src/jambandnerd/models/` with `model.py` and `serialization.py`.
2. **Register the Model**: Add a `ModelMetadata` entry in `src/jambandnerd/models/metadata.py` and wire it into `registry.py`.
3. **Add Pipeline Scripts**: The unified `scripts/generate_predictions.py` will auto-discover the new model via the registry.
4. **Update Documentation**: Add a new documentation file for the model in this directory and update this index.
