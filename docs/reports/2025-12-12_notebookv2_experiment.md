# Experiment: Notebook V2 (100-show vs 1-year window)

**Date:** 2025-12-12

## Hypothesis

A `notebook` model variant using a "last 100 shows" window (`notebookv2`) might outperform the existing `notebook` model (which uses a "last 1 year" window) for some or all bands. The theory is that a shorter, more recent window of shows could be a stronger predictor of immediate future setlists.

## Methodology

1.  A new model, `notebookv2`, was created as a copy of the `notebook` model.
2.  The data window for `notebookv2` was changed from "last 1 year" to "last 100 shows".
3.  A backtest was performed for both models across all supported bands, analyzing the last 100 completed shows for each band.
4.  The primary metric for comparison was the F1-score at K=25, with other metrics also considered.

## Results

The following table summarizes the F1-scores at K=25 for both models across all bands. The winner for each band is highlighted in **bold**.

| Band              | Notebook v1 (1-year) F1@25 | Notebook v2 (100-show) F1@25 | Winner |
| ----------------- | -------------------------- | ---------------------------- | ------ |
| Goose             | **0.292**                  | 0.285                        | **V1** |
| Eggy              | **0.167**                  | 0.166                        | **V1** |
| Phish             | **0.271**                  | 0.271                        | **Tie (V1)** |
| Widespread Panic  | 0.289                      | **0.311**                    | **V2** |
| Billy Strings     | **0.234**                  | 0.233                        | **V1** |
| Umphrey's McGee   | **0.212**                  | 0.210                        | **V1** |

## Conclusion

The original Notebook V1 model, with its 1-year data window, demonstrated superior or equal performance for 5 out of the 6 bands tested. The 100-show window of Notebook V2 only provided a significant advantage for Widespread Panic.

Given these results, the hypothesis that a shorter window is a better predictor was not validated across the majority of bands. The experiment was concluded, and the decision was made not to promote Notebook V2 to production. All code related to the experimental model was removed from the codebase.
