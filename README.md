# Virtual Piano Bot v5.2

A Python utility that reads MIDI files and translates them into simulated keystrokes to play seamlessly on virtual pianos. 

*(Why version 5.2? I have been developing and refining this project through several private iterations. Version 5.2 marks its very first public release!)*

---

## Core Features

- **Smart Sustain & Anti-Stuck:** Accurately reads Note On/Off MIDI events to hold keys (Sustain) without freezing or causing stuck keys in your OS.
- **Auto-Fold Algorithm:** Automatically shifts out-of-bounds notes into playable octaves (between MIDI 36 and 96). No melody is left behind.
- **Interactive UI:** Built with Tkinter. Features a progress bar for real-time seeking, speed control, transpose settings, and global hotkeys.

## Tech Stack
- **Language:** Python
- **Libraries:** `Tkinter` (GUI), `Mido` (MIDI Parsing), `PyDirectInput` / `keyboard` (Hardware-level input simulation)

## **Note/Warnig**
**When you press play, you MUST immediately click on the virtual piano window and keep it in focus.** Do not click on any other window or application during playback (with the exception of the bot's own interface, provided you are not currently focused on a text input field). If you click elsewhere, the bot will rapidly type random keys into whatever window is currently active (which could result in spamming your chats or messing up your files).
