from music21 import stream, note, key, scale, clef, instrument, environment, expressions, layout

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

def create_scale_measure(title_text, scale_object, octave_start, num_octaves):
    """
    Create a single Measure with:
      - A text title (above)
      - The scale notes (up then down) in that single measure
    """
    m = stream.Measure()

    # Add a text label at the start of the measure
    txt = expressions.TextExpression(title_text)
    txt.placement = 'above'  # ensure it appears above staff
    m.insert(0, txt)

    # Build the scale notes
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    # Avoid repeating the top note on the way down
    pitches_down = list(reversed(pitches_up[:-1]))

    # Add them to the measure
    for p in (pitches_up + pitches_down):
        n = note.Note(p)
        # Force accidentals to display (e.g., sharps/flats)
        if n.pitch.accidental:
            n.pitch.accidental.displayStatus = True
        m.append(n)

    return m

def generate_and_save_scales_to_pdf(key_signature, num_octaves, instrument_name):
    """
    1) Creates a single-staff Part for the specified instrument (e.g. Piano).
    2) Measure #1: Major scale with the user key_signature
    3) System break
    4) Measure #2: Relative minor scale (same key signature)
    5) Writes to PDF via MuseScore, no XML returned.
    """
    # --- 1) Configure MuseScore path
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    # --- 2) Determine clef + octave
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)

    # Create a Part and force it to a single staff (especially for Piano)
    part = stream.Part()
    instr = getattr(instrument, instrument_name)()
    instr.staffCount = 1  # remove the braced grand staff if it's Piano
    part.insert(0, instr)

    # Insert the Clef at the beginning
    part.insert(0, getattr(clef, selected_clef)())

    # --- 3) Build the Major scale measure
    #     e.g. "F#" major => key object => scale => measure
    major_key_obj = key.Key(key_signature, 'major')
    major_scale_obj = scale.MajorScale(key_signature)

    # Add the Key Signature object for the major scale
    part.append(major_key_obj)

    # Create measure #1 (title + notes)
    major_scale_measure = create_scale_measure(
        title_text=f"{key_signature} Major Scale",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    part.append(major_scale_measure)

    # --- 4) Force a line break AFTER measure #1
    sys_break = layout.SystemLayout()
    sys_break.systemBreak = True
    part.append(sys_break)

    # --- 5) Build the RELATIVE minor scale measure
    # For "F#" major, the relative minor is "D#" minor (same key signature)
    relative_minor_obj = major_key_obj.getRelativeMinor()   # e.g. D# minor
    minor_scale_obj = scale.MinorScale(relative_minor_obj.tonic.name)

    # Add the Key Signature object for that minor
    part.append(relative_minor_obj)  # e.g. key.Key('D#', 'minor')

    # Create measure #2 (title + notes)
    minor_scale_measure = create_scale_measure(
        title_text=f"{relative_minor_obj.tonic.name} Minor Scale",
        scale_object=minor_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    part.append(minor_scale_measure)

    # --- 6) Put the Part into a Score and write to PDF
    score = stream.Score()
    score.insert(0, part)

    # The output filename
    file_name = f"{key_signature}_{instrument_name}_major_relativeMinor_scales"
    output_path = f"/Users/az/Desktop/pythontestingforsheetscan2/output/{file_name}.pdf"

    score.write('musicxml.pdf', fp=output_path)
    print(f"PDF written to: {output_path}")

# Example usage (uncomment to run):
if __name__ == "__main__":
    generate_and_save_scales_to_pdf("F#", 2, "Piano")
