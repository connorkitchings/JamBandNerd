# Prediction Models

This section provides detailed documentation on the prediction models used in the JamBandNerd project.

## Overview

The project employs a modular, pluggable architecture for its prediction models, allowing for easy comparison and the addition of new models in the future. Each model is designed to be independent and can be run against the standardized data produced by the transformation pipeline.

### Current Models

- **[Notebook Model](./notebook.md)**: A frequency-based statistical model that prioritizes songs that have been played frequently in the last year.

- **[CK+ Model](./ckplus.md)**: A gap-based statistical model that ranks songs by how "overdue" they are for an appearance.

- **[Deal Model](./xgboost.md)**: An ML-based model using gradient boosted trees to learn patterns in song rotation and provide probability rankings. Hidden from public website until approved.

### How to Add a New Model

To add a new prediction model to the project, follow these steps:

1. **Create the Model Logic**: Implement the new model in its own subdirectory within `src/jambandnerd/models/`.
2. **Create Prediction Scripts**: Add new scripts to the `scripts/` directory to run the model and save its predictions and accuracy.
3. **Update Documentation**: Add a new documentation file for the model in this directory and update this index to include a link to it.
