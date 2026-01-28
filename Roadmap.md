# ROOT ACCESS — Dev Lead Roadmap (Big Picture + Step-by-Step)

This roadmap is designed to avoid dead ends and keep the engine future-proof (ElevenLabs swap, JSON scenes, more UI polish) while staying beginner-friendly.
QUICK KNOWLEDGE:
Red error text
White voice text
white info text 
---

## Big Picture (Phases)

### Phase 1 — Foundation / Proof of Architecture (Non-Blocking Core)
**Goal:** A working Pygame terminal window with:
- typed input + blinking cursor
- terminal history rendering (wrapping)
- scene pacing (typewriter + waits) using `dt_ms` (no main-thread sleeps)
- mock threaded AudioEngine (queue + worker thread) proving the loop never freezes
- StoryLoader + SceneRunner controlling progression (BOOT → JUMPSTART → ENGAGE)

**Definition of Done (Phase 1):**
- No `time.sleep()` in the main thread (only allowed in audio worker for mock latency)
- Worker thread never calls `pygame.*`
- `main()` is glue only (no story logic)
- Engine runs with no external assets required

---

### Phase 2 — Content Pipeline + UX Polish
**Goal:** Move content out of code and improve terminal experience:
- JSON scenes + schema validation
- branching, flags/tier-based decisions
- channel colors (terminal/voice/narration/system/error)
- scrolling, command history (↑/↓), better wrapping + log trimming
- optional skip/fast-forward cutscene

---

### Phase 3 — Real Audio + Expansion Systems
**Goal:** Swap mock audio with real backends:
- ElevenLabs backend integration + caching (text hash → audio file)
- optional local TTS backend
- real SFX playback (still main-thread safe)
- combat / tactical prompts, inventory, save/load

---

## Multi-File Structure (Phase 1 Target Layout)

```text
root_access/
  main.py
  core/
    __init__.py
    config.py
    models.py
    input_engine.py
    render_engine.py
    audio_engine.py
  story/
    __init__.py
    scene_types.py
    story_loader.py
    scene_runner.py
  content/
    scenes/              # Phase 2 (JSON later)
```

**Rule:** For Phase 1, scenes can be hardcoded in `StoryLoader`, but use a data structure shaped like your future JSON.

---

## Phase 1 — Step-by-Step (Multi-File)

### Step 0 — Project Setup + Sanity Boot
**Create folders/files:**
- `main.py`
- `core/` and `story/` packages with `__init__.py`

**Success criteria:**
- `python main.py` runs and opens a blank Pygame window (no systems yet)
- clean quit works

**Deliverable:** Minimal Pygame bootstrap loop (temporary)

---

### Step 1 — Core Data + Config (No Rendering Yet)
**Files:**
- `core/config.py`
- `core/models.py`

**Implement:**
- `GlobalConfig`:
  - WIDTH=1024, HEIGHT=768, FPS=60
  - CRT colors: green (0,255,0), near-black (10,10,10)
  - USE_MOCK_AUDIO=True
- `LogEntry` (structured):
  - `text`, `channel` (+ optional style/meta later)
- `GameState`:
  - `tier`, `flags`, `mode`, `history`, `current_scene_id`, `scene_cursor`
  - `append_history(text, channel="terminal")` trims to last N entries
- `UIState`:
  - `input_buffer`, `cursor_visible`, `cursor_timer_ms`
  - typewriter fields (placeholders): `typing_text`, `typing_index`, etc.

**Success criteria:**
- `main.py` can instantiate config/state/ui without errors
- history truncation works via `append_history`

---

### Step 2 — InputEngine (Text Buffer + Cursor Blink)
**File:**
- `core/input_engine.py`

**Implement:**
- Holds: `buffer`, `cursor_visible`, `cursor_timer_ms`
- `process_event(event, dt_ms, game_state) -> command|None`
  - if `game_state.mode` disallows input, ignore typing
  - handle BACKSPACE
  - handle ENTER (return command + clear buffer)
- `update(dt_ms)` for cursor blink toggle every 500ms

**Success criteria:**
- Typing works
- cursor blink toggles (even before rendering, you can debug via prints)

---

### Step 3 — RenderEngine (Terminal UI Rendering)
**File:**
- `core/render_engine.py`

**Implement:**
- Initializes font with fallback (Consolas → Courier New → default)
- `render(screen, game_state, ui_state)`
  - clear to black
  - draw `game_state.history` top-down
  - draw prompt + `ui_state.input_buffer` at bottom with cursor
  - simple wrapping (monospace; basic implementation is OK)
- **Phase 1 rule:** no CRT scanlines/vignette/post-processing

**Success criteria:**
- Window shows history lines
- input line appears at bottom
- cursor visible/hidden based on UIState

---

### Step 4 — Glue main loop (Input + Render + History)
**File:**
- `main.py`

**Implement:**
- init pygame, screen, clock
- instantiate: config, state, ui, input_engine, render_engine
- loop:
  - dt_ms = clock.tick(config.FPS)
  - gather events; pass to input_engine
  - on Enter command:
    - `state.append_history(f"> {cmd}", channel="terminal")`
  - render + flip
- clean quit on pygame.QUIT

**Success criteria:**
- You can type commands and see them appear in terminal history

---

### Step 5 — AudioEngine (Mock Async Thread + Queues + Shutdown)
**File:**
- `core/audio_engine.py`

**Implement:**
- `AudioJob` (`kind`: "tts"/"pause"/"sfx"; `text`; `seconds`; optional `voice_id`)
- `AudioEvent` (`type`: "STARTED"/"FINISHED"/"ERROR"; job info)
- Backend abstraction:
  - `AudioBackendBase`
  - `MockAudioBackend` (simulates latency; prints `[AUDIO] ...`)
- `AudioEngine`:
  - job queue + event queue
  - worker thread (daemon ok in Phase 1, but **still include sentinel shutdown**)
  - `enqueue(job)`
  - `poll_events()`
  - `shutdown()` posts sentinel and joins safely

**Hard rules:**
- Worker thread must never call `pygame.*`
- `time.sleep()` allowed only inside worker (mock latency)

**Success criteria:**
- On Enter, enqueue an audio job (“Processing…”)
- While audio “runs,” UI stays responsive and keeps updating

---

### Step 6 — Scene System (StoryLoader + SceneRunner)
**Files:**
- `story/scene_types.py`
- `story/story_loader.py`
- `story/scene_runner.py`

**Implement:**
- Scene structure:
  - `Scene(id, steps)`
- Step types (Phase 1 minimum):
  - `print` (instant)
  - `typewrite` (dt-based characters)
  - `wait` (dt-based timers)
  - `require_command` (blocks until player input matches)
  - `voice` (enqueues AudioJob)
- `StoryLoader.load_scene(scene_id)` returns hardcoded demo scene
- `SceneRunner`:
  - owns current scene + cursor
  - `update(dt_ms, latest_command=None)`
  - advances steps deterministically
  - writes `LogEntry`s via `GameState.append_history()`
  - queues audio via `AudioEngine.enqueue()`
  - controls `game_state.mode` when input should be locked/unlocked

**Demo scene (required):**
- Typewriter boot lines
- 2 second wait
- require_command: BOOT
- require_command: JUMPSTART
- require_command: ENGAGE
- enqueue a mock audio job on command accept (non-blocking proof)

**Success criteria:**
- Scene auto-prints boot text
- Engine pauses and waits for BOOT
- BOOT advances to the next part, etc.
- main loop remains glue-only (no story if/else in main)

---

## Phase 1 Final Checklist (Must Pass)
- [ ] 1024×768 window, 60 FPS target
- [ ] No `time.sleep()` in main thread
- [ ] Worker thread never calls `pygame.*`
- [ ] SceneRunner controls pacing via `dt_ms`
- [ ] AudioEngine uses jobs/events queues + shutdown sentinel
- [ ] main() contains only glue code
- [ ] No CRT post-processing yet (scanlines/vignette deferred)

---

## Phase 2 (Preview: Next Up)
- JSON scene files in `content/scenes/`
- schema validation + versioning
- channel coloring & formatting
- scrollback + command history
- branching by flags/tier
- save/load GameState

---
## Phase 2 — Content Pipeline + UX Polish (Step-by-step)

---

### Step 1 — JSON Scene Files (Move content out of code)
**Files/Folders:**
- `content/scenes/` (new)
- `story/story_loader.py` (update)
- `story/scene_types.py` (update, if needed)

**Implement:**
- Store scenes as JSON files (e.g., `content/scenes/boot.json`)
- Update `StoryLoader.load_scene(scene_id)` to:
  - read `content/scenes/{scene_id}.json`
  - parse JSON into your existing `Scene` + `Step` structures
- Define a minimum JSON shape:
  - `schema_version` (int)
  - `scene_id` (str)
  - `steps` (list of dicts with `"type"` plus fields)

**Success criteria:**
- You can edit story text in JSON without changing Python code
- `SceneRunner` executes a JSON scene exactly like the Phase 1 hardcoded scene

---

### Step 2 — Schema Validation + Versioning (Stop bad content early)
**Files:**
- `story/scene_validator.py` (new) *(or `story/schema.py`)*
- `story/story_loader.py` (update)

**Implement:**
- Require `"schema_version": 1` in every scene file
- Validate on load:
  - Required top-level keys exist: `schema_version`, `scene_id`, `steps`
  - Each step dict has `"type"`
  - Step `"type"` is known
  - Required fields exist per type (e.g., `typewrite` requires `text`)
  - (Optional) reject unknown keys to catch typos early
- On validation failure:
  - Raise a clear exception OR log an `error` LogEntry and fall back to a safe scene

**Success criteria:**
- Broken JSON produces readable errors (no silent weird behavior)
- You can evolve schema later (v2, v3) without breaking old scenes

---

### Step 3 — Channel Coloring + Formatting (Terminal feels “alive”)
**Files:**
- `core/render_engine.py` (update)
- `core/config.py` (update) *(or add `core/theme.py` new)*

**Implement:**
- Add per-channel styling in the renderer:
  - `terminal` = green
  - `system` = brighter tint
  - `narration` = dim tint
  - `voice` = different tint or prefix
  - `error` = red
- Add consistent prefixes (optional but clean):
  - `> ` for player input
  - `[SYS]`, `[ERR]`, `[NAR]`, `[VOICE]` etc.
- Keep strict separation: RenderEngine only renders, it does not decide story.

**Success criteria:**
- History log shows visible differences by channel
- SceneRunner only sets `channel` (no render-specific logic leaks in)

---

### Step 4 — Scrollback + Command History (Quality of life)
**Files:**
- `core/models.py` (update UIState)
- `core/input_engine.py` (update)
- `core/render_engine.py` (update)

**Implement:**

**Scrollback**
- Add to `UIState`:
  - `scroll_offset: int`
- Input controls:
  - PageUp/PageDown or mouse wheel adjusts `scroll_offset`
- RenderEngine:
  - Renders history based on `scroll_offset`
  - Clamps scrolling to valid range

**Command history**
- Add to `InputEngine` or `UIState`:
  - `command_history: list[str]`
  - `history_index: int`
- On Enter:
  - append command to history
- On Up/Down arrows:
  - cycle through command history into the input buffer

**Success criteria:**
- You can scroll back to see old output
- Up/Down recalls prior commands like a real terminal

---

### Step 5 — Branching by Flags / Tier (Real RPG logic begins)
**Files:**
- `story/scene_types.py` (update)
- `story/scene_runner.py` (update)
- `core/models.py` (GameState flags/tier already exist; extend if needed)

**Implement:**
Add step types (Phase 2 minimum):
- `set_flag`
  - `{ "type": "set_flag", "key": "tutorial_complete", "value": true }`
- `branch`
  - supports conditions like:
    - `flag_equals`
    - `tier_at_least`
  - supports actions like:
    - `goto_scene`
    - `goto_step`

Example:
- `{ "type": "branch", "if": {"flag_equals": ["tutorial_complete", true]}, "then": {"goto_scene": "after_tutorial"}, "else": {"goto_scene": "tutorial"} }`

**Success criteria:**
- Scene behavior changes based on flags and tier
- Branching is driven by JSON data, not hardcoded if/else chains in code

---

### Step 6 — Main Menu & Input Branching (Capture choice from require_command)
**Why this exists:**
To build a proper main menu (ex: “Type START or QUIT”), the engine must know **which** command was typed.  
Upgrade `require_command` so it can optionally store the accepted command into a flag, letting a later `branch` react to it.

**Files:**
- `story/scene_validator.py` (update if you reject unknown fields)
- `story/scene_runner.py` (update)
- `content/scenes/main_menu.json` (new)
- `main.py` (update initial scene)

**Implement:**
1. **Validator:** allow optional `output_flag` field on `require_command` (only required if your validator blocks unknown keys).
2. **Runner:** when `require_command` succeeds:
   - if `output_flag` exists, store the accepted user command into `GameState.flags[output_flag]`
3. **Content:** create a looping/branching main menu scene that:
   - prints title
   - waits for input
   - stores `menu_choice` via `output_flag`
(Recommended) Add a quit path that sets a flag like `EXIT_GAME = true`.

**Example runner change (concept):**
- On `require_command` success:
  - `flags[output_flag] = normalized_command`

**Example content (main idea):**
- `require_command` with `"commands": ["start", "quit"]` + `"output_flag": "menu_choice"`
- `branch` based on `menu_choice`:
  - start → `goto_scene: "boot_sequence"`
  - quit → set `EXIT_GAME` flag (or route to a shutdown scene)

**Success criteria:**
- Typing `start` goes to your boot sequence scene
- Typing `quit` triggers a clean shutdown path (at minimum sets `EXIT_GAME` flag)

---

### Step 7 — Save/Load GameState (Persist progress)
**Files:**
- `core/save_system.py` (new)
- `core/models.py` (add serialize/deserialize helpers)
- `main.py` or `SceneRunner` command handling (wire commands)

**Implement:**
- Serialize `GameState` to a JSON-safe dict:
  - `tier`, `flags`, `current_scene_id`, `scene_cursor`
  - (Optional) minimal history snapshot
- Save file location:
  - `content/saves/save1.json` (create `content/saves/`)
- Add commands:
  - `save`
  - `load`
  - (Optional) `reset`
- On load:
  - restore GameState
  - reload current scene via StoryLoader
  - resume from `scene_cursor`

**Success criteria:**
- You can quit/restart and load progress successfully
- Save/load doesn’t break SceneRunner pacing or input state

---

## Phase 2 Final Checklist (Must Pass)
- [ ] Scenes load from `content/scenes/*.json`
- [ ] Loader validates schema + version with clear errors
- [ ] RenderEngine supports channel colors/prefixes
- [ ] Scrollback works (PageUp/PageDown or wheel)
- [ ] Command history works (Up/Down)
- [ ] Branching works (flags + tier) and is data-driven
- [ ] Main menu works (START/QUIT) using `require_command.output_flag`
- [ ] Save/load restores progress reliably

---

## Phase 3 (Preview: Next Up)
- ElevenLabs backend + caching
- optional local TTS
- SFX playback (main-thread safe)
- combat / inventory / quests

---
