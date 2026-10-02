# Neotrellis-Isomorphic-Chord-Keyboard
A CircuitPython script for an isomorphic chord keyboard for the Adafruit Neotrellis 8x8.

This is an isomorphic chord keyboard for the Adafruit Neotrellis 8x8 grid controller.  It contains
the ability to add the Featherwing display module from Adafruit and rotary encoder, which allows you to select from 
Chord and Note modes.  In Chord mode, you can change the chord forms (maj/min/dim/aug/sus2/sus4/7/maj7/m7) on the fly 
by twisting the rotary encoder.  In Note mode, you can select the key and the mode the same way.  There's also an 
appegiator feature, and you can optionally select different layouts (Wicki-Hayden, thirds) in the code file.

This code has also includes instructions on how to add a TRS MIDI out based on a simple circuit, and how to 
add a DAC connection to output CV signals via the 12C connectors on the Neotrellis PCBs.

To install, place the code.py file into the root directory of the Neotrellis. 
