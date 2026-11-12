"""
Simple Coqui TTS helper.

Usage:
    # Built-in single-speaker voice (no sample needed)
    python speak.py --text "Hello world"

    # Clone a voice from a sample clip
    python speak.py --text "Hello world" --speaker my_sample.wav --language en

    # Pick a specific model
    python speak.py --text "Hello" --model tts_models/en/vctk/vits --speaker p225
"""
import argparse
import os
import sys

import torch
from TTS.api import TTS


def main() -> int:
    parser = argparse.ArgumentParser(description="Coqui TTS quick synth")
    parser.add_argument("--text", required=True, help="Text to speak")
    parser.add_argument("--out", default="output.wav", help="Output wav path")
    parser.add_argument(
        "--model",
        default="tts_models/en/ljspeech/tacotron2-DDC",
        help="TTS model name (see `tts --list_models`)",
    )
    parser.add_argument("--speaker", default=None, help="Speaker sample wav (for cloning)")
    parser.add_argument("--speaker-idx", default=None, help="Speaker id for multi-speaker models")
    parser.add_argument("--language", default="en", help="Language code (XTTS/YourTTS)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU")
    args = parser.parse_args()

    device = "cpu" if args.cpu else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    tts = TTS(args.model).to(device)

    kwargs = {"text": args.text, "file_path": args.out}
    if args.speaker:
        kwargs["speaker_wav"] = args.speaker
        kwargs["language"] = args.language
    if args.speaker_idx:
        kwargs["speaker"] = args.speaker_idx

    tts.tts_to_file(**kwargs)
    print(f"Wrote {os.path.abspath(args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
