**Fibonacci Rhythm Generator for EuroPi**  
*Version 0.30 – DustyMirror2026*

![Version](https://img.shields.io/badge/version-0.35-blue)
![EuroPi](https://img.shields.io/badge/EuroPi-compatible-green)


🐚 Pinecone Pulse ⏱️ is a versatile Fibonacci clock generator for the [EuroPi](https://github.com/Allen-Synthesis/EuroPi) modular synthesiser platform. It produces evolving polyrhythms based on the Fibonacci sequence, with dual independent trigger tracks (CV1 / CV4) and multiple clock divisions. Perfect for generative patches, complex percussive sequences, or resetting other sequencers.

---

## Features

-  **Fibonacci‑driven rhythm** – sequences are built from the Fibonacci numbers (1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89).  
-  **Adjustable range** – set minimum (`MIN`) and maximum (`MAX`) values with knobs K1 and K2.  
-  **Two playback modes** – `LOOP` (unidirectional) and `ROUND` (ping‑pong).  
-  **Six trigger outputs**:
  - `CV1` – first beat of each Fibonacci module (normal sequence)  
  - `CV2` – quarter notes (every beat)  
  - `CV3` – half notes (every 2 beats)  
  - `CV4` – first beat of each *reverse* Fibonacci module  
  - `CV5` – every 3 beats  
  - `CV6` – every 5 beats  
-  **Internal / external clock** – switch seamlessly with B2. External BPM is auto‑detected and displayed.  
-  **OLED display** – shows current MIN, MAX, CV1/CV4 progress, BPM, and mode.  
-  **Settings mode** – long‑press B1 to adjust BPM and toggle Loop/Round.  
-  **Reset function** – short‑press B1 to reset both CV1 and CV4 to their first modules after the current module finishes.  
---

## Hardware Requirements

- [EuroPi](https://github.com/Allen-Synthesis/EuroPi) (Raspberry Pi Pico based)  
- 6 × trigger outputs (5V gates, 5ms pulse width)  
- 3 × analog inputs (K1, K2 – on‑board potentiometers, Ain)  
- 2 × buttons (B1, B2)  
- 1 × clock input (DIN)  
- 128×32 OLED display  

---

## Installation

1. **Ensure your EuroPi has the latest firmware** (follow the [EuroPi installation guide](https://github.com/Allen-Synthesis/EuroPi#installation)).

2. **Copy the script**  
   Place `pinecone_pulse.py` into the `software/contrib/` folder of your EuroPi project.

3. **Update `menu.py`**  
   Add the following entry inside the `EUROPI_SCRIPTS` OrderedDict:
   ```python
   ["Pinecone Pulse", "contrib.pinecone_pulse.PineconePulse"],

   ## Controls & Operation

| Control         | Function (Normal Mode)                                      | Function (Settings Mode – long‑press B1)         |
|----------------|-------------------------------------------------------------|--------------------------------------------------|
| **K1**         | Adjust `MIN` (Fibonacci index, 0–10)                       | Adjust **BPM** (21–233)                         |
| **K2**         | Adjust `MAX` (Fibonacci index, 0–10)                       | Toggle **Loop** / **Round** mode                 |
| **B1 (short)** | Reset request (returns to first module after current ends) | *(same)*                                         |
| **B1 (long)**  | Enter **Settings Mode**                                    | Exit Settings Mode                               |
| **B2 (short)** | Start / stop internal clock                                | *(same – only when not in Settings Mode)*       |
| **B1+B2 (long, >0.5s)** | Return to EuroPi main menu (any mode)           |                                                  |

> 💡 **Tip:** In Settings Mode the display shows a `@` symbol before the BPM to indicate you are editing.

---

## External Input Interface Specifications

### Analog Input (AIN)

| Function | Description | Voltage Range | Mapping Range | Smoothing |
|----------|-------------|---------------|---------------|-----------|
| **MAX Value Control** | Dynamically control the maximum value of the Fibonacci sequence via external CV | 0 - 5V | 0 - 10 indices (01,1,2,3,5,8,13,21,34,55,89) | 1st order low-pass filter (coefficient 0.2) |

**Usage Notes:**
- When AIN has signal (>0.1V), MAX value is controlled by CV, display shows `MAX:21*` (with `*` indicator)
- When AIN has no signal (<0.1V), MAX value is controlled by K2 knob manually
- Sequence updates automatically when CV changes; update triggered only when change exceeds 1 index (prevents frequent rebuilds)

**Typical Applications:**
| CV Source | Effect |
|-----------|--------|
| LFO Sine Wave | Periodic MAX value changes, rhythm length sweeps back and forth |
| Envelope Follower | Rhythm complexity changes with sound intensity |
| Sequencer CV | Different song sections correspond to different MAX values, structured rhythmic evolution |
| Manual CV (Slider/Knob) | Real-time manual control of rhythm range |

---

### Digital Input (DIN) - External Clock

| Function | Description | Logic Level | BPM Detection | Display Format |
|----------|-------------|-------------|----------------|-----------------|
| **External Clock Sync** | Receive external clock pulses to drive rhythm generation | 5V trigger | Moving average (4 pulses) | `EX:120BPM` |

**Usage Notes:**
- When internal clock is off, DIN external clock is used automatically
- BPM is detected and displayed in real-time with 4-pulse moving average
- Display value is scaled to 1/4 (matches other modules' 16th note convention)
- When no clock signal present, displays `EX:---BPM`

### Interface Priority Summary

| Input | Priority | Can Be Overridden By |
|-------|----------|---------------------|
| **AIN** | High (auto-overrides K2 when signal present) | K2 only when no signal |
| **DIN** | Low (used when internal clock off) | Internal clock when active |


## Display Layout
<img width="278" height="370" alt="sc" src="https://github.com/user-attachments/assets/ac7c8b21-16d6-4e70-8b67-38bdedd24fb5" />

- **Row 1** – Current MIN and MAX values (as Fibonacci numbers; `01` represents the first `1`).  
- **Row 2** – CV1 (left) and CV4 (right): `track_number current_beat / total_beats`.  
- **Row 3** – Clock source (`IN`=internal, `EX`=external), BPM, and playback mode (`LOOP` or `RND`).  
  In Settings Mode a leading `@` appears.

---

## Clock Behaviour

- **External clock** (DIN): the module listens to incoming triggers. BPM is calculated via a moving average and displayed as `EX:xxxBPM`.  
- **Internal clock**: press **B2** to start/stop. When switching from external to internal, the BPM is copied from the last detected external value, ensuring tempo continuity.  
- **No clock**: display shows `EX:---BPM` and no triggers are generated.

---

## Fibonacci Sequence & Module Selection

The module uses the classic Fibonacci numbers:

**0:01 , 1:1 , 2:2 , 3:3 , 4:5 , 5:8 , 6:13 , 7:21 , 8:34 , 9:55 , 10:89**

- `MIN` chooses the starting index, `MAX` the ending index.  
- If `MIN <= MAX` → normal ascending sequence.  
- If `MIN > MAX` → descending (reverse) sequence – the display does not show “REV”, but the order changes accordingly.  
- When `MIN == MAX`, the module repeats the same single number forever.

---

## Example Patch Ideas

- **Complex percussive loops** – send CV2 (quarter notes) to a hi‑hat, CV5 (every 3 beats) to a snare, and CV6 (every 5 beats) to a kick.  
- **Reset multiple sequencers** – route CV1 to the reset input of two different sequencers; they will restart each time a new Fibonacci module begins.  
- **Evolving melodic sequence** – use CV1 to trigger an envelope that advances a pitch sequencer; the irregular module lengths create ever‑changing phrase lengths.  
- **Ping‑pong modulation** – use CV4 (reverse‑track triggers) with ADSR to modulate filter cut‑off or VCA, creating a mirrored effect of the main rhythm.

Happy Pulsing 🐚 🐚 🐚 ⏱️ 🐚 ⏱️ ⏱️  🐚 ⏱️ ⏱️ ⏱️ ⏱️  🐚 ⏱️ ⏱️ ⏱️ ⏱️ ⏱️ ⏱️ ⏱️ 🐚 
