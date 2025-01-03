from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, layout
)

# Enharmonic mapping: name -> (newName, octaveAdjustment)
# B# in the same octave as B? Actually, B# is enharmonically C in the *next* octave
# so we do an octaveAdjustment of +1 for B# -> C.
# Similarly, Cb is enharmonically B in the *previous* octave, so -1 for that.
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", +1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}

def determine_clef_and_octave(instrument_name):
    """
    Return a recommended clef and default octave start based on the instrument.
    """
    instrument_map = {
        "Piano": ("TrebleClef", 4),
        "Violin": ("TrebleClef", 3),
        "Cello": ("BassClef", 2),
        "Flute": ("TrebleClef", 4),
        "Clarinet": ("TrebleClef", 3),
        "Trumpet": ("TrebleClef", 4),
        "Trombone": ("BassClef", 2),
        "Guitar": ("TrebleClef", 3)
    }
    return instrument_map.get(instrument_name, ("TrebleClef", 4))

def fix_enharmonic_spelling(n):
    """
    For any note spelled as E#, B#, Cb, or Fb, rename it to a simpler equivalent
    (F, C, B, or E). Adjust the octave if needed.
    E.g. B#4 -> C5, Cb5 -> B4, etc.
    Also force accidental display so we see naturals if applicable.
    """
    if not n.pitch:
        return
    original_name = n.pitch.name  # e.g. "E#", "B#", ...
    if original_name in ENHARM_MAP:
        new_name, octave_adjust = ENHARM_MAP[original_name]
        # Update the pitch name
        n.pitch.name = new_name
        # Update the octave if needed
        n.pitch.octave += octave_adjust
        # Force accidental display (for naturals, etc.)
        if n.pitch.accidental:
            n.pitch.accidental.displayStatus = True

def create_scale_measure(title_text, scale_object, octave_start, num_octaves):
    """
    Create a single Measure containing:
      - A text title (above staff)
      - The scale (up then down) in one measure
      - Automatic rewriting of E# -> F, B# -> C, etc.
    """
    m = stream.Measure()

    # Place a text label at the top of the measure
    txt = expressions.TextExpression(title_text)
    txt.placement = 'above'
    m.insert(0, txt)

    # Create the up-then-down pattern
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))  # avoid repeating top note

    # Convert pitches to notes, fix enharmonics, add to measure
    for p in (pitches_up + pitches_down):
        n = note.Note(p)
        # Show accidentals (like sharps, flats, naturals)
        if n.pitch.accidental:
            n.pitch.accidental.displayStatus = True
        # Fix E#, B#, etc.
        fix_enharmonic_spelling(n)
        m.append(n)

    return m

def generate_and_save_scales_to_pdf(key_signature, num_octaves, instrument_name):
    """
    Creates a single staff with two measures:
     1) The Major scale of key_signature (title above)
     2) System break
     3) The relative minor scale (same key signature, different tonic)
    Writes the result to a PDF via MuseScore.
    """
    # 1) Set up MuseScore environment
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    # 2) Determine clef & octave
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)

    # 3) Create a single-staff Part
    part = stream.Part()
    instr = getattr(instrument, instrument_name)()
    instr.staffCount = 1  # Force a single staff (no braces for Piano)
    part.insert(0, instr)

    # Add the chosen clef
    part.insert(0, getattr(clef, selected_clef)())

    # =============== MAJOR SCALE ===============
    major_key_obj = key.Key(key_signature, 'major')  # e.g. F# major
    part.append(major_key_obj)

    major_scale_obj = scale.MajorScale(key_signature)
    major_measure = create_scale_measure(
        title_text=f"{key_signature} Major Scale",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    part.append(major_measure)

    # Force a line break so next measure is on a new system
    sys_break = layout.SystemLayout()
    sys_break.systemBreak = True
    part.append(sys_break)

    # =============== RELATIVE MINOR SCALE ===============
    # e.g. F# major -> D# minor
    relative_minor_obj = major_key_obj.getRelativeMinor()
    part.append(relative_minor_obj)  # add that key signature object

    minor_scale_obj = scale.MinorScale(relative_minor_obj.tonic.name)
    minor_measure = create_scale_measure(
        title_text=f"{relative_minor_obj.tonic.name} Minor Scale",
        scale_object=minor_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    part.append(minor_measure)

    # 4) Put Part in a Score
    score = stream.Score()
    score.insert(0, part)

    # 5) Write the Score to a PDF
    file_name = f"{key_signature}_{instrument_name}_major_relativeMinor_scales"
    output_path = f"/Users/az/Desktop/pythontestingforsheetscan2/output/{file_name}.pdf"
    score.write("musicxml.pdf", fp=output_path)

    print(f"PDF generated at: {output_path}")


# Example usage:
if __name__ == "__main__":
    # e.g. "F#" => measure #1: F# major => measure #2: D# minor, 
    # with E# automatically displayed as F natural, etc.
    generate_and_save_scales_to_pdf("F#", 2, "Piano")
