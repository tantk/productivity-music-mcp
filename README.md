# Productivity Music MCP Server

AI-powered focus music plugin for coding CLIs (Claude Code, Cursor, Windsurf, Cline, etc.).

Uses a **GLM 5.1 AI DJ** to pick the best music source based on your mood, time of day, and context. Generates and plays focus music using neuroscience-backed principles (neural entrainment, beta-wave targeting).

Built for the GMI Cloud x GLM Hackathon.

## Features

- **AI DJ** — GLM 5.1 picks the optimal source and generates music prompts
- **Lyria 3** — Google AI music generation (30s clips)
- **MiniMax Music 2.5** — Full song generation via GMI Cloud
- **Procedural audio** — Instant binaural beats, pink noise, rain, drones (no API needed)
- **YouTube** — Search and play any music (requires yt-dlp)
- **Freesound** — Ambient nature sounds
- **Pomodoro timer** — Auto-switches between focus and break music
- **Local playback** — Plays audio directly on your machine

## Project Structure

```
├── src/                    # Main package
│   ├── __init__.py         # Package entry point
│   ├── server.py           # MCP server (12 tools)
│   ├── player.py           # Cross-platform audio playback
│   ├── dj_agent.py         # GLM 5.1 AI DJ agent
│   └── sources/            # Music source modules
│       ├── procedural.py   # Binaural beats, pink noise, rain, drone
│       ├── lyria.py        # Google Lyria 3
│       ├── minimax_music.py # MiniMax Music 2.5 via GMI Cloud
│       ├── freesound.py    # Freesound.org ambient sounds
│       ├── youtube.py      # YouTube audio via yt-dlp
│       └── local_cache.py  # Local audio file scanner
├── scripts/                # Utility scripts
│   ├── generate_music.py   # Standalone Lyria 3 generator
│   └── test-keys.sh        # GMI Cloud API key validator
├── docs/                   # Documentation & reference
├── output/                 # Generated music (gitignored)
├── cache/                  # Cached audio (gitignored)
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Install

```bash
pip install -e .
```

## API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Required (at least one):
- `GMI_INFER` — GMI Cloud inference key (for DJ agent + MiniMax)
- `GOOGLE_API` — Google AI key (for Lyria 3)

Optional:
- `FREESOUND_API_KEY` — [Get one free](https://freesound.org/apiv2/apply/)
- `GMI_INFRA` — GMI Cloud infra key (for test-keys.sh only)

## Setup in your coding CLI

### Claude Code

```bash
claude mcp add productivity-music -- productivity-music-mcp
```

Or in `~/.claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "productivity-music": {
      "command": "productivity-music-mcp",
      "env": {
        "GMI_INFER": "your-key",
        "GOOGLE_API": "your-key"
      }
    }
  }
}
```

### Cursor / Windsurf / Cline

Add to MCP settings:
```json
{
  "mcpServers": {
    "productivity-music": {
      "command": "productivity-music-mcp",
      "env": {
        "GMI_INFER": "your-key",
        "GOOGLE_API": "your-key"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|---|---|
| `music(request)` | Ask the AI DJ to pick and play music |
| `generate_lyria(mood)` | Generate with Google Lyria 3 |
| `generate_minimax(mood)` | Generate with MiniMax Music 2.5 |
| `generate_procedural(type, duration)` | Instant ambient sounds |
| `play_youtube(query)` | Search and play from YouTube |
| `play_freesound(query)` | Search ambient sounds |
| `play_audio(path, loop)` | Play a local file |
| `stop()` | Stop playback |
| `now_playing()` | Check playback status |
| `pomodoro(focus, break, cycles)` | Start Pomodoro timer |
| `list_tracks()` | List cached audio |
| `list_sources()` | Show available sources |

## Examples

```
"Play some focus music"           → DJ picks best source
"I need calm rain sounds"         → Procedural rain or Freesound
"Generate lo-fi with Lyria"       → Lyria 3 generates custom track
"Start a pomodoro session"        → 25/5 timer with auto music
"Stop the music"                  → Stops playback
```

## Requirements

- Python 3.10+
- `ffplay` (from ffmpeg) for audio playback
- At least one API key (GMI_INFER or GOOGLE_API)
