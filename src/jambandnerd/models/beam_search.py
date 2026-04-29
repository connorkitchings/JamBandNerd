"""Beam search optimizer for Stage 3 of the 3-stage forecasting pipeline.

Reconciles calibrated availability probabilities (Stage 1) with directional
transition weights (Stage 2) to produce a sequence-aware ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from jambandnerd.transformations.transitions import TransitionMatrix


@dataclass
class BeamPath:
    songs: List[str]
    log_prob: float
    used: set[str]

    def copy(self) -> BeamPath:
        return BeamPath(
            songs=list(self.songs),
            log_prob=self.log_prob,
            used=set(self.used),
        )


@dataclass
class BeamSearchResult:
    ranked_songs: List[str]
    song_scores: Dict[str, float]
    paths: List[BeamPath]


def beam_search(
    stage1_probs: Dict[str, float],
    transition_matrix: TransitionMatrix,
    sequence_length: int,
    beam_width: int = 5,
    candidate_songs: Sequence[str] | None = None,
) -> BeamSearchResult:
    if not stage1_probs:
        return BeamSearchResult(ranked_songs=[], song_scores={}, paths=[])

    if candidate_songs is not None:
        all_songs = [s for s in candidate_songs if s in stage1_probs]
    else:
        all_songs = list(stage1_probs.keys())

    if not all_songs:
        return BeamSearchResult(ranked_songs=[], song_scores={}, paths=[])

    import math

    openers = sorted(all_songs, key=lambda s: -stage1_probs[s])[:beam_width]
    beam: List[BeamPath] = []
    for song in openers:
        log_p = math.log(max(stage1_probs[song], 1e-12))
        beam.append(BeamPath(songs=[song], log_prob=log_p, used={song}))

    for _step in range(1, sequence_length):
        candidates_for_step: List[tuple[float, BeamPath]] = []

        for path in beam:
            last_song = path.songs[-1]

            for song in all_songs:
                if song in path.used:
                    continue

                s1_prob = stage1_probs.get(song, 0.0)
                if s1_prob <= 0.0:
                    continue

                trans_prob = transition_matrix.get_probability(last_song, song)
                joint_prob = s1_prob * trans_prob if trans_prob is not None else s1_prob

                log_joint = path.log_prob + math.log(max(joint_prob, 1e-12))
                new_path = path.copy()
                new_path.songs.append(song)
                new_path.log_prob = log_joint
                new_path.used.add(song)

                candidates_for_step.append((log_joint, new_path))

        if not candidates_for_step:
            break

        candidates_for_step.sort(key=lambda x: -x[0])
        beam = [path for _, path in candidates_for_step[:beam_width]]

    song_max_scores: Dict[str, float] = {}
    for path in beam:
        for i, song in enumerate(path.songs):
            path_prob = math.exp(path.log_prob)
            if song not in song_max_scores or path_prob > song_max_scores[song]:
                song_max_scores[song] = path_prob

    ranked = sorted(all_songs, key=lambda s: -song_max_scores.get(s, 0.0))

    return BeamSearchResult(
        ranked_songs=ranked,
        song_scores=song_max_scores,
        paths=beam,
    )
