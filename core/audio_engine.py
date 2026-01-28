# core/audio_engine.py

import threading
import queue
import time
import os
from typing import Optional, List, Any
from core.config import GlobalConfig
from core.audio_cache import AudioCache
from core.elevenlabs_backend import ElevenLabsBackend
from core.local_tts_backend import LocalTTSBackend
from core.audio_models import AudioJob, AudioEvent, AudioBackendBase
from core.sfx_library import SFXLibrary

class MockAudioBackend(AudioBackendBase):
    def prepare(self, job: AudioJob, cache_path: Optional[str] = None) -> Optional[str]:
        if job.kind == "tts":
            duration = max(1.0, len(job.text or "") * 0.05)
            print(f"\n[MOCK AUDIO] Speaking: '{job.text}' ({duration:.1f}s)...")
            time.sleep(duration)
        elif job.kind == "pause":
            print(f"\n[MOCK AUDIO] Pausing for {job.seconds}s...")
            time.sleep(job.seconds)
        elif job.kind == "sfx":
            print(f"\n[MOCK AUDIO] SFX Trigger: {job.voice_id}")
            time.sleep(0.1)
        return None

class AudioEngine:
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.job_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.cache = AudioCache(config)
        self.sfx_library = SFXLibrary(config)
        
        # Select Backend
        if self.config.AUDIO_BACKEND == "elevenlabs":
            self.backend = ElevenLabsBackend(config)
        elif self.config.AUDIO_BACKEND == "local":
            self.backend = LocalTTSBackend(config)
        else:
            self.backend = MockAudioBackend()
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def enqueue(self, job: AudioJob):
        self.job_queue.put(job)

    def poll_events(self) -> List[AudioEvent]:
        events = []
        try:
            while True:
                events.append(self.event_queue.get_nowait())
        except queue.Empty:
            pass
        return events

    def shutdown(self):
        print("[AudioEngine] Shutting down...")
        self.enqueue(None)
        self.worker_thread.join(timeout=2.0)
        self.is_running = False

    def _worker_loop(self):
        while self.is_running:
            try:
                job = self.job_queue.get()
                if job is None: break

                self.event_queue.put(AudioEvent("STARTED", job))
                
                try:
                    result_path = None
                    
                    # --- HANDLING SFX ---
                    if job.kind == "sfx":
                        # SFX are local files, no generation needed
                        result_path = self.sfx_library.get_path(job.sfx_id)
                        if not result_path:
                            # Log warning but don't crash
                            print(f"[AudioEngine] SFX Missing: {job.sfx_id}")
                    
                    # --- HANDLING TTS ---
                    elif job.kind == "tts" and job.text:
                        cache_key = self.cache.get_key(self.config.AUDIO_BACKEND, job)
                        if self.cache.has(cache_key):
                            result_path = self.cache.get_filepath(cache_key)
                        
                        if not result_path:
                            target_path = self.cache.get_filepath(cache_key) if cache_key else None
                            result_path = self.backend.prepare(job, cache_path=target_path)
                    
                    # --- RESULT ---
                    if result_path:
                        self.event_queue.put(AudioEvent("AUDIO_READY", job, data=result_path))
                    else:
                        self.event_queue.put(AudioEvent("FINISHED", job))

                except Exception as e:
                    print(f"[AudioEngine] Backend Error: {e}")
                    self.event_queue.put(AudioEvent("ERROR", job, data=str(e)))
                    
                self.job_queue.task_done()
                
            except Exception as e:
                print(f"[AudioEngine] Critical Worker Error: {e}")