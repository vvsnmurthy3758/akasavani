"""Telugu (తెలుగు) text-to-speech backends for Akasavani.

Akasavani's main engine (Coqui TTS) ships no Telugu model, so Telugu is served
by this small, self-contained backend.

Three engines are available:

``piper``
    `Piper <https://github.com/OHF-Voice/piper1-gpl>`_ voices from
    ``rhasspy/piper-voices``. Three native Telugu voices are available
    (**Padmavathi**, **Venkatesh**, **Maya**) at 22,050 Hz. No login required,
    only ~63 MB per voice, and it runs fast on the CPU. This is the default.

``mms``
    ``facebook/mms-tts-tel`` — a single-voice VITS model (~145 MB). No login
    required and it supports the speed slider natively. License: CC-BY-NC-4.0
    (non-commercial).

``indicf5``
    ``ai4bharat/IndicF5`` — a high-quality voice-cloning model. It is *gated*
    on the Hugging Face Hub (you must accept its terms while logged in) and it
    needs a short Telugu reference clip plus its transcript. License: MIT.

Pick the engine with ``AKASAVANI_TELUGU_ENGINE`` (``auto`` | ``piper`` |
``mms`` | ``indicf5``). ``auto`` (the default) uses IndicF5 when a reference
clip, its transcript and a Hugging Face token are all present, otherwise Piper
when it is installed, and finally falls back to the always-available MMS voice.

Pick the Piper voice with ``AKASAVANI_TELUGU_VOICE`` (``padmavathi`` |
``venkatesh`` | ``maya``); the web UI also lets you switch voices per request.
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

# Piper voices (https://huggingface.co/rhasspy/piper-voices/tree/main/te/te_IN).
PIPER_VOICES: dict[str, str] = {
    "padmavathi": "te_IN-padmavathi-medium",
    "venkatesh": "te_IN-venkatesh-medium",
    "maya": "te_IN-maya-medium",
}
PIPER_VOICE_LABELS: dict[str, str] = {
    "padmavathi": "Padmavathi (female)",
    "venkatesh": "Venkatesh (male)",
    "maya": "Maya (female)",
}
PIPER_DEFAULT_VOICE = os.environ.get("AKASAVANI_TELUGU_VOICE", "padmavathi").strip().lower()
if PIPER_DEFAULT_VOICE not in PIPER_VOICES:
    PIPER_DEFAULT_VOICE = "padmavathi"
PIPER_CACHE_DIR = Path(
    os.environ.get("AKASAVANI_PIPER_DIR", str(Path.home() / ".cache" / "akasavani" / "piper"))
)


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


def _piper_available() -> bool:
    try:
        import piper  # noqa: F401
        from piper import PiperVoice  # noqa: F401
    except Exception:  # noqa: BLE001 - any failure simply means "piper is missing"
        return False
    return True


def resolve_engine() -> str:
    """Return the Telugu engine to use: ``piper``, ``mms`` or ``indicf5``."""
    engine = os.environ.get("AKASAVANI_TELUGU_ENGINE", "auto").strip().lower()
    if engine == "auto":
        if _indicf5_ready():
            return "indicf5"
        if _piper_available():
            return "piper"
        return "mms"
    return engine


def piper_voice_options() -> list[tuple[str, str]]:
    """``(voice_id, label)`` pairs for the web UI when Piper is the engine."""
    if resolve_engine() != "piper":
        return []
    return [(name, PIPER_VOICE_LABELS.get(name, name)) for name in PIPER_VOICES]


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

    def __init__(self, engine: str | None = None, voice: str | None = None):
        self.engine = (engine or resolve_engine()).lower()
        self.voice = self._resolve_voice(voice)
        self.sample_rate = 16000
        self._model = None
        self._tokenizer = None
        self._piper: dict[str, object] = {}
        self._ready = False
        logger.info("Telugu TTS engine selected: %s", self.engine)

    # -- helpers -------------------------------------------------------
    @staticmethod
    def _resolve_voice(voice: str | None) -> str:
        name = (voice or PIPER_DEFAULT_VOICE).strip().lower()
        return name if name in PIPER_VOICES else PIPER_DEFAULT_VOICE

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

    def _load_piper(self, voice: str) -> None:
        from piper import PiperVoice
        from piper.download_voices import download_voice

        name = self._resolve_voice(voice)
        if name in self._piper:
            self._model = self._piper[name]
            self.sample_rate = int(self._model.config.sample_rate)  # type: ignore[attr-defined]
            return
        voice_id = PIPER_VOICES[name]
        PIPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        model_path = PIPER_CACHE_DIR / f"{voice_id}.onnx"
        if not model_path.is_file():
            logger.info("Downloading Telugu voice '%s' (first run, ~63 MB)...", voice_id)
            download_voice(voice_id, PIPER_CACHE_DIR)
        self._model = PiperVoice.load(str(model_path))
        self._piper[name] = self._model
        self.sample_rate = int(self._model.config.sample_rate)  # type: ignore[attr-defined]
        logger.info("Loaded Telugu voice '%s' (%s Hz)", voice_id, self.sample_rate)

    def load(self) -> None:
        if self._ready:
            return
        if self.engine == "indicf5":
            self._load_indicf5()
        elif self.engine == "piper" and _piper_available():
            self._load_piper(self.voice)
        else:
            if self.engine == "piper":
                logger.warning("piper-tts is not installed; using the MMS voice instead")
            self.engine = "mms"
            self._load_mms()
        self._ready = True

    # -- synthesis -----------------------------------------------------
    def synthesize(self, text: str, speed: float = 1.0, voice: str | None = None) -> tuple[np.ndarray, int]:
        """Return ``(float32_waveform, sample_rate)`` for ``text``.

        ``voice`` selects a Piper voice for this request (ignored by the other
        engines, which have a single voice each).
        """
        if not text or not text.strip():
            raise ValueError("text is required")
        self.load()
        speed = float(speed) if speed else 1.0
        if self.engine == "indicf5":
            return self._synth_indicf5(text, speed)
        if self.engine == "piper":
            return self._synth_piper(text, speed, voice)
        return self._synth_mms(text, speed)

    def _synth_piper(self, text: str, speed: float, voice: str | None) -> tuple[np.ndarray, int]:
        from piper.config import SynthesisConfig

        name = self._resolve_voice(voice)
        if name not in self._piper:
            self._load_piper(name)
        model = self._piper[name]
        # VITS controls tempo through `length_scale` (bigger = slower).
        syn_config = SynthesisConfig(length_scale=1.0 / max(0.1, min(3.0, speed)))
        chunks = [chunk.audio_int16_array for chunk in model.synthesize(text, syn_config=syn_config)]  # type: ignore[attr-defined]
        if not chunks:
            raise ValueError(
                "The Telugu voice could not read that text. Type Telugu text "
                "(తెలుగు), or switch the language back to English."
            )
        wav = np.concatenate(chunks).astype(np.float32) / 32768.0
        return wav, int(model.config.sample_rate)  # type: ignore[attr-defined]

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
