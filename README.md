# root_access

Terminal-driven RPG engine built with Python + Pygame.

https://elevenlabs.io/app/developers/usage?usage-start-date=2026-01-27T09:08:21.658Z&api-requests-start-date=2026-01-27T09:08:21.666Z&concurrent-requests-start-date=2026-01-27T09:08:21.671Z

**Tone/Theme:** cold procedural sci-fi system UI fused with high-fantasy narrative (“operator controlling a remote vessel”).

---

## What’s Working (Current State)

- ✅ **Terminal UI**: scrolling history, wrapped text, input prompt + blinking cursor  
- ✅ **Scene system (JSON)**: `print`, `typewrite`, `wait`, `voice`, `require_command`, `set_flag`, `branch`, etc.  
- ✅ **Non-blocking Audio Architecture**:
  - Worker thread handles network / file I/O
  - Main thread performs `pygame.mixer` playback safely
- ✅ **TTS Caching**: generated audio is cached so the same line isn’t regenerated every run
- ✅ **SFX by ID** (safe if missing)
- ✅ **Minimal RPG systems**: inventory + quests + combat hooks (data-driven via JSON)
- ✅ **Save/Load**: GameState persistence support (see `content/saves/`)

---

## Quick Start

### 1) Create a virtual environment (recommended)
**Windows (PowerShell):**
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies
```powershell
pip install pygame==2.6.1
```

### 3) Run
```powershell
python main.py
```

---

## ElevenLabs (Optional)

If you’re using the ElevenLabs backend, set your API key as an environment variable:

**PowerShell (temporary for current terminal session):**
```powershell
$env:ELEVENLABS_API_KEY="YOUR_KEY_HERE"
python main.py
```

**Recommended (persistent):** set `ELEVENLABS_API_KEY` in Windows “Environment Variables” (User variables) so it survives new terminals/VS Code sessions.

> ⚠️ Don’t commit secrets to Git. If you use a local `core/secrets.py`, ensure it’s in `.gitignore`.

---

## Project Structure

```
ROOT_ACCESS/
├─ main.py                     # Minimal glue loop (init, tick, input, render, scene update, audio events)
├─ CORE.md                     # Core spec / design constraints
├─ Roadmap.md                  # Phase roadmap
├─ Story.md                    # Narrative reference / early story draft
├─ content/
│  ├─ scenes/                  # JSON scenes (boot/menu/validation/etc.)
│  ├─ audio_cache/             # Cached TTS audio files (hash-named)
│  ├─ saves/                   # Save files (json)
│  └─ sfx/                     # Optional SFX assets
├─ core/
│  ├─ config.py                # GlobalConfig (colors, fonts, fps, backends)
│  ├─ models.py                # GameState + LogEntry + persistence helpers
│  ├─ input_engine.py          # Typing buffer + cursor blink + command history
│  ├─ render_engine.py         # Terminal renderer (wrapping, channels, layout)
│  ├─ audio_engine.py          # Job queue + worker thread + backend abstraction
│  ├─ audio_player.py          # Main-thread-safe mixer playback
│  ├─ audio_cache.py           # Cache lookup/write
│  ├─ elevenlabs_backend.py     # ElevenLabs implementation (network -> cached audio)
│  ├─ local_tts_backend.py      # Optional local TTS backend (if enabled)
│  ├─ sfx_library.py            # SFX id -> file resolution
│  ├─ save_system.py           # Save/load helpers
│  ├─ inventory.py             # Minimal inventory helpers (if split out)
│  ├─ quests.py                # Minimal quest helpers (if split out)
│  └─ theme.py                 # Channel colors / prefixes / UI theme
└─ story/
   ├─ story_loader.py           # Loads scenes from content/scenes
   ├─ scene_validator.py        # Validates schema_version + step types/fields
   ├─ scene_types.py            # Scene/Step dataclasses
   └─ scene_runner.py           # Executes steps deterministically + sets mode/flags
```

---

## How the Engine Runs (High-Level)

### Main loop responsibilities (main thread only)
- Pygame init + event polling
- Collect latest command from `InputEngine`
- Update `SceneRunner` with `dt_ms` + optional `latest_command`
- Render frame via `RenderEngine`
- Poll audio events, and play audio using `AudioPlayer` (**main-thread safe**)

### Worker thread responsibilities
- TTS network calls / file generation / cache writes  
- It **never** calls `pygame.*`

This separation prevents freezes and avoids thread-unsafe mixer usage.

---

## Scene System (JSON)

Scenes live in: `content/scenes/*.json`

Each scene contains:
- `schema_version`
- `scene_id`
- `steps[]` — ordered step list

Example step types you’ll see:
- `print` / `typewrite` / `wait`
- `voice` (TTS)
- `sfx`
- `require_command` (optional `output_flag`)
- `set_flag`
- `branch` (flag/item conditions)
- `give_item`, `quest_update`, `combat_start` (Phase 3 validation steps)

### Recommended workflow

---

## Development Notes

### Fonts
The renderer prefers monospace fonts (e.g., **Consolas**, **Cascadia Mono**, **Courier New**).  
If a font isn’t found, it falls back to the system default.

### Caching & costs
TTS cache is stored under `content/audio_cache/`.  
If the same line is requested again, the engine should reuse cached output (when configured to do so).

---

## Next Phase (Planned)

See `Roadmap.md` for the authoritative phase plan.

Common next upgrades:
- CRT post-processing (scanlines, vignette, bloom-ish glow)
- Richer combat (abilities, status effects)
- Data-driven items/quests definitions (separate JSON registries)
- Packaging/build scripts

---

## License
For class projects / personal learning. Add a license file if you plan to distribute.
