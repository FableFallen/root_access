# ROOT ACCESS — Core Project Spec (Authoritative Reference)

## 0) Project Identity
- **Title:** ROOT ACCESS  
- **Format:** Text-first RPG / Terminal-driven narrative engine (Pygame UI)  
- **Tone:** Cold, procedural, high-tech meets high-fantasy  
- **Primary UX:** CRT terminal feed + typed commands + optional voice/SFX layer  
- **Core Promise:** Non-blocking architecture (no freezing during “audio/network/typing delays”)

---

## 1) Hard Constraints
- **Python:** 3.13  
- **Pygame:** 2.6.1  
- **Architecture:** Strictly class-based. **No global script variables** (constants live in config classes).  
- **Threading rule:** **Only main thread may call Pygame APIs** (display, fonts, mixer, events).  
- **Non-blocking rule:** **No `time.sleep()` in main loop**. All timing via `dt_ms` accumulation.

---

## 2) Design Principles (Guardrails)
1) **Main loop stays dumb:** input → update → async events → render. No story logic in `main()`.  
2) **Data-driven story:** scenes are scripts (steps), not hardcoded if/else chains.  
3) **Separation of concerns:** rendering doesn’t mutate story; input doesn’t decide story.  
4) **Composition over inheritance** for effects (text, audio jobs, UI states).  
5) **Every slow thing is async** (TTS download, file I/O, future API calls).

---

## 3) Core Loop Contract
Each frame (60 FPS target):
1. `dt_ms = clock.tick(FPS)`  
2. `input_engine.process_events(pygame_events, dt_ms)`  
3. `scene_runner.update(dt_ms)` (timed output, waits, scene progression)  
4. `audio_engine.poll_events()` → forward to `scene_runner` / `game_state`  
5. `render_engine.render(screen, game_state, ui_state)`  
6. `pygame.display.flip()`

---

## 4) Core Data Models (Stable Shapes)

### 4.1 GlobalConfig
- `WIDTH=1024`, `HEIGHT=768`, `FPS=60`  
- `COLORS`: CRT green `(0,255,0)`, near-black `(10,10,10)`  
- `USE_MOCK_AUDIO=True`  
- Future: font preferences, volume, text speed defaults, debug flags

### 4.2 GameState (World + Narrative State)
- `tier: int` (0 Guest, 1 Debug, 2 Admin)
- `flags: dict[str, bool|int|str]` (world state)
- `mode: str` (`"cutscene"|"terminal"|"combat"|"locked"`)
- `history: list[LogEntry]` (chronological terminal/voice events)
- `current_scene_id: str`
- `scene_cursor: int` (current step index)
- Future: player/vessel stats, inventory, quests, save slots

**Rule:** History truncation handled centrally (e.g., keep last N lines).

### 4.3 UIState (Pure UI/Presentation)
- `input_buffer: str`
- `cursor_visible: bool`
- `cursor_timer_ms: int`
- `typed_line_partial: str` (if typewriter in-progress)
- `scroll_offset: int` (future)
- `notifications: list[str]` (future)

### 4.4 LogEntry (Structured output line)
Minimum:
- `text: str`
- `channel: str` (`"terminal"|"voice"|"narration"|"system"|"error"`)
Optional future:
- `style: str` (`"info"|"warn"|"danger"|"dim"`)
- `timestamp_ms: int`
- `meta: dict` (speaker, tags, etc.)

---

## 5) Systems (Classes + Responsibilities)

### 5.1 InputEngine
**Job:** Convert Pygame input → text buffer and commands.
- Maintains buffer string
- Handles BACKSPACE, ENTER, and text input
- Cursor blink every 500ms (dt-based)
- Respects `game_state.mode` (locked modes ignore typing)
- Returns `command: str|None` on ENTER

Future upgrades:
- command history (↑/↓), autocompletion, command aliases, clickable options

### 5.2 RenderEngine
**Job:** Draw terminal UI only. No story logic.
- Clears screen to black
- Draws visible lines from `game_state.history`
- Draws input prompt and cursor at bottom
- Handles wrapping (monospace)
- Font fallback strategy (Consolas/Courier/whatever available)

Future upgrades:
- CRT effects (scanlines, glow), channel colors, smooth scroll, layout themes

### 5.3 AudioEngine (Async Manager)
**Job:** Non-blocking audio jobs, with backend abstraction.
- `enqueue(AudioJob)`
- Worker thread processes jobs (network/file prep allowed)
- Worker thread **must not call Pygame**
- `poll_events()` returns `AudioEvent`s for main thread to process
- `shutdown()` clean stop via sentinel (no “forever daemon” dead end)

**AudioJob** (dict or dataclass):
- `kind: "tts"|"pause"|"sfx"`
- `text: str|None`
- `seconds: float|None`
- `voice_id: str|None`
- `interrupt: bool` (future)
- `tags/meta: dict` (future)

**AudioEvent**:
- `type: "STARTED"|"FINISHED"|"ERROR"`
- `job_id` / `info`

Backends:
- `MockAudioBackend` (sleep + print)
- `ElevenLabsBackend` later (API, caching, retries)
- optional `LocalTTSBackend` later

### 5.4 StoryLoader
**Job:** Load scenes (hardcoded now, JSON later) and validate schema.
- `load_scene(scene_id) -> Scene`
- Phase 1 may return hardcoded Scene object in memory

Future:
- JSON file reading, schema validation, versioning, localization

### 5.5 SceneRunner (Director / Brain)
**Job:** Execute scene scripts over time & input (dt-based).
- Holds current `Scene`
- Progresses steps sequentially via `scene_cursor`
- Handles waits, typewriter pacing, command gates
- Emits `LogEntry`s to history
- Enqueues `AudioJob`s
- Handles branching based on flags / tier
- Owns “input allowed?” decisions via `game_state.mode`

**Rule:** All story progression lives here, not in `main()`.

---

## 6) Story / Scene Format (Data-Driven Script)

### 6.1 Scene
- `id: str`
- `steps: list[Step]`
- Optional: `title`, `tags`, `defaults`

### 6.2 Step Types (Minimum Set)
- `print`: instant terminal line  
  - fields: `text`, `channel`
- `typewrite`: terminal line revealed over time  
  - fields: `text`, `channel`, `speed_cps`
- `wait`: delay without blocking  
  - fields: `seconds`
- `voice`: enqueue TTS line  
  - fields: `text`, `voice_id`, `channel="voice"`
- `require_command`: pause until player inputs accepted commands  
  - fields: `commands: list[str]`, `case_insensitive=True`, `on_success`
- `set_flag`: mutate game state  
  - fields: `key`, `value`
- `branch`: conditional jump  
  - fields: `conditions`, `goto_scene_or_step`

### 6.3 Channel Policy
- Terminal feed lines → `channel="terminal"` or `"system"`
- Voiceover lines → `channel="voice"` (may or may not also print)
- Narration lines → `channel="narration"` (often printed with dim style)

---

## 7) Timing & Pacing Rules (No Dead Ends)
- All delays use `wait` steps with `dt_ms`.
- Typewriter uses `speed_cps` and accumulators; never sleeps.
- Audio never blocks; SceneRunner can optionally “wait for audio finished” by listening to AudioEvents.

---

## 8) Threading + Safety Rules (Non-Negotiable)
- Worker threads may do: network calls, file I/O, decoding/prep, sleeping (mock latency).
- Worker threads may **NOT** do: `pygame.*` calls of any kind.
- Cross-thread communication only via `queue.Queue`.
- `GameState` mutations only on main thread.

---

## 9) File Layout (Growth-Friendly)
Phase 1 can be a single `main.py`, but structure code as if it will split into:
- `core/config.py`
- `core/state.py`
- `core/input_engine.py`
- `core/render_engine.py`
- `core/audio_engine.py`
- `story/story_loader.py`
- `story/scene_runner.py`
- `content/scenes/*.json` (future)

---

## 10) Future Upgrades (Planned Extensions)
- **ElevenLabs API:** backend swap + caching layer (hash text → audio file)
- **SFX:** sound cues triggered by `AudioJob(kind="sfx")`
- **Save/Load:** serialize `GameState`
- **Combat:** command-driven tactical prompts; structured options
- **UI polish:** CRT effects, channel colors, scrolling
- **Accessibility:** adjustable text speed, font size, optional voice-only mode
- **Testing:** headless SceneRunner tests (simulate dt, input commands)

---

## 11) Non-Goals (Phase 1)
- No external assets required
- No actual audio playback required (mock is acceptable)
- No file I/O for story yet (hardcoded scene allowed)
- No combat math/stats system yet

---

## 12) “AI Generation Rules” (Stability)
- Never add extra frameworks beyond standard library + pygame
- Keep `main()` minimal; story logic only in `SceneRunner`
- Use structured data models (`LogEntry`, `AudioJob`) instead of raw strings
- Include clean shutdown (`AudioEngine.shutdown()`, `pygame.quit()`)
- Avoid overengineering (Phase 1 = prove non-blocking + scripting + terminal render)
