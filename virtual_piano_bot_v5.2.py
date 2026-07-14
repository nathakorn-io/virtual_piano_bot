import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import json
import time
import threading
import pydirectinput
import socket
import random
import re
import bisect
import mido  
import keyboard 
import os
from collections import defaultdict

# Config & Setup
pydirectinput.FAILSAFE = False
pydirectinput.PAUSE = 0.001
CONFIG_FILE = "vpb_v5_config.json"

VP_MAP_STD = {} 

BASE_KEYS = [
    ('1', False), ('1', True), ('2', False), ('2', True), ('3', False),
    ('4', False), ('4', True), ('5', False), ('5', True), ('6', False), ('6', True), ('7', False),
    ('8', False), ('8', True), ('9', False), ('9', True), ('0', False),
    ('q', False), ('q', True), ('w', False), ('w', True), ('e', False), ('e', True), ('r', False),
    ('t', False), ('t', True), ('y', False), ('y', True), ('u', False),
    ('i', False), ('i', True), ('o', False), ('o', True), ('p', False), ('p', True), ('a', False),
    ('s', False), ('s', True), ('d', False), ('d', True), ('f', False),
    ('g', False), ('g', True), ('h', False), ('h', True), ('j', False), ('j', True), ('k', False),
    ('l', False), ('l', True), ('z', False), ('z', True), ('x', False),
    ('c', False), ('c', True), ('v', False), ('v', True), ('b', False), ('b', True), ('n', False),
    ('m', False)
]

for i, (k, s) in enumerate(BASE_KEYS):
    midi = 36 + i
    VP_MAP_STD[midi] = (k, s, False) 

class VirtualPianoBotV5Sustain:
    def __init__(self, root):
        self.root = root
        self.root.title("Virtual Piano Bot V5.2")
        self.root.geometry("550x850")
        self.root.attributes('-topmost', True) 
        self.root.attributes('-alpha', 0.95) 

        # State vars
        self.is_playing = False
        self.is_paused = False
        self.song_data = None
        self.seek_req = None
        self.total_duration = 0
        
        # Anti-stuck note tracking
        self.active_notes_map = {} 
        self.physical_key_refs = defaultdict(int) 
        
        # Config Vars
        self.var_speed = tk.DoubleVar(value=1.0)
        self.var_transpose = tk.IntVar(value=0)
        self.var_autotune = tk.BooleanVar(value=False)
        self.var_nodrums = tk.BooleanVar(value=True)
        self.var_autofold = tk.BooleanVar(value=True)
        self.var_topmost = tk.BooleanVar(value=True)
        self.var_loop = tk.BooleanVar(value=False)
        self.var_progress = tk.DoubleVar(value=0)
        self.var_sustain = tk.BooleanVar(value=True) 
        self.var_humanize = tk.BooleanVar(value=False) 

        self._init_ui()
        self._load_config()
        self._setup_hotkeys()
        self.toggle_topmost()

    def _setup_hotkeys(self):
        try:
            keyboard.add_hotkey('alt+f7', lambda: self.root.after(0, self.toggle_pause))
            keyboard.add_hotkey('alt+f8', lambda: self.root.after(0, self.stop_playing))
            self.log("Hotkeys: Alt+F7 (Pause), Alt+F8 (Stop)")
        except: pass

    def _init_ui(self):
        tk.Label(self.root, text="Virtual Piano Bot V5.2", font=("Segoe UI", 16, "bold"), fg="#333").pack(pady=10)
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=5)
        
        t_play = tk.Frame(nb)
        nb.add(t_play, text="Player")
        
        # Mode title
        f_mode = tk.Frame(t_play, padx=10, pady=10)
        f_mode.pack(fill="x", padx=5, pady=5)
        tk.Label(f_mode, text="Standard (1-m keys)", font=("Segoe UI", 10, "bold"), fg="#555").pack(anchor="w")

        f_load = tk.Frame(t_play)
        f_load.pack(fill="x", padx=5, pady=5)
        self.lbl_file = tk.Label(f_load, text="No file loaded", fg="red", font=("Segoe UI", 9))
        self.lbl_file.pack()
        tk.Button(f_load, text="Load MIDI File", command=self.load_file, bg="#E3F2FD", height=2).pack(fill="x")

        f_dash = tk.LabelFrame(t_play, text="Control", padx=5, pady=5)
        f_dash.pack(fill="x", padx=5)
        self.lbl_time = tk.Label(f_dash, text="00:00 / 00:00", font=("Consolas", 12))
        self.lbl_time.pack()
        self.progress = ttk.Progressbar(f_dash, orient="horizontal", mode="determinate", variable=self.var_progress)
        self.progress.pack(fill="x", pady=10)
        self.progress.bind("<Button-1>", self.on_seek)
        
        f_btns = tk.Frame(f_dash)
        f_btns.pack(pady=5)
        
        # Control buttons
        self.btn_play = tk.Button(f_btns, text="Play", command=self.start_sequence, bg="#4CAF50", fg="white", width=12, state="disabled")
        self.btn_play.pack(side="left", padx=2)
        
        self.btn_pause = tk.Button(f_btns, text="Pause", command=self.toggle_pause, bg="#FFC107", width=12, state="disabled")
        self.btn_pause.pack(side="left", padx=2)
        
        self.btn_stop = tk.Button(f_btns, text="Stop", command=self.stop_playing, bg="#f44336", fg="white", width=12, state="disabled")
        self.btn_stop.pack(side="left", padx=2)

        t_set = tk.Frame(nb)
        nb.add(t_set, text="Settings")
        f_set = tk.Frame(t_set, padx=10, pady=10)
        f_set.pack(fill="both")
        
        tk.Label(f_set, text="Speed:", font="bold").pack(anchor="w")
        tk.Scale(f_set, variable=self.var_speed, from_=0.1, to=2.0, resolution=0.1, orient="horizontal").pack(fill="x")
        
        tk.Label(f_set, text="Transpose:", font="bold").pack(anchor="w", pady=(10,0))
        f_tr = tk.Frame(f_set)
        f_tr.pack(fill="x")
        tk.Button(f_tr, text="-", width=3, command=lambda: self.var_transpose.set(self.var_transpose.get()-1)).pack(side="left")
        tk.Entry(f_tr, textvariable=self.var_transpose, width=5, justify="center").pack(side="left", padx=5)
        tk.Button(f_tr, text="+", width=3, command=lambda: self.var_transpose.set(self.var_transpose.get()+1)).pack(side="left")
        tk.Button(f_tr, text="Auto-Calc", command=self.apply_smart_tune, bg="#E0F2F1").pack(side="left", padx=10)

        tk.Label(f_set, text="Options:", font="bold").pack(anchor="w", pady=(10,0))
        tk.Checkbutton(f_set, text="Hold Notes", variable=self.var_sustain, fg="blue").pack(anchor="w")
        tk.Checkbutton(f_set, text="Smart Auto-Tune", variable=self.var_autotune).pack(anchor="w")
        tk.Checkbutton(f_set, text="Auto-Fold", variable=self.var_autofold, fg="#009688").pack(anchor="w")
        tk.Checkbutton(f_set, text="Ignore Drums", variable=self.var_nodrums, fg="red").pack(anchor="w")
        tk.Checkbutton(f_set, text="Loop Song", variable=self.var_loop).pack(anchor="w")
        tk.Checkbutton(f_set, text="Always on Top", variable=self.var_topmost, command=self.toggle_topmost).pack(anchor="w")
        tk.Checkbutton(f_set, text="Humanize", variable=self.var_humanize, fg="purple").pack(anchor="w")

        self.log_box = scrolledtext.ScrolledText(self.root, height=7, state="disabled", font=("Consolas", 8))
        self.log_box.pack(fill="both", padx=10, pady=10)

    # KEY PRESS LOGIC
    def press_key_down(self, key_data):
        char, shift, ctrl = key_data
        if ctrl: pydirectinput.keyDown('ctrl')
        if shift: pydirectinput.keyDown('shift')
        pydirectinput.keyDown(char)
        if shift: pydirectinput.keyUp('shift')
        if ctrl: pydirectinput.keyUp('ctrl')

    def press_key_up(self, key_data):
        char, _, _ = key_data
        pydirectinput.keyUp(char)

    def tap_key(self, key_data):
        char, shift, ctrl = key_data
        if ctrl: pydirectinput.keyDown('ctrl')
        if shift: pydirectinput.keyDown('shift')
        pydirectinput.press(char)
        if shift: pydirectinput.keyUp('shift')
        if ctrl: pydirectinput.keyUp('ctrl')

    # CORE LOGIC
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("MIDI Files", "*.mid *.midi")])
        if not path: return
        try:
            mid = mido.MidiFile(path)
            events = []
            curr = 0.0
            
            for msg in mid:
                if msg.time > 0:
                    curr += max(0, msg.time + random.uniform(-0.02, 0.03))
                else:
                    curr += msg.time
                    
                if msg.type == 'note_on' and msg.velocity > 0:
                    ch = getattr(msg, 'channel', 0)
                    events.append({'t': int(curr*1000), 'k': msg.note, 'ch': ch, 'act': 1})
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    ch = getattr(msg, 'channel', 0)
                    events.append({'t': int(curr*1000), 'k': msg.note, 'ch': ch, 'act': 0})
            
            if not events: raise ValueError("Empty MIDI")
            events.sort(key=lambda x: x['t'])
            
            self.song_data = events
            self.total_duration = events[-1]['t']
            self.lbl_file.config(text=f"Loaded: {os.path.basename(path)}", fg="green")
            self.reset_ui()
            
            if self.var_autotune.get(): self.apply_smart_tune()
            
        except Exception as e:
            self.lbl_file.config(text="Error", fg="red")
            self.log(str(e))

    def apply_smart_tune(self):
        if not self.song_data: return
        notes = [n['k'] for n in self.song_data if n['act'] == 1 and (not self.var_nodrums.get() or n['ch'] != 9)]
        if not notes: return
        
        # 1-m range bounds
        RANGE = (36, 96)  
        best_t, max_score = 0, -1
        
        for t in range(-48, 49):
            score = sum(1 for n in notes if RANGE[0] <= (n + t) <= RANGE[1])
            if score > max_score: 
                max_score, best_t = score, t
                
        self.var_transpose.set(best_t)
        self.log(f"Auto-Tune: {best_t:+d}")

    def start_sequence(self):
        delay = 2.0
        self.log(f"Starting in {delay}s...")
        self.start_thread(time.time() + delay)

    def start_thread(self, start_ts):
        self.is_playing = True
        self.is_paused = False
        self.seek_req = None
        self.btn_play.config(state="disabled")
        self.btn_pause.config(state="normal", text="Pause (Alt+F7)", bg="#FFC107")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.run_player, args=(start_ts,), daemon=True).start()

    def run_player(self, start_ts):
        if not self.song_data: return
        timeline = defaultdict(list)
        for n in self.song_data:
            if self.var_nodrums.get() and n['ch'] == 9: continue
            timeline[n['t']].append(n)
            
        times = sorted(timeline.keys())
        self.release_all_keys()

        while time.time() < start_ts:
            if not self.is_playing: 
                self.reset_ui()
                return
            time.sleep(0.001)

        base_ts = start_ts * 1000
        idx = 0
        max_idx = len(times)
        
        while self.is_playing and idx < max_idx:
            spd = self.var_speed.get()
            
            if self.seek_req:
                self.release_all_keys()
                base_ts = (time.time()*1000) - (self.seek_req/spd)
                idx = bisect.bisect_left(times, self.seek_req)
                self.seek_req = None
                continue
            
            if self.is_paused:
                self.release_all_keys()
                p_start = time.time()
                while self.is_paused and self.is_playing:
                    if self.seek_req: break
                    time.sleep(0.1)
                base_ts += (time.time()-p_start)*1000
                continue

            curr_note_time = times[idx]
            target_real = (curr_note_time / spd)
            
            if self.var_humanize.get():
                target_real += random.uniform(-0.02, 0.035)
            
            while self.is_playing:
                if self.is_paused or self.seek_req: break
                elapsed = (time.time()*1000) - base_ts
                if int(elapsed) % 200 == 0: 
                    self.root.after(0, lambda e=elapsed: self.update_time_lbl(e))
                if elapsed >= target_real: break
                time.sleep(0.0001)

            if self.is_paused or self.seek_req: continue

            trans = self.var_transpose.get()
            do_fold = self.var_autofold.get()
            use_sustain = self.var_sustain.get()

            # limits 1-m range
            MIN_KEY, MAX_KEY = 36, 96
            events = timeline[curr_note_time]
            
            if not use_sustain: 
                keys_to_press = []
                for n in events:
                    if n['act'] == 1:
                        val = n['k'] + trans
                        if do_fold:
                            while val < MIN_KEY: val += 12
                            while val > MAX_KEY: val -= 12
                        if val in VP_MAP_STD: 
                            keys_to_press.append(VP_MAP_STD[val])
                
                keys_to_press = list(set(keys_to_press))
                for k in keys_to_press: 
                    self.tap_key(k)

            else: 
                # Process note-offs first to free up physical keys
                for n in events:
                    if n['act'] == 0:
                        note_id = (n['ch'], n['k'])
                        if note_id in self.active_notes_map:
                            char_key = self.active_notes_map.pop(note_id)
                            self.physical_key_refs[char_key] -= 1
                            
                            if self.physical_key_refs[char_key] <= 0:
                                pydirectinput.keyUp(char_key)
                                self.physical_key_refs[char_key] = 0

                # Process note-ons
                for n in events:
                    if n['act'] == 1:
                        val = n['k'] + trans
                        if do_fold:
                            while val < MIN_KEY: val += 12
                            while val > MAX_KEY: val -= 12
                        
                        if val in VP_MAP_STD:
                            k_data = VP_MAP_STD[val]
                            char_key = k_data[0]
                            note_id = (n['ch'], n['k'])
                            
                            # Edge case: overlapping Note-Ons for same key. Release briefly before press.
                            if note_id in self.active_notes_map:
                                old_char = self.active_notes_map.pop(note_id)
                                self.physical_key_refs[old_char] -= 1
                                if self.physical_key_refs[old_char] <= 0:
                                    pydirectinput.keyUp(old_char)
                                    self.physical_key_refs[old_char] = 0
                            
                            if self.physical_key_refs[char_key] == 0:
                                self.press_key_down(k_data)
                            else:
                                self.press_key_up(k_data)
                                time.sleep(0.001)
                                self.press_key_down(k_data)
                                
                            self.physical_key_refs[char_key] += 1 
                            self.active_notes_map[note_id] = char_key
                            
                            if self.var_humanize.get():
                                time.sleep(random.uniform(0.005, 0.020))

            idx += 1

        self.release_all_keys()
        self.is_playing = False
        
        if self.var_loop.get(): 
            self.root.after(100, self.start_sequence)
        else: 
            self.reset_ui()

    # Clear all held physical keys cleanly
    def release_all_keys(self):
        for char, count in list(self.physical_key_refs.items()):
            if count > 0:
                pydirectinput.keyUp(char)
        self.physical_key_refs.clear()
        self.active_notes_map.clear()
        pydirectinput.keyUp('shift')
        pydirectinput.keyUp('ctrl')

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    cfg = json.load(f)
                    self.var_speed.set(cfg.get('speed', 1.0))
                    self.var_autofold.set(cfg.get('autofold', True))
                    self.var_nodrums.set(cfg.get('nodrums', True))
                    self.var_sustain.set(cfg.get('sustain', True))
                    self.var_autotune.set(cfg.get('autotune', False)) 
                    self.var_humanize.set(cfg.get('humanize', False))
            except: pass

    def _save_config(self):
        cfg = {
            'speed': self.var_speed.get(),
            'autofold': self.var_autofold.get(),
            'nodrums': self.var_nodrums.get(),
            'sustain': self.var_sustain.get(),
            'autotune': self.var_autotune.get(),
            'humanize': self.var_humanize.get()
        }
        try:
            with open(CONFIG_FILE, 'w') as f: 
                json.dump(cfg, f)
        except: pass

    def on_close(self):
        try: keyboard.unhook_all()
        except: pass
        self.release_all_keys()
        self._save_config()
        self.root.destroy()

    def stop_playing(self): 
        self.is_playing = False
        self.is_paused = False
        self.release_all_keys()
        self.log("Stopped.")

    def toggle_pause(self):
        if not self.is_playing and self.btn_play['state'] == 'normal': 
            self.start_sequence()
            return
        
        self.is_paused = not self.is_paused
        if self.is_paused: 
            self.release_all_keys()
            
        self.btn_pause.config(
            text="Resume" if self.is_paused else "Pause", 
            bg="#2196F3" if self.is_paused else "#FFC107"
        )

    def on_seek(self, event):
        if not self.total_duration: return
        self.seek_req = (event.x / event.widget.winfo_width()) * self.total_duration

    def update_time_lbl(self, ms):
        self.var_progress.set((ms/self.total_duration)*100 if self.total_duration else 0)
        self.lbl_time.config(text=f"{int(ms/1000)//60:02d}:{int(ms/1000)%60:02d} / {int(self.total_duration/1000)//60:02d}:{int(self.total_duration/1000)%60:02d}")

    def reset_ui(self): 
        self.root.after(0, self._reset_ui_internal)

    def _reset_ui_internal(self):
        self.btn_play.config(state="normal")
        self.btn_pause.config(state="disabled", text="Pause (Alt+F7)", bg="#FFC107")
        self.btn_stop.config(state="disabled")

    def toggle_topmost(self): 
        self.root.attributes('-topmost', self.var_topmost.get())

    def log(self, msg): 
        self.log_box.config(state="normal")
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = VirtualPianoBotV5Sustain(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()