"""
Voice Authentication
--------------------
Verifies that the speaker is the registered owner before executing commands.

Approach
~~~~~~~~
Uses *resemblyzer* (a speaker-embedding library) to convert audio waveforms
into fixed-size "voice prints" (256-d vectors).  Enrolment stores the mean
embedding of several samples.  Verification computes cosine similarity between
the live embedding and the stored profile.

If resemblyzer is not installed the module falls back to a lightweight
comparison using *librosa* MFCCs and cosine distance.

The voice profile is stored as a NumPy ``.npy`` file so it survives restarts.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "settings.json"
)


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh).get("voice_auth", {})
    except Exception as exc:
        logger.warning("VoiceAuth: could not load config – %s", exc)
        return {}


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ---------------------------------------------------------------------------
# Embedding backend selection
# ---------------------------------------------------------------------------

def _get_embedding_backend():
    """Return (embed_fn, sample_rate) for the best available backend."""
    try:
        from resemblyzer import VoiceEncoder, preprocess_wav  # type: ignore
        encoder = VoiceEncoder()

        def embed(wav_path: str) -> np.ndarray:
            wav = preprocess_wav(wav_path)
            return encoder.embed_utterance(wav)

        logger.info("VoiceAuth: using resemblyzer backend.")
        return embed, 16000
    except ImportError:
        pass

    try:
        import librosa  # type: ignore

        def embed(wav_path: str) -> np.ndarray:  # type: ignore[misc]
            y, sr = librosa.load(wav_path, sr=16000, mono=True)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
            return np.mean(mfcc, axis=1)

        logger.info("VoiceAuth: using librosa MFCC backend.")
        return embed, 16000
    except ImportError:
        pass

    logger.warning("VoiceAuth: no embedding backend found. Auth will be disabled.")
    return None, 16000


_embed_fn, _SAMPLE_RATE = _get_embedding_backend()


class VoiceAuthenticator:
    """Enrols the owner's voice and authenticates subsequent speakers.

    Parameters
    ----------
    profile_dir:
        Directory where the voice profile (``.npy`` file) is stored.
    threshold:
        Cosine-similarity threshold (0–1).  A score ≥ threshold is accepted.
    """

    def __init__(
        self,
        profile_dir: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> None:
        cfg = _load_config()
        _dir = profile_dir or cfg.get("profile_path", "authentication/voice_profiles")
        self._profile_dir = Path(_dir)
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._profile_path = self._profile_dir / "owner_profile.npy"
        self._threshold: float = threshold if threshold is not None else cfg.get("threshold", 0.75)
        self._profile: Optional[np.ndarray] = self._load_profile()
        self._enabled: bool = cfg.get("enabled", True) and _embed_fn is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_enrolled(self) -> bool:
        """*True* if an owner voice profile exists."""
        return self._profile is not None

    def enroll(self, wav_paths: list[str]) -> bool:
        """Build an owner profile from a list of WAV file paths.

        Parameters
        ----------
        wav_paths:
            At least one WAV file recorded from the owner.
        Returns
        -------
        *True* on success.
        """
        if not self._enabled:
            logger.warning("VoiceAuth: no backend – enrolment skipped.")
            return False
        if not wav_paths:
            logger.error("VoiceAuth: no wav_paths provided for enrolment.")
            return False

        embeddings = []
        for path in wav_paths:
            try:
                emb = _embed_fn(path)  # type: ignore[misc]
                embeddings.append(emb)
            except Exception as exc:
                logger.warning("VoiceAuth: error embedding %s – %s", path, exc)

        if not embeddings:
            return False

        self._profile = np.mean(embeddings, axis=0)
        np.save(str(self._profile_path), self._profile)
        logger.info(
            "VoiceAuth: owner profile saved to %s (%d samples).",
            self._profile_path,
            len(embeddings),
        )
        return True

    def verify(self, wav_path: str) -> tuple[bool, float]:
        """Verify whether *wav_path* belongs to the enrolled owner.

        Returns
        -------
        (is_owner, similarity_score)
        """
        if not self._enabled:
            # Auth disabled – always allow
            return True, 1.0

        if self._profile is None:
            logger.warning("VoiceAuth: no profile enrolled – access denied.")
            return False, 0.0

        try:
            emb = _embed_fn(wav_path)  # type: ignore[misc]
            score = _cosine_similarity(self._profile, emb)
            accepted = score >= self._threshold
            logger.info(
                "VoiceAuth: similarity=%.3f threshold=%.3f → %s",
                score,
                self._threshold,
                "ACCEPTED" if accepted else "REJECTED",
            )
            return accepted, score
        except Exception as exc:
            logger.error("VoiceAuth: verification error – %s", exc)
            return False, 0.0

    def delete_profile(self) -> None:
        """Remove the stored owner profile."""
        if self._profile_path.exists():
            self._profile_path.unlink()
        self._profile = None
        logger.info("VoiceAuth: profile deleted.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_profile(self) -> Optional[np.ndarray]:
        if self._profile_path.exists():
            try:
                profile = np.load(str(self._profile_path))
                logger.info("VoiceAuth: loaded owner profile from %s.", self._profile_path)
                return profile
            except Exception as exc:
                logger.warning("VoiceAuth: could not load profile – %s", exc)
        return None
