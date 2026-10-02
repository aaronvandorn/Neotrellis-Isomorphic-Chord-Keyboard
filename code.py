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
#     Feather "3V" pin (3.3V, ALWAYS present -- it's the onboard
#     regulator's output, so it's the same steady rail whether the board
#     is USB-powered or running on battery. Use this, not the "USB" pin,
#     if the controller will ever be run off battery: the "USB" pin is
#     literally the USB connector's VBUS passed through, so it has NO
#     voltage at all when no USB cable is delivering power -- a circuit
#     built on it goes completely dead the moment you unplug USB, even
#     with the battery installed and the board otherwise running fine.
#     The 3V-pin circuit below works identically in both power modes, so
#     there's no need for two different circuits or any switching.)
#         --[150ohm resistor]--> TRS RING
#     Feather "TX" pin
#         --[150ohm resistor]--> TRS TIP
#     Feather "GND"
#         -------------------->  TRS SLEEVE
#   That's it -- no optoisolator needed on the output side. Use a normal
#   3.5mm TRS-A to TRS-A (or TRS-A to 5-pin-DIN) cable from that jack into
#   the S-1's MIDI IN. (150ohm at 3.3V lands loop current around 7mA,
#   in the same working range as the classic 220ohm/5V design -- every
#   standard opto-isolated MIDI input, including the S-1's, reads it fine.
#   If you know the board will ALWAYS be USB-powered and want a bit more
#   margin, 220ohm resistors off the "USB" pin (5V) instead is the other
#   standard option -- just not compatible with ever running on battery.)
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
#   pad) when the arpeggiator is off, or the arpeggiator's current step
#   when it's on. Gate is high whenever any note should be sounding. If
#   your board doesn't ACK at 0x59, check its silkscreen for an
#   address-select jumper and update DAC_I2C_ADDRESS below. Missing/
#   unwired DAC is handled gracefully -- the grid and MIDI still work
#   fine, just without CV/Gate.
#
# STATUS DISPLAY (optional, DISPLAY_ENABLED below):
#   Adds a small status screen using the Adafruit FeatherWing OLED - 128x64
#   (SH1107, adafruit.com/product/4650) showing the current playing mode
#   (NOTE/CHORD), key, chord form/scale, octave, arpeggiator state, and
#   (while the menu is open) the full settings menu. It's on the SAME I2C
#   bus as everything else -- I2C address 0x3C by default.
#     IMPORTANT: this FeatherWing is designed to stack directly on the
#     Feather's header pins, but that header is already buried between the
#     two NeoTrellis boards in this build's enclosure, so there's no room
#     to stack it there. Wire it in remotely instead, using its STEMMA QT
#     / Qwiic JST-SH connector onto the same I2C bus as the NeoTrellis
#     boards, the DAC, and the rotary encoder (a STEMMA QT cable, or 4
#     hand-soldered wires to SDA/SCL/3V/GND). That gets you the screen but
#     NOT its onboard A/B/C buttons -- those are wired straight to the
#     Feather's D9/D6/D5 header pins on the FeatherWing PCB, which the
#     STEMMA QT cable doesn't carry at all, so they're simply unused here.
#     All menu/setting input now comes from the rotary encoder described
#     below instead.
#   Missing/unwired display is handled gracefully, same as the DAC -- the
#   grid, MIDI, and CV/Gate all still work fine without it (you just won't
#   be able to see the menu while changing settings).
#
# ENCODER CONTROL (optional, ENCODER_ENABLED below):
#   Every pad on the 8x8 grid plays notes/chords -- there is no dedicated
#   control strip anymore. Instead, an Adafruit I2C QT Rotary Encoder
#   Breakout with NeoPixel (adafruit.com/product/4991, seesaw-based) on
#   the shared I2C bus (STEMMA QT, address 0x36 by default) handles every
#   setting:
#     A SHORT PRESS of the encoder's built-in pushbutton, while PLAYING,
#       cycles which parameter turning the knob live-adjusts: Octave ->
#       Key -> Note/Chord -> Scale -> Arpeggio (on/off) -> back to Octave.
#       The footer of the status screen always shows the currently
#       selected target.
#     Turning the knob while PLAYING adjusts whichever of those five is
#       currently selected. The "Scale" slot is context-sensitive: in NOTE
#       mode it cycles the scale (major/minor/dorian/...), but in CHORD
#       mode there's no scale to speak of, so it cycles the chord quality
#       (maj/min/dim/...) instead -- the footer relabels itself "Chord" to
#       match whichever one it's actually doing.
#     A LONG PRESS (held over MENU_HOLD_SECONDS, ~1s) opens the on-screen
#       MENU with the remaining, less-frequently-changed parameters:
#       Chord (quality) / Sustain / ArpPattern / ArpRate / Effects / Exit
#       menu. Rotate to move between menu items; click again to start
#       EDITING the selected item, rotate to change its value, click once
#       more to confirm and return to the menu list. Selecting "Exit
#       menu" and clicking returns straight to normal play.
#     A VERY LONG PRESS (held over PANIC_HOLD_SECONDS, ~2s), from ANY
#       screen, is a panic shortcut -- it immediately silences every note
#       (MIDI, CV/Gate, and the arpeggiator) and returns to play mode.
#   The breakout's onboard NeoPixel gives a quick at-a-glance mode cue
#   (dim blue = playing, white = menu list, green = editing a value) if
#   it's present; this is optional and skipped gracefully if not.
#   FALLBACK: the encoder + menu need BOTH the encoder AND the display to
#   be usable. If either one isn't detected on the I2C bus at boot, the
#   firmware automatically reverts to the ORIGINAL control-strip layout
#   instead -- 7 playing columns (x = 0..6) plus a control strip on column
#   7 (octave up/down, key up/down, NOTE/CHORD toggle, cycle scale/chord
#   quality, cycle sustain, panic), exactly like the very first version of
#   this firmware. The OLED (if it happens to be present anyway) still
#   shows status in that mode, just without the menu. The arpeggiator and
#   "Effects" CC send are menu-only features, so they're simply unavailable
#   in the fallback layout. This means the encoder/display upgrade is
#   entirely optional and safe to leave unwired -- you always get a fully
#   working controller either way.
#
# ARPEGGIATOR (configured from the encoder menu -- "Arp"/"ArpPattern"/
#   "ArpRate"):
#   When on, held (and still-sustaining) notes across every pressed pad
#   are pooled together and stepped through one at a time -- Up, Down,
#   UpDown, or Random -- at a selectable rate, instead of all sounding at
#   once. This applies to MIDI, and to CV/Gate (which is monophonic
#   anyway). It plays nicely with CHORD mode too: every note of every
#   held chord goes into the same pool.
#
# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------
# 1. Copy this file to the CIRCUITPY drive as code.py.
# 2. From the Adafruit CircuitPython Library Bundle (matching your
#    CircuitPython version), copy these into /lib on CIRCUITPY:
#       adafruit_neotrellis/   (neotrellis.py, multitrellis.py, __init__.py)
#       adafruit_seesaw/       (dependency of adafruit_neotrellis; copy the
#                                WHOLE folder -- it also supplies the
#                                rotaryio/digitalio/neopixel submodules the
#                                rotary encoder driver below needs)
#       adafruit_bus_device/   (dependency of adafruit_seesaw)
#       adafruit_pixelbuf.mpy  (dependency of adafruit_seesaw -- built into
#                                many M4 CircuitPython builds already; only
#                                copy it if boot raises ImportError)
#       adafruit_midi/         (adafruit_midi.py + note_on.py, note_off.py,
#                                control_change.py, ...)
#    CV/Gate needs no extra library -- adafruit_bus_device is already
#    required above (it's a dependency of adafruit_seesaw), and the small
#    GP8413 driver below is included right in this file.
#    The status display needs (only if DISPLAY_ENABLED, see below):
#       adafruit_displayio_sh1107.mpy
#       adafruit_display_text/  (bitmap_label.py + dependencies)
#    displayio, terminalio, and i2cdisplaybus are built into CircuitPython
#    itself -- nothing to copy for those.
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
# 6. Optional: wire the OLED FeatherWing onto the shared I2C bus via its
#    STEMMA QT connector per the STATUS DISPLAY notes above; leave
#    DISPLAY_ENABLED = False below until it's wired if you're bringing
#    this up in stages.
# 7. Optional: wire the rotary encoder breakout onto the shared I2C bus via
#    its STEMMA QT connector per the ENCODER CONTROL notes above; leave
#    ENCODER_ENABLED = False below until it's wired if you're bringing
#    this up in stages. Without it, settings stay fixed at whatever the
#    CONFIGURATION constants below say.
#
# ---------------------------------------------------------------------------
# WHAT IT DOES
# ---------------------------------------------------------------------------
# The entire 8x8 grid (x = 0..7, y = 0..7) is the isomorphic playing
# surface: every pad's pitch is a fixed function of its grid position, so
# any chord or scale "shape" you learn can be played starting from any pad
# and it always sounds like the same shape, transposed.
#
# Two playing modes (chosen from the encoder menu, "Mode"):
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
# mode only) and a pressed pad flashes white. If the optional OLED status
# display (see STATUS DISPLAY above) is wired up, it shows the current
# mode, key, chord form/scale, octave, and arpeggiator state at a glance,
# plus the full settings menu when it's open.
#
# All settings -- octave, key, NOTE/CHORD mode, scale, chord quality,
# sustain length, the arpeggiator, and a MIDI CC "effects" send -- are
# controlled by the rotary encoder + OLED menu; see ENCODER CONTROL above.
#
# Sustain is a LOCAL, timed note-off delay (not a MIDI sustain-pedal CC64
# message) -- stepping the "Sustain" menu item picks the next hold length,
# so notes always let go on their own after a bounded, predictable time
# instead of ringing until you remember to release a pedal.
#
# ---------------------------------------------------------------------------

import random
import time

import board

import adafruit_midi
from adafruit_midi.control_change import ControlChange
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
OCTAVE_OFFSET = 0  # in octaves, adjustable live from the encoder
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

# (name, intervals-from-root) -- cycled from the encoder menu ("Chord") in
# CHORD mode
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

# Extra ring-on time (seconds) added after a pad is released, cycled from
# the encoder menu ("Sustain"). Index 0 is "off" -- notes stop the instant
# you let go, same as if this feature didn't exist.
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

# PLAY_COLS and CTRL_COL are NOT set here -- they're determined automatically
# further down (see "PLAYING SURFACE MODE" in HARDWARE SETUP), once we know
# whether the rotary encoder + OLED display actually showed up on the I2C
# bus. With both present, all 8 columns play and the encoder+menu handles
# settings. With either missing, the firmware falls back to the original
# 7-play-columns + control-strip-on-column-7 layout instead.

# CV/Gate output via an optional Makerfabs Mabee_DAC_GP8413 on the shared
# I2C bus -- see the CV/GATE OUTPUT notes at the top of this file.
CV_GATE_ENABLED = True
DAC_I2C_ADDRESS = 0x59
CV_REFERENCE_NOTE = 0  # MIDI note that maps to 0V -- kept at 0 so CV can
#                         never need to go negative (the DAC is 0-10V only)
CV_MAX_VOLTS = 10.0
GATE_HIGH_VOLTS = 5.0  # conservative default; raise toward 10V if your
#                         gate input wants a hotter signal

# Status display via an optional Adafruit FeatherWing OLED - 128x64
# (SH1107) on the shared I2C bus -- see the STATUS DISPLAY notes at the
# top of this file.
DISPLAY_ENABLED = True
DISPLAY_I2C_ADDRESS = 0x3C  # 0x3D if the FeatherWing's ADDR jumper is set

# Rotary encoder + menu control via an optional Adafruit I2C QT Rotary
# Encoder Breakout with NeoPixel (adafruit.com/product/4991) on the shared
# I2C bus -- see the ENCODER CONTROL notes at the top of this file.
ENCODER_ENABLED = True
ENCODER_I2C_ADDRESS = 0x36
MENU_HOLD_SECONDS = 1.0   # hold the encoder's button this long, from play
#                            mode, to open the on-screen menu
PANIC_HOLD_SECONDS = 2.0  # hold the encoder's button this long, from any
#                            screen, to panic (all notes off)

# What turning the encoder changes while you're PLAYING (not in the menu).
# A short press of the encoder's button cycles through these, in order.
ENCODER_ASSIGN_OPTIONS = ("octave", "key", "mode", "scale", "arpeggio")
ENCODER_ASSIGN_LABELS = {
    "octave": "Octave",
    "key": "Key",
    "mode": "Note/Chord",
    "scale": "Scale",
    "arpeggio": "Arpeggio",
}
encoder_assign_index = 0  # default: turning the knob while playing changes octave

# Arpeggiator -- pools the currently-held (and still-sustaining) notes
# across every pressed pad and steps through them instead of sounding them
# all at once. Toggle and configure from the menu ("Arp"/"ArpPattern"/
# "ArpRate").
ARP_PATTERNS = ("Up", "Down", "UpDown", "Random")
ARP_RATES_MS = (300, 220, 160, 110, 70)
ARP_RATE_LABELS = ("Slow", "Med", "Fast", "Faster", "V.Fast")

# "Effects" menu item -- sends a MIDI CC message (default CC1 / mod wheel)
# in steps, for whatever effect your synth has that CC mapped to.
EFFECTS_CC_NUMBER = 1
EFFECTS_STEP = 8

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

# Control-strip base colours and a short label, by row (y) -- only used in
# the fallback layout, when the encoder + display aren't both detected
# (see "PLAYING SURFACE MODE" in HARDWARE SETUP below).
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
# ctrl_flash[y] = time.monotonic() deadline until which that control pad
# stays lit white after a press (fallback layout only)
ctrl_flash = {}

CHORD_MODE = False

# active_notes[(x, y)] = list of MIDI note numbers currently sounding on that pad
active_notes = {}
# pending_release[(x, y)] = (list of notes, time.monotonic() deadline) for
# pads that were released while a sustain level > 0 was selected -- their
# NoteOff is delayed until the deadline instead of sent immediately. These
# notes also stay in the arpeggiator's pool until they expire.
pending_release = {}

# --- Menu / encoder runtime state ---
APP_MODE = "play"  # "play", "menu_nav", "menu_edit"
menu_index = 0

ARP_ON = False
arp_pattern_index = 0
arp_rate_index = 2
effects_value = 0

_arp_last_note = None
_arp_step_index = -1
_arp_last_time = 0.0

encoder_last_pos = 0
button_was_pressed = False
button_press_time = 0.0
menu_hold_fired = False
panic_hold_fired = False

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

# Status display (SH1107 OLED FeatherWing). Same tolerant pattern as the
# DAC above: if it's disabled, not wired up yet, or the libraries aren't
# on CIRCUITPY, the controller carries on without it instead of crashing.
display = None
_display_mode_label = None
_display_key_label = None
_display_detail_label = None
_display_footer_label = None
if DISPLAY_ENABLED:
    try:
        import displayio
        import i2cdisplaybus
        import terminalio
        from adafruit_displayio_sh1107 import SH1107
        from adafruit_display_text import bitmap_label

        displayio.release_displays()
        _display_bus = i2cdisplaybus.I2CDisplayBus(i2c_bus, device_address=DISPLAY_I2C_ADDRESS)
        display = SH1107(_display_bus, width=128, height=64, rotation=0)

        _splash = displayio.Group()
        _display_mode_label = bitmap_label.Label(terminalio.FONT, text="NOTE", scale=2, x=2, y=9)
        _display_key_label = bitmap_label.Label(terminalio.FONT, text="", scale=1, x=2, y=27)
        _display_detail_label = bitmap_label.Label(terminalio.FONT, text="", scale=1, x=2, y=40)
        _display_footer_label = bitmap_label.Label(terminalio.FONT, text="", scale=1, x=2, y=53)
        for _lbl in (_display_mode_label, _display_key_label, _display_detail_label, _display_footer_label):
            _splash.append(_lbl)
        display.root_group = _splash
    except (ImportError, ValueError, OSError, RuntimeError, AttributeError) as e:
        print("OLED FeatherWing display not found/usable at", hex(DISPLAY_I2C_ADDRESS), "-- continuing without it:", e)
        display = None

# Rotary encoder + button + (optional) NeoPixel, via adafruit_seesaw. Same
# tolerant pattern as the DAC and display above.
encoder = None
button = None
ss_pixel = None
if ENCODER_ENABLED:
    try:
        from adafruit_seesaw import digitalio as _seesaw_digitalio
        from adafruit_seesaw import rotaryio as _seesaw_rotaryio
        from adafruit_seesaw import seesaw as _seesaw_mod

        _ss = _seesaw_mod.Seesaw(i2c_bus, addr=ENCODER_I2C_ADDRESS)
        encoder = _seesaw_rotaryio.IncrementalEncoder(_ss)
        _ss.pin_mode(24, _ss.INPUT_PULLUP)
        button = _seesaw_digitalio.DigitalIO(_ss, 24)
        encoder_last_pos = encoder.position

        # NeoPixel mode indicator is a nice-to-have -- keep its failure
        # from taking down the encoder itself if the seesaw firmware on
        # hand doesn't expose it for some reason.
        try:
            from adafruit_seesaw import neopixel as _seesaw_neopixel

            ss_pixel = _seesaw_neopixel.NeoPixel(_ss, 6, 1)
            ss_pixel.brightness = 0.3
        except (ImportError, ValueError, OSError, RuntimeError, AttributeError):
            ss_pixel = None
    except (ImportError, ValueError, OSError, RuntimeError, AttributeError) as e:
        print("Rotary encoder not found/usable at", hex(ENCODER_I2C_ADDRESS), "-- continuing without it:", e)
        encoder = None
        button = None
        ss_pixel = None

# ---------------------------------------------------------------------------
# PLAYING SURFACE MODE
# ---------------------------------------------------------------------------
# The encoder + OLED menu needs BOTH the rotary encoder (with its
# pushbutton) AND the display to be usable -- without the display you can't
# see the menu, and without the encoder there's no way to drive it. If
# either one didn't show up on the I2C bus, fall back to exactly the
# original control-strip behaviour instead: 7 playing columns (x = 0..6)
# plus a control strip on column 7 for octave/key/mode/scale-quality/
# sustain/panic, with the OLED (if it happens to be present anyway) simply
# showing status the way it always did. The arpeggiator and "Effects" CC,
# which only exist as menu items, are unreachable in this mode -- ARP_ON
# simply never gets set, so play_callback()/flush_pending_releases() behave
# exactly as they did before the encoder/menu existed.
NEW_UI_ACTIVE = encoder is not None and button is not None and display is not None

if NEW_UI_ACTIVE:
    PLAY_COLS = range(0, 8)
    CTRL_COL = None
else:
    PLAY_COLS = range(0, 7)
    CTRL_COL = 7
    if ENCODER_ENABLED:
        print("Encoder + display not both detected -- reverting to the classic control-strip layout")

# held_order tracks (x, y) pads in press order, across both playing modes,
# purely for the monophonic CV/Gate output -- MIDI polyphony is unaffected.
held_order = []

# ---------------------------------------------------------------------------
# MUSIC HELPERS
# ---------------------------------------------------------------------------


_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_name(note):
    """MIDI note number -> name like 'C2' (standard MIDI octave numbering,
    where note 60 = C4 -- matches how ROOT_NOTE = 36 above is called 'C2')."""
    return "{}{}".format(_NOTE_NAMES[note % 12], (note // 12) - 1)


def key_pitch_name():
    return _NOTE_NAMES[ROOT_NOTE % 12]


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
    """Last-note-priority CV/Gate output. Only used when the arpeggiator
    is OFF -- while it's on, flush_arp() drives CV/Gate directly instead
    (see ARPEGGIATOR below)."""
    global dac
    if not (CV_GATE_ENABLED and dac) or ARP_ON:
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


def set_cv_gate_direct(note, gate_on):
    """Used by the arpeggiator to drive CV/Gate for its current step,
    bypassing the last-note-priority logic in update_cv_gate()."""
    global dac
    if not (CV_GATE_ENABLED and dac):
        return
    try:
        if note is not None:
            dac.set_channel0(note_to_cv_volts(note))
        dac.set_channel1(GATE_HIGH_VOLTS if gate_on else 0.0)
    except OSError:
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
    """Classic control-strip pad (fallback layout only, CTRL_COL is not
    None)."""
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


def set_encoder_led():
    if ss_pixel is None:
        return
    try:
        if APP_MODE == "play":
            ss_pixel[0] = (0, 0, 40)
        elif APP_MODE == "menu_nav":
            ss_pixel[0] = (40, 40, 40)
        else:
            ss_pixel[0] = (0, 40, 0)
    except OSError:
        pass


def update_display():
    """Refresh the optional OLED status/menu screen. Cheap to call
    whenever mode/key/scale/chord/octave/sustain/arp/menu-position
    changes -- it just rewrites text labels already on screen, no I2C
    traffic if there's no display."""
    if display is None:
        return
    if APP_MODE == "play":
        _display_mode_label.text = "CHORD" if CHORD_MODE else "NOTE"
        _display_key_label.text = "Key:{} Oct:{:+d}".format(key_pitch_name(), OCTAVE_OFFSET)
        if CHORD_MODE:
            _display_detail_label.text = "Chord:" + CHORD_QUALITIES[chord_quality_index][0]
        else:
            _display_detail_label.text = "Scale:" + SCALE_NAMES[scale_index]
        if NEW_UI_ACTIVE:
            arp_txt = "Arp:" + ("On" if ARP_ON else "Off")
            target = ENCODER_ASSIGN_OPTIONS[encoder_assign_index]
            # "scale" actually drives chord quality while in CHORD mode
            # (see adjust_scale()) -- reflect that in the label too, so
            # the footer always names what turning the knob will do.
            if target == "scale" and CHORD_MODE:
                assign_label = "Chord"
            else:
                assign_label = ENCODER_ASSIGN_LABELS[target]
            assign_txt = "Turn:" + assign_label
            _display_footer_label.text = "{} {}".format(arp_txt, assign_txt)
        else:
            # Classic control-strip layout -- no encoder to reassign and
            # no menu, so just show the sustain length like the original
            # firmware did.
            _display_footer_label.text = "Sustain:" + _sustain_label()
    elif APP_MODE == "menu_nav":
        item = MENU_ITEMS[menu_index]
        prev_item = MENU_ITEMS[(menu_index - 1) % len(MENU_ITEMS)]
        next_item = MENU_ITEMS[(menu_index + 1) % len(MENU_ITEMS)]
        _display_mode_label.text = "MENU"
        _display_key_label.text = "  " + prev_item["name"]
        _display_detail_label.text = "> " + item["name"] + ": " + str(item["value"]())
        _display_footer_label.text = "  " + next_item["name"]
    else:  # menu_edit
        item = MENU_ITEMS[menu_index]
        _display_mode_label.text = "EDIT"
        _display_key_label.text = item["name"]
        _display_detail_label.text = "< " + str(item["value"]()) + " >"
        _display_footer_label.text = "click = done"


# ---------------------------------------------------------------------------
# MIDI ACTIONS
# ---------------------------------------------------------------------------


def panic():
    global _arp_last_note, _arp_step_index
    for note in range(128):
        midi.send(NoteOff(note, 0))
    active_notes.clear()
    pending_release.clear()
    held_order.clear()
    _arp_last_note = None
    _arp_step_index = -1
    if dac is not None:
        try:
            dac.set_channel1(0.0)
        except OSError:
            pass
    update_cv_gate()
    draw_all_play_pads()


# ---------------------------------------------------------------------------
# ARPEGGIATOR
# ---------------------------------------------------------------------------


def arp_pool_notes():
    """Every note currently held down, plus every note still ringing out
    in its sustain tail, deduplicated and sorted -- what the arpeggiator
    steps through."""
    pool = []
    for notes in active_notes.values():
        pool.extend(notes)
    for notes, _ in pending_release.values():
        pool.extend(notes)
    return sorted(set(pool))


def _arp_note_on(note):
    midi.send(NoteOn(note, NOTE_VELOCITY))


def _arp_note_off(note):
    midi.send(NoteOff(note, 0))


def flush_arp():
    global _arp_last_note, _arp_step_index, _arp_last_time
    if not ARP_ON:
        return
    pool = arp_pool_notes()
    if not pool:
        if _arp_last_note is not None:
            _arp_note_off(_arp_last_note)
            _arp_last_note = None
            set_cv_gate_direct(None, False)
        return

    now = time.monotonic()
    interval = ARP_RATES_MS[arp_rate_index] / 1000.0
    if now - _arp_last_time < interval:
        return
    _arp_last_time = now

    pattern = ARP_PATTERNS[arp_pattern_index]
    if pattern == "Random":
        next_note = random.choice(pool)
    else:
        if pattern == "Down":
            seq = list(reversed(pool))
        elif pattern == "UpDown" and len(pool) > 2:
            seq = pool + list(reversed(pool[1:-1]))
        else:
            seq = pool
        _arp_step_index = (_arp_step_index + 1) % len(seq)
        next_note = seq[_arp_step_index]

    if _arp_last_note is not None:
        _arp_note_off(_arp_last_note)
    _arp_note_on(next_note)
    _arp_last_note = next_note
    set_cv_gate_direct(next_note, True)


# ---------------------------------------------------------------------------
# MENU SYSTEM
# ---------------------------------------------------------------------------


def adjust_encoder_assign(step):
    global encoder_assign_index
    encoder_assign_index = (encoder_assign_index + step) % len(ENCODER_ASSIGN_OPTIONS)


def adjust_key(step):
    global ROOT_NOTE
    base = (ROOT_NOTE // 12) * 12
    pc = (ROOT_NOTE % 12 + step) % 12
    ROOT_NOTE = base + pc


def adjust_octave(step):
    global OCTAVE_OFFSET
    OCTAVE_OFFSET = max(-OCTAVE_LIMIT, min(OCTAVE_LIMIT, OCTAVE_OFFSET + step))


def adjust_mode(step):
    global CHORD_MODE
    CHORD_MODE = not CHORD_MODE


def adjust_scale(step):
    # Scale only affects anything in NOTE mode (it picks which pads are
    # in-scale). In CHORD mode there's no scale to speak of, so the same
    # quick-turn slot instead cycles the chord quality -- whichever one
    # actually does something for the current mode.
    global scale_index
    if CHORD_MODE:
        adjust_chord_quality(step)
    else:
        scale_index = (scale_index + step) % len(SCALE_NAMES)


def adjust_chord_quality(step):
    global chord_quality_index
    chord_quality_index = (chord_quality_index + step) % len(CHORD_QUALITIES)


def adjust_sustain(step):
    global sustain_level_index
    sustain_level_index = max(0, min(len(SUSTAIN_LEVELS) - 1, sustain_level_index + step))


def adjust_arp_on(step):
    global ARP_ON, _arp_last_note, _arp_step_index
    ARP_ON = not ARP_ON
    if not ARP_ON and _arp_last_note is not None:
        _arp_note_off(_arp_last_note)
        _arp_last_note = None
        set_cv_gate_direct(None, False)
    _arp_step_index = -1


def adjust_arp_pattern(step):
    global arp_pattern_index
    arp_pattern_index = (arp_pattern_index + step) % len(ARP_PATTERNS)


def adjust_arp_rate(step):
    global arp_rate_index
    arp_rate_index = max(0, min(len(ARP_RATES_MS) - 1, arp_rate_index + step))


def adjust_effects(step):
    global effects_value
    effects_value = max(0, min(127, effects_value + step * EFFECTS_STEP))
    midi.send(ControlChange(EFFECTS_CC_NUMBER, effects_value))


def adjust_exit(step):
    pass


# Maps each ENCODER_ASSIGN_OPTIONS entry to the function that live-adjusts
# it while playing (selected by a short press of the encoder button, then
# controlled by turning it -- see handle_encoder_click() / ENCODER CONTROL
# notes at the top of this file).
ENCODER_ASSIGN_TARGETS = {
    "octave": adjust_octave,
    "key": adjust_key,
    "mode": adjust_mode,
    "scale": adjust_scale,
    "arpeggio": adjust_arp_on,
}


def _sustain_label():
    if sustain_level_index == 0:
        return "Off"
    return "{:.2f}s".format(SUSTAIN_LEVELS[sustain_level_index])


# The on-screen MENU (opened with a long press, ~1s) only holds the
# parameters that AREN'T already reachable via the quick short-press cycle
# above (Octave/Key/Note-Chord/Scale/Arpeggio) -- just the remaining,
# less-frequently-changed settings.
MENU_ITEMS = (
    {"name": "Chord", "value": lambda: CHORD_QUALITIES[chord_quality_index][0], "adjust": adjust_chord_quality},
    {"name": "Sustain", "value": _sustain_label, "adjust": adjust_sustain},
    {"name": "ArpPattern", "value": lambda: ARP_PATTERNS[arp_pattern_index], "adjust": adjust_arp_pattern},
    {"name": "ArpRate", "value": lambda: ARP_RATE_LABELS[arp_rate_index], "adjust": adjust_arp_rate},
    {"name": "Effects", "value": lambda: "CC{}:{}".format(EFFECTS_CC_NUMBER, effects_value), "adjust": adjust_effects},
    {"name": "Exit menu", "value": lambda: "click", "adjust": adjust_exit},
)

# ---------------------------------------------------------------------------
# ENCODER POLLING
# ---------------------------------------------------------------------------


def handle_encoder_rotate(delta):
    global menu_index
    step = 1 if delta > 0 else -1
    for _ in range(abs(delta)):
        if APP_MODE == "play":
            target = ENCODER_ASSIGN_OPTIONS[encoder_assign_index]
            ENCODER_ASSIGN_TARGETS[target](step)
        elif APP_MODE == "menu_nav":
            menu_index = (menu_index + step) % len(MENU_ITEMS)
        elif APP_MODE == "menu_edit":
            MENU_ITEMS[menu_index]["adjust"](step)
    if APP_MODE == "play":
        draw_all_play_pads()
    update_display()


def handle_encoder_click():
    """A SHORT press of the encoder button (released before
    MENU_HOLD_SECONDS)."""
    global APP_MODE, menu_index
    if APP_MODE == "play":
        # Cycle which parameter turning the knob live-adjusts: Octave ->
        # Key -> Note/Chord -> Scale -> Arpeggio -> back to Octave.
        adjust_encoder_assign(1)
    elif APP_MODE == "menu_nav":
        if MENU_ITEMS[menu_index]["name"] == "Exit menu":
            APP_MODE = "play"
        else:
            APP_MODE = "menu_edit"
    elif APP_MODE == "menu_edit":
        APP_MODE = "menu_nav"
    if APP_MODE == "play":
        draw_all_play_pads()
    set_encoder_led()
    update_display()


def handle_menu_hold():
    """A LONG press of the encoder button (held past MENU_HOLD_SECONDS) --
    opens the on-screen menu of the "other" parameters."""
    global APP_MODE, menu_index
    APP_MODE = "menu_nav"
    menu_index = 0
    set_encoder_led()
    update_display()


def handle_panic_hold():
    """A VERY long press of the encoder button (held past
    PANIC_HOLD_SECONDS) -- panic, from any screen."""
    global APP_MODE
    panic()
    APP_MODE = "play"
    draw_all_play_pads()
    set_encoder_led()
    update_display()


def poll_encoder():
    global encoder_last_pos, button_was_pressed, button_press_time
    global menu_hold_fired, panic_hold_fired
    if not NEW_UI_ACTIVE:
        # Fallback layout is active (encoder + display weren't both
        # detected) -- the encoder, if physically present at all, is left
        # completely inert so behaviour matches the original control-strip
        # firmware exactly.
        return
    if encoder is not None:
        pos = encoder.position
        delta = pos - encoder_last_pos
        if delta != 0:
            encoder_last_pos = pos
            handle_encoder_rotate(delta)

    if button is None:
        return

    pressed = not button.value
    now = time.monotonic()
    if pressed and not button_was_pressed:
        button_was_pressed = True
        button_press_time = now
        menu_hold_fired = False
        panic_hold_fired = False
    elif pressed and button_was_pressed:
        held = now - button_press_time
        if not panic_hold_fired and held >= PANIC_HOLD_SECONDS:
            panic_hold_fired = True
            handle_panic_hold()
        elif not menu_hold_fired and held >= MENU_HOLD_SECONDS:
            menu_hold_fired = True
            handle_menu_hold()
    elif not pressed and button_was_pressed:
        button_was_pressed = False
        if not menu_hold_fired and not panic_hold_fired:
            handle_encoder_click()


# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------


def play_callback(x, y, edge):
    if edge == NeoTrellis.EDGE_RISING:
        # If this pad is still ringing out from a previous release, cut
        # that off now rather than letting it stack with the new notes.
        old_notes, _ = pending_release.pop((x, y), (None, None))
        if old_notes and not ARP_ON:
            midi.send([NoteOff(n, 0) for n in old_notes])

        notes = chord_notes_for_pad(x, y) if CHORD_MODE else [note_for_pad(x, y)]
        active_notes[(x, y)] = notes
        if not ARP_ON:
            midi.send([NoteOn(n, NOTE_VELOCITY) for n in notes])
        draw_play_pad(x, y, pressed=True)
        if (x, y) not in held_order:
            held_order.append((x, y))
        if not ARP_ON:
            update_cv_gate()
    elif edge == NeoTrellis.EDGE_FALLING:
        notes = active_notes.pop((x, y), [])
        if (x, y) in held_order:
            held_order.remove((x, y))
        if not ARP_ON:
            update_cv_gate()
        if not notes:
            draw_play_pad(x, y, pressed=False)
            return
        hold = SUSTAIN_LEVELS[sustain_level_index]
        if hold <= 0:
            if not ARP_ON:
                midi.send([NoteOff(n, 0) for n in notes])
        else:
            pending_release[(x, y)] = (notes, time.monotonic() + hold)
        draw_play_pad(x, y, pressed=False)


def ctrl_callback(x, y, edge):
    """Classic control strip (fallback layout only, registered on CTRL_COL
    when the encoder + display aren't both detected -- see "PLAYING
    SURFACE MODE" above). Identical to the original pre-encoder firmware's
    control strip."""
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
    update_display()


def flush_ctrl_flash():
    now = time.monotonic()
    for y in [y for y, deadline in ctrl_flash.items() if now >= deadline]:
        del ctrl_flash[y]
        draw_ctrl_pad(y)


def flush_pending_releases():
    now = time.monotonic()
    done = [key for key, (_, deadline) in pending_release.items() if now >= deadline]
    if not done:
        return
    for key in done:
        notes, _ = pending_release.pop(key)
        if not ARP_ON:
            midi.send([NoteOff(n, 0) for n in notes])
    if not ARP_ON:
        update_cv_gate()


# ---------------------------------------------------------------------------
# STARTUP
# ---------------------------------------------------------------------------

for _y in range(8):
    for _x in PLAY_COLS:
        trellis.activate_key(_x, _y, NeoTrellis.EDGE_RISING)
        trellis.activate_key(_x, _y, NeoTrellis.EDGE_FALLING)
        trellis.set_callback(_x, _y, play_callback)
    if CTRL_COL is not None:
        trellis.activate_key(CTRL_COL, _y, NeoTrellis.EDGE_RISING)
        trellis.set_callback(CTRL_COL, _y, ctrl_callback)

if BOOT_ANIMATION:
    for _y in range(8):
        for _x in range(8):
            trellis.color(_x, _y, (40, 0, 60))
            time.sleep(0.01)

draw_all_play_pads()
if CTRL_COL is not None:
    draw_all_ctrl_pads()
set_encoder_led()
update_display()

# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

while True:
    # The NeoTrellis (seesaw) hardware can only be polled roughly every
    # 17ms or so.
    trellis.sync()
    poll_encoder()
    flush_ctrl_flash()
    flush_pending_releases()
    flush_arp()
    time.sleep(0.02)
