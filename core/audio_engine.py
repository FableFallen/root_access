# core/audio_engine.py

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import Optional, List

# --- Data Models ---

@dataclass
class AudioJob:
    """
    A unit of work for the AudioEngine.
    """
    kind: str  # "tts", "pause", "sfx"
    text: Optional[str] = None
    seconds: float = 0.0
    voice_id: str = "default"
    
@dataclass
class AudioEvent:
    """
    Feedback sent from Worker -> Main Thread.
    """
    type: str  # "STARTED", "FINISHED", "ERROR"
    job: AudioJob
    timestamp: float = field(default_factory=time.time)

# --- Backends ---

class AudioBackendBase:
    """Interface for audio drivers (Mock, ElevenLabs, etc)."""
    def play_job(self, job: AudioJob):
        raise NotImplementedError

class MockAudioBackend(AudioBackendBase):
    """
    Simulates latency and logging without actual audio hardware.
    Perfect for development and maintaining the 'cold' vibe.
    """
    def play_job(self, job: AudioJob):
        if job.kind == "tts":
            # Simulate speaking time: ~0.1s per character, min 1s
            duration = max(1.0, len(job.text or "") * 0.05)
            print(f"\n[MOCK AUDIO] Speaking: '{job.text}' ({duration:.1f}s)...")
            time.sleep(duration)
            
        elif job.kind == "pause":
            print(f"\n[MOCK AUDIO] Pausing for {job.seconds}s...")
            time.sleep(job.seconds)
            
        elif job.kind == "sfx":
            print(f"\n[MOCK AUDIO] SFX Trigger: {job.voice_id}")
            time.sleep(0.1) # Minimal latency for SFX

# --- Engine ---

class AudioEngine:
    """
    Asynchronous manager for audio playback.
    Main Thread -> enqueue() -> Queue -> Worker Thread
    Worker Thread -> events -> Queue -> poll_events() -> Main Thread
    """
    def __init__(self, backend=None):
        self.job_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.backend = backend if backend else MockAudioBackend()
        
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def enqueue(self, job: AudioJob):
        """Add a job to the queue. Safe to call from Main Thread."""
        self.job_queue.put(job)

    def poll_events(self) -> List[AudioEvent]:
        """
        Retrieve all pending events. Call this every frame in Main Loop.
        Does NOT block.
        """
        events = []
        try:
            while True:
                # get_nowait raises Empty when done
                events.append(self.event_queue.get_nowait())
        except queue.Empty:
            pass
        return events

    def shutdown(self):
        """Signals the worker thread to stop and waits for it to join."""
        print("[AudioEngine] Shutting down...")
        self.enqueue(None) # Sentinel value
        self.worker_thread.join(timeout=2.0)
        self.is_running = False

    def _worker_loop(self):
        """
        The heavy lifting happens here. 
        STRICT RULE: NO Pygame calls allowed here.
        """
        while self.is_running:
            try:
                # Blocking get() - waits until a job arrives
                job = self.job_queue.get()
                
                # 1. Check Sentinel (Shutdown)
                if job is None:
                    break

                # 2. Process Job
                self.event_queue.put(AudioEvent("STARTED", job))
                
                try:
                    self.backend.play_job(job)
                    self.event_queue.put(AudioEvent("FINISHED", job))
                except Exception as e:
                    print(f"[AudioEngine] Backend Error: {e}")
                    self.event_queue.put(AudioEvent("ERROR", job))
                    
                self.job_queue.task_done()
                
            except Exception as e:
                print(f"[AudioEngine] Critical Worker Error: {e}")