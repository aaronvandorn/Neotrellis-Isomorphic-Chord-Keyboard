# Neotrellis-Isomorphic-Chord-Keyboard
A CircuitPython script for an isomorphic chord keyboard for the Adafruit Neotrellis 8x8.

This is an isomorphic chord keyboard for the Adafruit Neotrellis 8x8 grid controller.  It

The first seven columns form the notes and playing surface, and the last column is the control strip.  
The layout is one semitone per column, and one perfect fourth per row, similar to a guitar.  It also
features a chord mode.  

Control strip:
- Octave Up
- Octave Down
- Transpose Up
- Transpose Down
- Toggle between Note/Chord mode
- Cycle Scale (Note mode) and Chord quality (Chord mode)
- Sustain cycle (steps through multiple sustain lengths, which can be changed in the code)
- Panic (all notes off

The Chord mode will cycle through scale and mode, and the chord forms (maj/min/dim/aug/sus2/sus4/7/maj7/m7), 
and you can optionally select different layouts (Wicki-Hayden, thirds) in the file.

This code has also includes instructions on how to add a TRS MIDI out based on a simple circuit, and how to 
add a DAC connection to output CV signals via the 12C connectors on the Neotrellis PCBs.

To install, place the code.py file into the root directory of the Neotrellis. 
