# Neotrellis-Isomorphic-Chord-Keyboard
A CircuitPython script for an isomorphic chord keyboard for the Adafruit Neotrellis 8x8.

This is an isomorphic chord keyboard for the Adafruit Neotrellis 8x8 grid controller.  It

The first seven columns form the notes and playing surface, and the last column is the control strip.  
The layout is one semitone per column, and one perfect fourth per row, similar to a guitar.  It also
features a chord mode.  

Control strip:
#   row 7  octave up          row 3  toggle NOTE/CHORD mode
#   row 6  octave down        row 2  cycle scale (NOTE) / chord quality (CHORD)
#   row 5  transpose up       row 1  sustain toggle (MIDI CC64)
#   row 4  transpose down     row 0  panic (all notes off)

The Chord mode will cycle through scale and mode, and the chord forms (maj/min/dim/aug/sus2/sus4/7/maj7/m7), 
and you can optionally select different layouts (Wicki-Hayden, thirds) in the file.
