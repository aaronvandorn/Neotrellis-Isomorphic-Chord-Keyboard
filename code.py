# SPDX-License-Identifier: MIT
#
# Isomorphic Grid MIDI Chord Controller
# Hardware: Adafruit 8x8 NeoTrellis Feather M4 Kit Pack (adafruit.com/product/1929)
#           -- four 4x4 NeoTrellis (seesaw) elastomer keypads tiled 2x2,
#              driven over I2C by a Feather M4 Express.
#
# MIDI OUTPUT -- pick a backend below with MIDI_BACKEND:
#   "usb"  -- class-compliant USB MIDI. Works when the Feather is plugged
#             into a computer (or anything else that acts as a genuine USB
#             HOST). Many small standalone synths (including Roland's AIRA
#             Compact line, e.g. the S-1) do NOT host other USB devices --
#             their USB-C port is itself a "device" port meant for a
#             computer -- so plugging the Feather straight into one of
#             those will NOT work even though a cable/power connection is
#             detected. Use "uart" for those.
#   "uart" -- real 5-pin-DIN-style MIDI over a hardware serial port, wired
#             out to a 3.5mm TRS jack via a simple 2-resistor circuit (see
#             below). This is what you want for the S-1 and most other
#             hardware synths' MIDI IN jacks.
#
# TRS MIDI-OUT CIRCUIT (for MIDI_BACKEND = "uart"):
#   Roland's AIRA Compact gear (S-1, P-6, etc.) uses 3.5mm TRS "Type-A"
#   MIDI wiring, same polarity as the standard DIN-5 MIDI OUT circuit:
#     Feather "USB" pin (5V, present while USB-powered)
#         --[220ohm resistor]--> TRS RING
#     Feather "TX" pin
#         --[220ohm resistor]--> TRS TIP
#     Feather "GND"
#         -------------------->  TRS SLEEVE
#   That's it -- no optoisolator needed on the output side. Use a normal
#   3.5mm TRS-A to TRS-A (or TRS-A to 5-pin-DIN) cable from that jack into
#   the S-1's MIDI IN. If your board is ever battery-only (no USB 5V
#   present), swap in the Feather's "3V" pin and drop both resistors to
#   ~150ohm so loop current stays in a sane range.
#
# CV/GATE OUTPUT (optional, CV_GATE_ENABLED below):
#   Adds real 1V/octave pitch CV + a gate signal for driving Eurorack gear
#   directly from the same grid, using a Makerfabs Mabee_DAC_GP8413 (2ch,
#   15-bit, 0-10V, I2C address 0x59 by default -- makerfabs.com/mabee-dac-
#   gp8413.html) on the SAME I2C bus as the NeoTrellis (just a different
#   address, no extra wiring for the bus itself). This is a real digital-
#   to-analog converter, not a MIDI path -- it can't stand in for the UART
#   MIDI-out circuit above (an I2C DAC is far too slow/imprecise to bit-
#   bang a 31.25kbaud MIDI bitstream, and its 0-10V swing would overdrive
#   a MIDI input's current loop anyway). It runs alongside MIDI, not
#   instead of it.
#     DAC channel 0 (pitch CV) -> TRS TIP    (through a series resistor,
#                                              e.g. 1k, is good practice)
#     DAC channel 1 (gate)     -> TRS RING   (likewise)
#     DAC GND                  -> TRS SLEEVE
#   This is a *monophonic* CV/Gate pair even though the grid is polyphonic:
#   pitch follows last-note-priority (the most recently pressed still-held
#   pad), gate is high whenever any pad is held. If your board doesn't ACK
#   at 0x59, check its silkscreen for an address-select jumper and update
#   DAC_I2C_ADDRESS below. Missing/unwired DAC is handled gracefully --
#   the grid and MIDI still work fine, just without CV/Gate.
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
#    CV/Gate needs no extra library -- adafruit_bus_device is already
#    required above (it's a dependency of adafruit_seesaw), and the small
#    GP8413 driver below is included right in this file.
# 3. Wire/solder the four NeoTrellis boards per the "Tiling" guide
#    (learn.adafruit.com/adafruit-neotrellis/tiling), addresses 0x2E
#    (top-left), 0x2F (top-right), 0x30 (bottom-left), 0x31 (bottom-right)
#    -- set with the A0-A4 solder jumpers on the back of each board.
# 4. MIDI_BACKEND = "usb": plug the Feather M4 into USB -- it enumerates as
#    a class-compliant USB MIDI device, point your DAW/synth at it.
#    MIDI_BACKEND = "uart": build the TRS-out circuit above, then plug that
#    jack into your synth's MIDI IN with a TRS-A (or TRS-A-to-DIN) cable.
# 5. Optional: wire the GP8413 onto the shared I2C bus and into a second
#    TRS jack per the CV/GATE notes above; leave CV_GATE_ENABLED = False
#    below until it's wired if you're bringing this up in stages.
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
#   row 5  transpose up       row 1  cycle sustain length: off/short/med/long/longest
#   row 4  transpose down     row 0  panic (all notes off)
#
# Sustain here is a LOCAL, timed note-off delay (not a MIDI sustain-pedal
# CC64 message) -- each press of row 1 steps to the next hold length, so
# notes always let go on their own after a bounded, predictable time
# instead of ringing until you remember to release a pedal.
#
# ---------------------------------------------------------------------------

import time

import board

import adafruit_midi
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_neotrellis.multitrellis import MultiTrellis
from adafruit_neotrellis.neotrellis import NeoTrellis

# ---------------------------------------------------------------------------
# GP8413 CV/GATE DAC DRIVER (minimal, ported from Makerfabs/DFRobot's
# GP8XXX_IIC reference library's register-level protocol; range is pinned
# to 0-10V permanently rather than auto-switching, so 1V/octave scaling
# never changes underneath you mid-performance)
# ---------------------------------------------------------------------------

from adafruit_bus_device import i2c_device


class GP8413:
    """2-channel 15-bit I2C DAC, 0-10V output, fixed range."""

    _RANGE_REG = 0x01
    _CH0_REG = 0x02
    _CH1_REG = 0x04
    _RANGE_10V = 0x11
    _RESOLUTION = 0x7FFF  # 15-bit

    def __init__(self, i2c_bus, address=0x59):
        self._device = i2c_device.I2CDevice(i2c_bus, address)
        with self._device as i2c:
            i2c.write(bytes([self._RANGE_REG, self._RANGE_10V]))

    def _write_channel(self, reg, voltage):
        voltage = max(0.0, min(10.0, voltage))
        code = int((voltage / 10.0) * self._RESOLUTION)
        value = (code << 1) & 0xFFFF
        with self._device as i2c:
            i2c.write(bytes([reg, value & 0xFF, (value >> 8) & 0xFF]))

    def set_channel0(self, voltage):
        self._write_channel(self._CH0_REG, voltage)

    def set_channel1(self, voltage):
        self._write_channel(self._CH1_REG, voltage)


# ---------------------------------------------------------------------------
# CONFIGURATION -- tweak these to taste
# ---------------------------------------------------------------------------

MIDI_BACKEND = "uart"  # "usb" or "uart" -- see notes at the top of this file
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

# Extra ring-on time (seconds) added after a pad is released, cycled with
# control-strip row 1. Index 0 is "off" -- notes stop the instant you let
# go, same as if this feature didn't exist.
SUSTAIN_LEVELS = (0.0, 0.15, 0.4, 1.0, 2.5)
sustain_level_index = 0

BRIGHTNESS = 0.2  # 0.0-1.0. Keep this modest -- 64 RGB LEDs plus the DAC
#                    add up to real current. If you see dimming/reddish
#                    flicker as you press more keys, that's a power
#                    brownout: lower this further and/or switch from a
#                    computer's USB port to a proper 5V/1A+ USB power
#                    adapter (laptop ports are often current-limited well
#                    below what a fully-lit 8x8 NeoPixel grid can pull).
BOOT_ANIMATION = True

PLAY_COLS = range(0, 7)  # x = 0..6 are the isomorphic playing surface
CTRL_COL = 7  # x = 7 is the control strip

# CV/Gate output via an optional Makerfabs Mabee_DAC_GP8413 on the shared
# I2C bus -- see the CV/GATE OUTPUT notes at the top of this file.
CV_GATE_ENABLED = True
DAC_I2C_ADDRESS = 0x59
CV_REFERENCE_NOTE = 0  # MIDI note that maps to 0V -- kept at 0 so CV can
#                         never need to go negative (the DAC is 0-10V only)
CV_MAX_VOLTS = 10.0
GATE_HIGH_VOLTS = 5.0  # conservative default; raise toward 10V if your
#                         gate input wants a hotter signal

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

# active_notes[(x, y)] = list of MIDI note numbers currently sounding on that pad
active_notes = {}
# pending_release[(x, y)] = (list of notes, time.monotonic() deadline) for
# pads that were released while a sustain level > 0 was selected -- their
# NoteOff is delayed until the deadline instead of sent immediately
pending_release = {}
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

if MIDI_BACKEND == "uart":
    import busio

    uart = busio.UART(board.TX, board.RX, baudrate=31250, timeout=0.001)
    midi = adafruit_midi.MIDI(midi_out=uart, out_channel=MIDI_CHANNEL - 1)
else:
    import usb_midi

    midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=MIDI_CHANNEL - 1)

dac = None
if CV_GATE_ENABLED:
    try:
        dac = GP8413(i2c_bus, address=DAC_I2C_ADDRESS)
    except (ValueError, OSError):
        # adafruit_bus_device's I2CDevice raises ValueError (not OSError)
        # when nothing ACKs at that address -- catch both so a DAC that
        # isn't wired up (yet) doesn't take the whole controller down.
        print("GP8413 CV/Gate DAC not found at", hex(DAC_I2C_ADDRESS), "-- continuing without it")
        dac = None

# held_order tracks (x, y) pads in press order, across both playing modes,
# purely for the monophonic CV/Gate output -- MIDI polyphony is unaffected.
held_order = []

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


def note_to_cv_volts(note):
    volts = (note - CV_REFERENCE_NOTE) / 12.0
    return max(0.0, min(CV_MAX_VOLTS, volts))


def update_cv_gate():
    global dac
    if not (CV_GATE_ENABLED and dac):
        return
    try:
        if held_order:
            top_notes = active_notes.get(held_order[-1])
            if top_notes:
                dac.set_channel0(note_to_cv_volts(top_notes[0]))
            dac.set_channel1(GATE_HIGH_VOLTS)
        else:
            # Gate drops, but pitch CV is deliberately left at its last
            # value (standard CV/sequencer behaviour) rather than
            # snapping to 0V.
            dac.set_channel1(0.0)
    except OSError:
        # A runtime I2C hiccup (bus contention, marginal power, a jostled
        # wire) must never take the whole controller down over an optional
        # peripheral -- drop the DAC for the rest of this session, same as
        # if it had never been found at startup.
        print("GP8413 CV/Gate write failed -- disabling CV/Gate for this session")
        dac = None


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
    if y == 1:
        # Brightness steps up with the selected sustain level so you can
        # see how much is dialed in at a glance; level 0 looks like any
        # other idle control pad.
        frac = CTRL_DIM if sustain_level_index == 0 else 0.4 + 0.15 * sustain_level_index
        trellis.color(CTRL_COL, y, tuple(int(c * frac) for c in color))
        return
    active = y == 3 and CHORD_MODE
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
    for note in range(128):
        midi.send(NoteOff(note, 0))
    active_notes.clear()
    pending_release.clear()
    held_order.clear()
    update_cv_gate()


# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------


def play_callback(x, y, edge):
    if edge == NeoTrellis.EDGE_RISING:
        # If this pad is still ringing out from a previous release, cut
        # that off now rather than letting it stack with the new notes.
        old_notes, _ = pending_release.pop((x, y), (None, None))
        if old_notes:
            midi.send([NoteOff(n, 0) for n in old_notes])

        notes = chord_notes_for_pad(x, y) if CHORD_MODE else [note_for_pad(x, y)]
        active_notes[(x, y)] = notes
        midi.send([NoteOn(n, NOTE_VELOCITY) for n in notes])
        draw_play_pad(x, y, pressed=True)
        if (x, y) not in held_order:
            held_order.append((x, y))
        update_cv_gate()
    elif edge == NeoTrellis.EDGE_FALLING:
        notes = active_notes.pop((x, y), [])
        if (x, y) in held_order:
            held_order.remove((x, y))
        update_cv_gate()
        if not notes:
            return
        hold = SUSTAIN_LEVELS[sustain_level_index]
        if hold <= 0:
            midi.send([NoteOff(n, 0) for n in notes])
        else:
            pending_release[(x, y)] = (notes, time.monotonic() + hold)
        draw_play_pad(x, y, pressed=False)


def ctrl_callback(x, y, edge):
    global OCTAVE_OFFSET, ROOT_NOTE, CHORD_MODE, sustain_level_index
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
        sustain_level_index = (sustain_level_index + 1) % len(SUSTAIN_LEVELS)
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


def flush_pending_releases():
    now = time.monotonic()
    done = [key for key, (_, deadline) in pending_release.items() if now >= deadline]
    for key in done:
        notes, _ = pending_release.pop(key)
        midi.send([NoteOff(n, 0) for n in notes])


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
    flush_pending_releases()
    time.sleep(0.02)
