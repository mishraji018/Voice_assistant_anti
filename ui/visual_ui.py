import tkinter as tk
import threading
import math
import random
import time

# ── Palette (HUD Design) ───────────────────────────────────────────────────
BG          = "#050a0f"          # Near black deep blue
ACCENT_CYAN = "#00e5ff"          # Primary cyan 
ACCENT_PURPLE = "#7c4dff"        # Secondary purple
ORB_GLOW    = "#006677"          # Dim glow for the central orb
RING_COLOR  = "#002a35"          # Dark cyan for background rings
TEXT_COLOR  = "#00e5ff"

# ── Constants ─────────────────────────────────────────────────────────────
W, H        = 400, 400
CX, CY      = W // 2, H // 2
ORB_R       = 85                 # Central orb radius
FPS         = 60
TICK        = 1000 // FPS

class JarvisUI:
    def __init__(self, frameless: bool = False):
        self._state = "IDLE"
        self._subtitle = ""
        self._lock = threading.Lock()
        self._tick = 0
        self._mic_level = 0.0
        self._frameless = frameless
        
        # Orbital positions
        self._p1_angle = 0.0 # Cyan particle
        self._p2_angle = 180.0 # Purple particle

    def set_state(self, state: str) -> None:
        with self._lock:
            self._state = state.upper()
        print(f"[UI] State → {self._state}")

    def set_subtitle(self, text: str) -> None:
        with self._lock:
            self._subtitle = text[:55]

    def clear_subtitle(self) -> None:
        with self._lock:
            self._subtitle = ""

    def set_audio_level(self, level: float) -> None:
        with self._lock:
            self._mic_level = max(0.0, min(1.0, float(level)))

    def destroy(self) -> None:
        try:
            self._root.after(0, self._root.destroy)
        except Exception:
            pass

    def run(self) -> None:
        """Entry point for the UI (should run on main thread)."""
        self._root = tk.Tk()
        self._root.title("J.A.R.V.I.S HUD")
        self._root.configure(bg=BG)
        
        if self._frameless:
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            self._root.attributes("-transparentcolor", BG)
        else:
            self._root.attributes("-topmost", True) # Keep it on top but with window controls
            
        # Center window
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        px, py = (sw - W) // 2, (sh - H) // 2
        self._root.geometry(f"{W}x{H}+{px}+{py}")

        self._canvas = tk.Canvas(self._root, width=W, height=H, bg=BG, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        
        self._animate()
        self._root.mainloop()

    def _animate(self) -> None:
        self._tick += 1
        c = self._canvas
        c.delete("all")
        
        with self._lock:
            state = self._state
            mic = self._mic_level
            subtitle = self._subtitle

        t = self._tick / FPS
        
        # 1. Background static rings
        c.create_oval(CX-140, CY-140, CX+140, CY+140, outline="#001a1f", width=1)
        c.create_oval(CX-125, CY-125, CX+125, CY+125, outline="#081520", width=1)
        
        # 2. Concentric animated rings
        # Inner active ring
        r_inner = 115 + math.sin(t * 2) * 2
        c.create_oval(CX-r_inner, CY-r_inner, CX+r_inner, CY+r_inner, outline="#003344", width=2)
        
        # Outer active ring
        r_outer = 135
        c.create_oval(CX-r_outer, CY-r_outer, CX+r_outer, CY+r_outer, outline="#0a1a2a", width=1)

        # 3. Orbiting particles
        self._p1_angle += 1.5
        p1_rad = 135
        x1 = CX + p1_rad * math.cos(math.radians(self._p1_angle))
        y1 = CY + p1_rad * math.sin(math.radians(self._p1_angle))
        c.create_oval(x1-4, y1-4, x1+4, y1+4, fill=ACCENT_CYAN, outline="")
        c.create_oval(x1-8, y1-8, x1+8, y1+8, outline=ACCENT_CYAN, width=1)

        self._p2_angle -= 1.0
        p2_rad = 155
        x2 = CX + p2_rad * math.cos(math.radians(self._p1_angle * 0.7))
        y2 = CY + p2_rad * math.sin(math.radians(self._p1_angle * 0.7))
        c.create_oval(x2-3, y2-3, x2+3, y2+3, fill=ACCENT_PURPLE, outline="")

        # 4. Central Orb
        pulse = 0.95 + 0.05 * math.sin(t * 3)
        if state == "LISTENING":
            pulse = 1.0 + mic * 0.1
        elif state == "SPEAKING":
            pulse = 1.0 + 0.1 * math.sin(t * 10)
            
        r = ORB_R * pulse
        c.create_oval(CX-r, CY-r, CX+r, CY+r, fill="#05101a", outline="#004455", width=3)
        c.create_oval(CX-r-5, CY-r-5, CX+r+5, CY+r+5, outline="#00e5ff", width=1)
        
        # 5. Microphone Icon
        mic_color = ACCENT_CYAN if state != "IDLE" else "#005566"
        c.create_rectangle(CX-8, CY-15, CX+8, CY+5, fill="", outline=mic_color, width=2)
        c.create_arc(CX-8, CY-25, CX+8, CY-5, start=0, extent=180, outline=mic_color, width=2, style=tk.ARC)
        c.create_arc(CX-8, CY-5, CX+8, CY+15, start=180, extent=180, outline=mic_color, width=2, style=tk.ARC)
        c.create_arc(CX-15, CY-5, CX+15, CY+20, start=180, extent=180, outline=mic_color, width=2, style=tk.ARC)
        c.create_line(CX, CY+20, CX, CY+28, fill=mic_color, width=2)
        
        # 6. Waveform (if LISTENING)
        if state == "LISTENING" and mic > 0.01:
            for i in range(10):
                h = random.randint(5, int(10 + mic * 40))
                x_off = (i - 5) * 12
                c.create_line(CX+x_off, CY+50-h, CX+x_off, CY+50+h, fill=ACCENT_CYAN, width=3)

        # 7. Subtitle
        if subtitle:
            c.create_text(CX, H-40, text=subtitle, fill="#a0b0d0", font=("Arial", 10, "bold"))

        self._root.after(TICK, self._animate)

if __name__ == "__main__":
    ui = JarvisUI(frameless=False)
    ui.run()
