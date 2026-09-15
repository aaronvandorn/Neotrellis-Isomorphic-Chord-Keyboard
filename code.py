# SPDX-License-Identifier: MIT
#
# Isomorphic Grid MIDI Chord Controller
# Hardware: Adafruit 8x8 NeoTrellis Feather M4 Kit Pack (adafruit.com/product/1929)
#           -- four 4x4 NeoTrellis (seesaw) elastomer keypads tiled 2x2,
#              driven over I2C by a Feather M4 Express, output as class-
#              compliant USB MIDI (no extra MIDI hardware needed).
#
# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------
# 1. Copy this file to the CIRCUITPY drive as code.py.
# 2. From the Adafruit CircuitPython Library Bundle (matching your
#    CircuitPython version), copy these into /lib on CIRCUITPY:
#       adafruit_neotrellis/   (neotrellis.py, multitrellis.py, __init__.py)
#       adafruit_seesaw/       (dependency of adafruit_neotrellis)
#       adafruit_bus_device/   (dependency of adafruit_seesaw)
#       adafruit_pixelbuf.mpy  (dependency of adafruit_seesaw -- built into
#                                many M4 CircuitPython builds already; only
#                                copy it if boot raises ImportError)
#       adafruit_midi/         (adafruit_midi.py + note_on.py, note_off.py,
#                                control_change.py, ...)
# 3. Wire/solder the four NeoTrellis boards per the "Tiling" guide
#    (learn.adafruit.com/adafruit-neotrellis/tiling), addresses 0x2E
#    (top-left), 0x2F (top-right), 0x30 (bottom-left), 0x31 (bottom-right)
#    -- set with the A0-A4 solder jumpers on the back of each board.
# 4. Plug the Feather M4 into USB. It will enumerate as a class-compliant
#    USB MIDI device -- point your DAW/synth at it, no drivers needed.
#
# ---------------------------------------------------------------------------
# WHAT IT DOES
# ---------------------------------------------------------------------------
# The 7 left-hand columns (x = 0..6, all 8 rows) are the isomorphic
# playing surface: every pad's pitch is a fixed function of its grid
# position, so any chord or scale "shape" you learn can be played
# starting from any pad and it always sounds like the same shape,
# transposed. The rightmost column (x = 7) is a control strip.
#
# Two playing modes (toggle with the control strip):
#   NOTE mode  (default) -- every pad plays a single note. Because the
#               layout is isomorphic, you build chords by pressing the
#               same relative pad pattern anywhere on the grid.
#   CHORD mode -- every pad plays a whole voiced chord (root + a
#               selectable quality: maj/min/dim/aug/sus2/sus4/7/maj7/m7)
#               rooted at that pad's isomorphic pitch.
#
# LEDs are colour-coded by pitch class (a fixed 12-colour wheel) so the
# same note/chord root always looks the same colour anywhere on the
# grid; pads outside the currently selected scale are dimmed (NOTE
# mode only) and a pressed pad flashes white.
#
# Control strip (x = 7, top to bottom):
#   row 7  octave up          row 3  toggle NOTE/CHORD mode
#   row 6  octave down        row 2  cycle scale (NOTE) / chord quality (CHORD)
#   row 5  transpose up       row 1  sustain toggle (MIDI CC64)
#   row 4  transpose down     row 0  panic (all notes off)
#
# ---------------------------------------------------------------------------

import time

import board
import usb_midi

import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_neotrellis.multitrellis import MultiTrellis
from adafruit_neotrellis.neotrellis import NeoTrellis

# ---------------------------------------------------------------------------
# CONFIGURATION -- tweak these to taste
# ---------------------------------------------------------------------------

MIDI_CHANNEL = 1  # 1-16
NOTE_VELOCITY = 100  # NeoTrellis pads are on/off, not velocity-sensitive

# Isomorphic layout presets: (semitones per column-right, semitones per
# row-up). Pick one, or add your own.
LAYOUTS = {
    "fourths": (1, 5),  # chromatic across, perfect 4th up rows (LinnStrument/
    #                     guitar-style tuning) -- compact triad shapes. Default.
    "wicki_hayden": (2, 7),  # whole-tone across, perfect 5th up rows
    "thirds": (1, 4),  # chromatic across, major 3rd up rows -- very tight shapes
}
LAYOUT = "fourths"
COL_INTERVAL, ROW_INTERVAL = LAYOUTS[LAYOUT]

ROOT_NOTE = 36  # MIDI note for the bottom-left playing pad (36 = C2)
OCTAVE_OFFSET = 0  # in octaves, adjustable live from the control strip
OCTAVE_LIMIT = 4  # max |OCTAVE_OFFSET|

# MultiTrellis reports x, y measured from the TOP-LEFT corner. FLIP_Y makes
# pitch rise as you move UP the physical grid, like a normal keyboard.
FLIP_Y = True

SCALE_HIGHLIGHT = True  # dim out-of-scale pads in NOTE mode
SCALES = {
    "major": (0, 2, 4, 5, 7, 9, 11),
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "mixolydian": (0, 2, 4, 5, 7, 9, 10),
    "chromatic": tuple(range(12)),
}
SCALE_NAMES = list(SCALES.keys())
scale_index = 0

# (name, intervals-from-root) -- cycled with control-strip row 2 in CHORD mode
CHORD_QUALITIES = (
    ("maj", (0, 4, 7)),
    ("min", (0, 3, 7)),
    ("dim", (0, 3, 6)),
    ("aug", (0, 4, 8)),
    ("sus2", (0, 2, 7)),
    ("sus4", (0, 5, 7)),
    ("7", (0, 4, 7, 10)),
    ("maj7", (0, 4, 7, 11)),
    ("m7", (0, 3, 7, 10)),
)
chord_quality_index = 0

BRIGHTNESS = 0.35  # 0.0-1.0, keep modest -- 64 RGB LEDs draw real current
BOOT_ANIMATION = True

PLAY_COLS = range(0, 7)  # x = 0..6 are the isomorphic playing surface
CTRL_COL = 7  # x = 7 is the control strip

# ---------------------------------------------------------------------------
# COLOUR / STATE
# ---------------------------------------------------------------------------

# Fixed 12-colour wheel indexed by pitch class (note % 12), hand-picked so
# neighbouring pitch classes stay visually distinct.
PITCH_COLORS = (
    (255, 0, 0),
    (255, 60, 0),
    (255, 140, 0),
    (255, 200, 0),
    (170, 255, 0),
    (60, 255, 0),
    (0, 255, 90),
    (0, 255, 220),
    (0, 140, 255),
    (40, 40, 255),
    (150, 0, 255),
    (255, 0, 170),
)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)
DIM_SCALE = 0.18  # brightness multiplier for out-of-scale pads

# Control-strip base colours and a short label, by row (y)
CTRL_ROWS = {
    7: ("octave up", (0, 80, 255)),
    6: ("octave down", (0, 40, 140)),
    5: ("key up", (150, 0, 255)),
    4: ("key down", (80, 0, 140)),
    3: ("note/chord mode", (255, 120, 0)),
    2: ("cycle scale/quality", (255, 220, 0)),
    1: ("sustain", (0, 220, 220)),
    0: ("panic", (255, 0, 0)),
}
CTRL_DIM = 0.25
FLASH_SECONDS = 0.15

CHORD_MODE = False
SUSTAIN_ON = False

# active_notes[(x, y)] = list of MIDI note numbers currently sounding on that pad
active_notes = {}
# ctrl_flash[y] = time.monotonic() deadline until which that control pad
# stays lit white after a press
ctrl_flash = {}

# ---------------------------------------------------------------------------
# HARDWARE SETUP
# ---------------------------------------------------------------------------

i2c_bus = board.I2C()  # uses board.SCL / board.SDA

# 2x2 tiling, addresses set via the A0-A4 jumpers on each board's back.
# trelli[row][col]; row 0 = top, per the tiling guide.
trelli = [
    [NeoTrellis(i2c_bus, False, addr=0x2E), NeoTrellis(i2c_bus, False, addr=0x2F)],
    [NeoTrellis(i2c_bus, False, addr=0x30), NeoTrellis(i2c_bus, False, addr=0x31)],
]
trellis = MultiTrellis(trelli)
trellis.brightness = BRIGHTNESS

midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL - 1)

# ---------------------------------------------------------------------------
# MUSIC HELPERS
# ---------------------------------------------------------------------------


def _scale_row_col(x, y):
    row = (7 - y) if FLIP_Y else y
    return row, x


def note_for_pad(x, y):
    row, col = _scale_row_col(x, y)
    note = ROOT_NOTE + (OCTAVE_OFFSET * 12) + col * COL_INTERVAL + row * ROW_INTERVAL
    return max(0, min(127, note))


def chord_notes_for_pad(x, y):
    root = note_for_pad(x, y)
    _, intervals = CHORD_QUALITIES[chord_quality_index]
    notes = []
    for iv in intervals:
        n = root + iv
        if 0 <= n <= 127 and n not in notes:
            notes.append(n)
    return notes


def in_scale(pitch_class):
    scale = SCALES[SCALE_NAMES[scale_index]]
    root_pc = ROOT_NOTE % 12
    return ((pitch_class - root_pc) % 12) in scale


def pad_color(x, y):
    note = note_for_pad(x, y)
    pc = note % 12
    r, g, b = PITCH_COLORS[pc]
    if SCALE_HIGHLIGHT and not CHORD_MODE and not in_scale(pc):
        r, g, b = int(r * DIM_SCALE), int(g * DIM_SCALE), int(b * DIM_SCALE)
    return (r, g, b)


# ---------------------------------------------------------------------------
# DRAWING
# ---------------------------------------------------------------------------


def draw_play_pad(x, y, pressed=False):
    trellis.color(x, y, WHITE if pressed else pad_color(x, y))


def draw_all_play_pads():
    for y in range(8):
        for x in PLAY_COLS:
            draw_play_pad(x, y)


def draw_ctrl_pad(y, force_white=False):
    if force_white:
        trellis.color(CTRL_COL, y, WHITE)
        return
    _, color = CTRL_ROWS[y]
    active = (y == 3 and CHORD_MODE) or (y == 1 and SUSTAIN_ON)
    if active:
        trellis.color(CTRL_COL, y, color)
    else:
        dim = tuple(int(c * CTRL_DIM) for c in color)
        trellis.color(CTRL_COL, y, dim)


def draw_all_ctrl_pads():
    for y in range(8):
        draw_ctrl_pad(y)


# ---------------------------------------------------------------------------
# MIDI ACTIONS
# ---------------------------------------------------------------------------


def panic():
    global SUSTAIN_ON
    for note in range(128):
        midi.send(NoteOff(note, 0))
    active_notes.clear()
    if SUSTAIN_ON:
        SUSTAIN_ON = False
        midi.send(ControlChange(64, 0))


# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------


def play_callback(x, y, edge):
    if edge == NeoTrellis.EDGE_RISING:
        notes = chord_notes_for_pad(x, y) if CHORD_MODE else [note_for_pad(x, y)]
        active_notes[(x, y)] = notes
        midi.send([NoteOn(n, NOTE_VELOCITY) for n in notes])
        draw_play_pad(x, y, pressed=True)
    elif edge == NeoTrellis.EDGE_FALLING:
        notes = active_notes.pop((x, y), [])
        if notes:
            midi.send([NoteOff(n, 0) for n in notes])
        draw_play_pad(x, y, pressed=False)


def ctrl_callback(x, y, edge):
    global OCTAVE_OFFSET, ROOT_NOTE, CHORD_MODE, SUSTAIN_ON
    global scale_index, chord_quality_index

    if edge != NeoTrellis.EDGE_RISING:
        return

    if y == 7:
        OCTAVE_OFFSET = min(OCTAVE_LIMIT, OCTAVE_OFFSET + 1)
    elif y == 6:
        OCTAVE_OFFSET = max(-OCTAVE_LIMIT, OCTAVE_OFFSET - 1)
    elif y == 5:
        ROOT_NOTE = min(127, ROOT_NOTE + 1)
    elif y == 4:
        ROOT_NOTE = max(0, ROOT_NOTE - 1)
    elif y == 3:
        CHORD_MODE = not CHORD_MODE
    elif y == 2:
        if CHORD_MODE:
            chord_quality_index = (chord_quality_index + 1) % len(CHORD_QUALITIES)
        else:
            scale_index = (scale_index + 1) % len(SCALE_NAMES)
    elif y == 1:
        SUSTAIN_ON = not SUSTAIN_ON
        midi.send(ControlChange(64, 127 if SUSTAIN_ON else 0))
    elif y == 0:
        panic()

    ctrl_flash[y] = time.monotonic() + FLASH_SECONDS
    draw_ctrl_pad(y, force_white=True)
    draw_all_play_pads()  # key/octave/scale/mode may have changed


def flush_ctrl_flash():
    now = time.monotonic()
    for y in [y for y, deadline in ctrl_flash.items() if now >= deadline]:
        del ctrl_flash[y]
        draw_ctrl_pad(y)


# ---------------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------------

for _y in range(8):
    for _x in PLAY_COLS:
        trellis.activate_key(_x, _y, NeoTrellis.EDGE_RISING)
        trellis.activate_key(_x, _y, NeoTrellis.EDGE_FALLING)
        trellis.set_callback(_x, _y, play_callback)
    trellis.activate_key(CTRL_COL, _y, NeoTrellis.EDGE_RISING)
    trellis.set_callback(CTRL_COL, _y, ctrl_callback)

if BOOT_ANIMATION:
    for _y in range(8):
        for _x in range(8):
            trellis.color(_x, _y, (40, 0, 60))
            time.sleep(0.01)

draw_all_play_pads()
draw_all_ctrl_pads()

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

while True:
    # The NeoTrellis (seesaw) hardware can only be polled roughly every
    # 17ms or so.
    trellis.sync()
    flush_ctrl_flash()
    time.sleep(0.02)
