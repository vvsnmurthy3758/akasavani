"""Telugu (తెలుగు) text-to-speech backends for Akasavani.

Akasavani's main engine (Coqui TTS) ships no Telugu model, so Telugu is served
by this small, self-contained backend that speaks through Hugging Face
``transformers``.

Two engines are available:

``mms``
    ``facebook/mms-tts-tel`` — a single-voice VITS model (~145 MB). No login
    required, works fully offline once downloaded, and supports the speed
    slider natively. License: CC-BY-NC-4.0 (non-commercial).

``indicf5``
    ``ai4bharat/IndicF5`` — a high-quality voice-cloning model. It is *gated*
    on the Hugging Face Hub (you must accept its terms while logged in) and it
    needs a short Telugu reference clip plus its transcript. License: MIT.

Pick the engine with ``AKASAVANI_TELUGU_ENGINE`` (``auto`` | ``mms`` |
``indicf5``). ``auto`` (the default) uses IndicF5 when a reference clip, its
transcript and a Hugging Face token are all present, and otherwise falls back
to the always-available MMS voice.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

MMS_MODEL = os.environ.get("MMS_TELUGU_MODEL", "facebook/mms-tts-tel")
INDICF5_MODEL = os.environ.get("INDICF5_MODEL", "ai4bharat/IndicF5")
INDICF5_REF_AUDIO = os.environ.get("INDICF5_REF_AUDIO", "").strip()
INDICF5_REF_TEXT = os.environ.get("INDICF5_REF_TEXT", "").strip()


def _hf_token_available() -> bool:
    for var in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACEHUB_API_TOKEN"):
        if os.environ.get(var):
            return True
    try:
        from huggingface_hub import HfFolder

        return bool(HfFolder.get_token())
    except Exception:  # noqa: BLE001 - any failure simply means "no token"
        return False


def _indicf5_ready() -> bool:
    return bool(
        INDICF5_REF_AUDIO
        and INDICF5_REF_TEXT
        and Path(INDICF5_REF_AUDIO).is_file()
        and _hf_token_available()
    )


def resolve_engine() -> str:
    """Return the Telugu engine to use: ``mms`` or ``indicf5``."""
    engine = os.environ.get("AKASAVANI_TELUGU_ENGINE", "auto").strip().lower()
    if engine == "auto":
        return "indicf5" if _indicf5_ready() else "mms"
    return engine


def apply_speed(wav: np.ndarray, sample_rate: int, speed: float) -> np.ndarray:
    """Change the duration of ``wav`` without changing its pitch.

    Uses ``librosa`` when available and falls back to plain resampling (which
    shifts pitch slightly) if it is not.
    """
    if not speed or abs(speed - 1.0) < 1e-3:
        return wav
    try:
        import librosa

        return librosa.effects.time_stretch(wav, rate=float(speed)).astype(np.float32)
    except Exception:  # noqa: BLE001 - librosa is optional
        logger.warning("librosa unavailable; falling back to pitch-shifting resample")
        length = max(1, int(round(len(wav) / speed)))
        old = np.arange(len(wav))
        new = np.linspace(0, len(wav) - 1, length)
        return np.interp(new, old, wav).astype(np.float32)


class TeluguTTS:
    """Lazily-loaded Telugu speech synthesizer.

    The underlying model is only downloaded/loaded on the first synthesis
    request, so the server still starts instantly for English-only use.
    """

    def __init__(self, engine: str | None = None):
        self.engine = (engine or resolve_engine()).lower()
        self.sample_rate = 16000
        self._model = None
        self._tokenizer = None
        self._ready = False
        logger.info("Telugu TTS engine selected: %s", self.engine)

    # -- loading -------------------------------------------------------
    def _load_mms(self) -> None:
        from transformers import AutoTokenizer, VitsModel

        logger.info("Loading Telugu voice '%s' (first run downloads ~145 MB)...", MMS_MODEL)
        self._tokenizer = AutoTokenizer.from_pretrained(MMS_MODEL)
        self._model = VitsModel.from_pretrained(MMS_MODEL)
        self._model.eval()
        self.sample_rate = int(self._model.config.sampling_rate)

    def _load_indicf5(self) -> None:
        from transformers import AutoModel

        if not _indicf5_ready():
            raise RuntimeError(
                "IndicF5 needs INDICF5_REF_AUDIO, INDICF5_REF_TEXT and a Hugging Face "
                "token. Accept the model terms at https://huggingface.co/ai4bharat/IndicF5 "
                "then run `huggingface-cli login`."
            )
        logger.info("Loading Telugu voice '%s' ...", INDICF5_MODEL)
        self._model = AutoModel.from_pretrained(INDICF5_MODEL, trust_remote_code=True)
        self.sample_rate = 24000

    def load(self) -> None:
        if self._ready:
            return
        if self.engine == "indicf5":
            self._load_indicf5()
        else:
            self.engine = "mms"
            self._load_mms()
        self._ready = True

    # -- synthesis -----------------------------------------------------
    def synthesize(self, text: str, speed: float = 1.0) -> tuple[np.ndarray, int]:
        """Return ``(float32_waveform, sample_rate)`` for ``text``."""
        if not text or not text.strip():
            raise ValueError("text is required")
        self.load()
        speed = float(speed) if speed else 1.0
        if self.engine == "indicf5":
            return self._synth_indicf5(text, speed)
        return self._synth_mms(text, speed)

    def _synth_mms(self, text: str, speed: float) -> tuple[np.ndarray, int]:
        import torch

        inputs = self._tokenizer(text, return_tensors="pt")
        if inputs["input_ids"].shape[1] == 0:
            raise ValueError(
                "The Telugu voice only understands Telugu script. Type Telugu text "
                "(తెలుగు), or switch the language back to English."
            )
        # VITS controls tempo through `speaking_rate` (length_scale = 1 / rate).
        self._model.speaking_rate = max(0.1, min(3.0, speed))
        with torch.no_grad():
            waveform = self._model(**inputs).waveform
        wav = waveform.squeeze().cpu().numpy().astype(np.float32)
        return wav, self.sample_rate

    def _synth_indicf5(self, text: str, speed: float) -> tuple[np.ndarray, int]:
        audio = self._model(text, ref_audio_path=INDICF5_REF_AUDIO, ref_text=INDICF5_REF_TEXT)
        wav = np.asarray(audio, dtype=np.float32).squeeze()
        return apply_speed(wav, self.sample_rate, speed), self.sample_rate
