# YouTube Translator

A Python-based interactive tool that enables on-the-fly translation of YouTube video subtitles while playing them in `mpv`. It automatically downloads subtitles, tracks your mouse movements over the video, and pauses playback to translate the specific word you hover over.

## Features
* **Automated Subtitle Download:** Seamlessly fetches auto-generated or manual subtitles from YouTube using `yt-dlp`.
* **Interactive Playback:** Integrates deeply with the `mpv` media player via IPC sockets to read properties and control playback state.
* **Hover-to-Translate:** Simply hover your mouse over a specific word in the subtitle; the script calculates the text bounding box, pauses the video, and displays the translation on-screen.
* **Quick Copy:** Easily copy the current subtitle sentence to your clipboard by pressing `Ctrl+C`.
* **NixOS Support:** Includes a ready-to-use `shell.nix` environment configuration out of the box.

## Prerequisites
* Python >= 3.12
* [uv](https://github.com/astral-sh/uv) (Fast Python package installer and resolver)
* [mpv](https://mpv.io/) media player

## Installation

1. Clone this repository and navigate into the project directory.
2. We use `uv` for blazing-fast dependency management. Run the following commands to install the required packages:

```bash
uv sync
uv pip install ./quickmt/
uv pip install --no-cache-dir --force-reinstall spacy thinc

```

*Note for NixOS users: You can drop into the development shell directly which provides `uv`, `python312`, and the required library paths (`gcc`, `zlib`) by simply running `nix-shell`.*

## Usage

1. **Start `mpv` with the IPC Server:**
You must start `mpv` and expose an IPC socket so the Python controller can communicate with it.
```bash
mpv --input-ipc-server=/tmp/mpvsocket <your-video-file-or-url>

```


2. **Run the Controller:**
Start the main script to begin tracking subtitles and mouse movements.
```bash
python mpv_controller.py

```
