# Contributing

Thanks for your interest! This is a small project, so contributions are welcome and simple.

## Ways to help

- 🐛 Report bugs or request features via GitHub Issues.
- 🔊 Suggest or add more demo samples.
- 🧩 Improve the UI (accessibility, layout, extra controls such as pitch/volume).
- 🐳 Improve the Docker setup or add a Hugging Face Space.

## Development

```bash
git clone https://github.com/vvsnmurthy3758/akasavani.git
cd akasavani
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install ruff
```

Run the linter before opening a pull request:

```bash
ruff check .
python -m compileall -q start_webui.py speak.py
```

## Notes

- `patches/` contains modified files from Coqui TTS (MPL-2.0). Keep those changes minimal and license-compatible.
- Don't commit model weights or generated audio; they're covered by `.gitignore` (the demo clips in `docs/assets/` are the exception).

By contributing, you agree that your contributions are licensed under the project's [MPL-2.0](LICENSE) license.
