import os
import shutil
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, duration
)

# ------------------------------------------------------------------------
# Enharmonic mapping: name -> (newName, octaveAdjustment)
# ------------------------------------------------------------------------
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", +1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}

# ------------------------------------------------------------------------
# Updated determine_clef_and_octave
# ------------------------------------------------------------------------
def determine_clef_and_octave(instrument_name, part='right'):
    """
    Return a recommended clef and default octave start based on the instrument.
    For piano, differentiate between right and left hands.

    NOTE: These ranges and clefs are approximate, serving only as
    a starting point. Real-world usage may need adjustments, particularly
    for transposing instruments or advanced ranges.
    """

    # If you need special logic for piano specifically:
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}[part]

    # If you need special logic for electric piano similarly:
    if instrument_name == "Electric Piano":
        return ("TrebleClef", 4)  # Simplified single staff

    # Basic attempts at a suitable clef & starting octave for each instrument.
    # Adjust as necessary for your needs.
    instrument_map = {
        # Strings
        "Violin":       ("TrebleClef", 3),
        "Viola":        ("AltoClef",   3),
        "Cello":        ("BassClef",   2),
        "Double Bass":  ("BassClef",   1),
        "Guitar":       ("TrebleClef", 3),
        "Harp":         ("TrebleClef", 3),  # Often written on grand staff, but we'll simplify

        # Woodwinds
        "Alto Saxophone":   ("TrebleClef", 3), 
        "Bass Clarinet":    ("TrebleClef", 2),  # Real pitch is deeper, but commonly notated in treble
        "Bassoon":          ("BassClef",   2),  
        "Clarinet":         ("TrebleClef", 3),
        "English Horn":     ("TrebleClef", 4),
        "Flute":            ("TrebleClef", 4),
        "Oboe":             ("TrebleClef", 4),
        "Piccolo":          ("TrebleClef", 5),  # Sounds an octave up, but we’ll keep it simple
        "Tenor Saxophone":  ("TrebleClef", 3),
        "Trumpet":          ("TrebleClef", 4),  # Also transposing, but we’ll keep it simple

        # Brass
        "Euphonium":    ("BassClef", 2),  # Commonly in bass clef
        "French Horn":  ("TrebleClef", 3),  
        "Trombone":     ("BassClef",   2),
        "Tuba":         ("BassClef",   1),

        # Percussion (pitched)
        "Marimba":      ("TrebleClef", 3), 
        "Timpani":      ("BassClef",   3),
        "Vibraphone":   ("TrebleClef", 3),
        "Xylophone":    ("TrebleClef", 4),

        # Keyboards
        "Organ":        ("TrebleClef", 4),

        # Voice
        # If you want a single default, pick something in the mid-range:
        "Voice":        ("TrebleClef", 4),
    }

    # For unpitched percussion or anything not in the map, we’ll default to
    # a "PercussionClef" or fallback Treble, or skip scale generation entirely.
    unpitched_percussion = {
        "Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine"
    }

    if instrument_name in unpitched_percussion:
        # You might skip scale generation for these or assign a generic clef:
        return ("PercussionClef", 4)

    # Return the mapping if found; otherwise default to TrebleClef, 4
    return instrument_map.get(instrument_name, ("TrebleClef", 4))

# ------------------------------------------------------------------------
# Fix Enharmonic Spelling
# ------------------------------------------------------------------------
def fix_enharmonic_spelling(n):
    """
    1) For notes spelled as E#, B#, Cb, or Fb, rename them to F, C, B, or E,
       adjusting octave if needed.
    2) If there's an accidental, force it to display.
    """
    if not n.pitch:
        return

    original_name = n.pitch.name
    if original_name in ENHARM_MAP:
        new_name, octave_adjust = ENHARM_MAP[original_name]
        n.pitch.name = new_name
        n.pitch.octave += octave_adjust

    if n.pitch.accidental is not None:
        n.pitch.accidental.displayStatus = True
        n.pitch.accidental.displayType = 'normal'

# ------------------------------------------------------------------------
# Create Scale Measures (unchanged)
# ------------------------------------------------------------------------
def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    measures_stream = stream.Stream()

    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))  # omit repeated top
    all_pitches = pitches_up + pitches_down

    notes_per_measure = 7  # 1 quarter + 6 eighths
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        # Last pitch => whole note
        if i == len(all_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)
            whole_note_measure = stream.Measure()

            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                whole_note_measure.insert(0, txt)

            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            whole_note_measure.append(n)
            measures_stream.append(whole_note_measure)
            break

        position_in_measure = note_counter % notes_per_measure
        if position_in_measure == 0:
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()

            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)

            n = note.Note(p)
            n.duration = duration.Duration('quarter')
            fix_enharmonic_spelling(n)
            current_measure.append(n)
        else:
            n = note.Note(p)
            n.duration = duration.Duration('eighth')
            fix_enharmonic_spelling(n)
            current_measure.append(n)

        note_counter += 1

    return measures_stream

# ------------------------------------------------------------------------
# Create Arpeggio Measures (ALL EIGHTH NOTES + final WHOLE)
# ------------------------------------------------------------------------
def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a major arpeggio (1–3–5–8), skipping repeated top notes between octaves.
    - All notes except the final note are 8th notes.
    - The final note is a whole note in a new measure.
    - 8 eighth notes per measure = 4 beats (4/4).
    """
    measures_stream = stream.Stream()

    # 1) Gather scale pitches
    scale_pitches = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )

    # 2) Build the arpeggio going up (avoid repeated top note per octave)
    arpeggio_up = []
    for o in range(num_octaves):
        base_idx = 7 * o
        try:
            root = scale_pitches[base_idx + 0]  # 1
            third = scale_pitches[base_idx + 2] # 3
            fifth = scale_pitches[base_idx + 4] # 5

            if o < num_octaves - 1:
                arpeggio_up.extend([root, third, fifth])
            else:
                # final octave => add the top note
                octave_tone = scale_pitches[base_idx + 7]
                arpeggio_up.extend([root, third, fifth, octave_tone])
        except IndexError:
            pass

    # 3) Build the downward portion, omitting the final top note
    if len(arpeggio_up) > 1:
        arpeggio_down = list(reversed(arpeggio_up[:-1]))
    else:
        arpeggio_down = []

    all_arpeggio_pitches = arpeggio_up + arpeggio_down

    # 4) 8 eighth notes per measure => 4 beats of eighths in 4/4
    notes_per_measure = 8
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        # If this is the last pitch => WHOLE note in a new measure
        if i == len(all_arpeggio_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)

            whole_note_measure = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                whole_note_measure.insert(0, txt)

            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            whole_note_measure.append(n)
            measures_stream.append(whole_note_measure)
            break

        position_in_measure = note_counter % notes_per_measure
        if position_in_measure == 0:
            # Start a new measure if necessary
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()

            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)

        # ALL EIGHTH NOTES here
        n = note.Note(p)
        n.duration = duration.Duration('eighth')
        fix_enharmonic_spelling(n)
        current_measure.append(n)

        note_counter += 1

    return measures_stream

# ------------------------------------------------------------------------
# Clear Output Folder
# ------------------------------------------------------------------------
def clear_output_folder(folder_path):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error removing {file_path}: {e}")

# ------------------------------------------------------------------------
# Generate AND Save BOTH Scale & Arpeggio in the SAME PDF
# ------------------------------------------------------------------------
def generate_and_save_scales_arpeggios_to_pdf(key_signature, num_octaves, instrument_name):
    """
    Generates a major scale (up/down) + a major arpeggio with all eighth notes (except 
    final whole note) in ONE PDF, skipping repeated top notes between octaves.
    """
    # 1) Clear output folder
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    clear_output_folder(output_folder)

    # 2) MuseScore environment
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    # 3) Determine clef/octave
    #    (For piano, this might return a dict with {right:(), left:()}
    #     so handle that case carefully.)
    clef_octave = determine_clef_and_octave(instrument_name)

    # 4) Create a Score
    score = stream.Score()

    # ------------------------------------------
    # PIANO: Two parts (Right hand / Left hand)
    # ------------------------------------------
    if instrument_name == "Piano":
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        major_key_obj_right = key.Key(key_signature, 'major')
        major_scale_obj_right = scale.MajorScale(key_signature)

        # Scale (RH)
        # Here, clef_octave is a dict for 'right' & 'left'
        selected_clef, octave_start = clef_octave['right']
        scale_measures_right = create_scale_measures(
            title_text=f"{key_signature} Major Scale (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if scale_measures_right:
            first_scale_measure_right = scale_measures_right[0]
            first_scale_measure_right.insert(0, getattr(clef, selected_clef)())
            first_scale_measure_right.insert(0, major_key_obj_right)

        # Arpeggio (RH)
        arpeggio_measures_right = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if arpeggio_measures_right:
            first_arp_measure_right = arpeggio_measures_right[0]
            first_arp_measure_right.insert(0, major_key_obj_right)

        # Append RH
        for m in scale_measures_right:
            right_part.append(m)
        for m in arpeggio_measures_right:
            right_part.append(m)

        # Left part
        left_part = stream.Part()
        left_instr = instrument.Piano()
        left_instr.staves = [2]
        left_part.insert(0, left_instr)

        major_key_obj_left = key.Key(key_signature, 'major')
        major_scale_obj_left = scale.MajorScale(key_signature)

        selected_clef_left, octave_start_left = clef_octave['left']
        scale_measures_left = create_scale_measures(
            title_text=f"{key_signature} Major Scale (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start_left,
            num_octaves=num_octaves
        )
        if scale_measures_left:
            first_scale_measure_left = scale_measures_left[0]
            first_scale_measure_left.insert(0, getattr(clef, selected_clef_left)())
            first_scale_measure_left.insert(0, major_key_obj_left)

        arpeggio_measures_left = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start_left,
            num_octaves=num_octaves
        )
        if arpeggio_measures_left:
            first_arp_measure_left = arpeggio_measures_left[0]
            first_arp_measure_left.insert(0, major_key_obj_left)

        # Append LH
        for m in scale_measures_left:
            left_part.append(m)
        for m in arpeggio_measures_left:
            left_part.append(m)

        # Add to score
        score.insert(0, right_part)
        score.insert(0, left_part)

    # ------------------------------------------
    # NON-PIANO: Single staff
    # ------------------------------------------
    else:
        part = stream.Part()
        instr = instrument.fromString(instrument_name)
        instr.staffCount = 1
        part.insert(0, instr)

        major_key_obj = key.Key(key_signature, 'major')
        major_scale_obj = scale.MajorScale(key_signature)

        # If the returned value is just a (clefType, octave) tuple:
        if isinstance(clef_octave, tuple):
            selected_clef, octave_start = clef_octave
        else:
            # If it somehow returned a dict or something else, default:
            selected_clef, octave_start = ("TrebleClef", 4)

        # SCALE measures
        scale_measures = create_scale_measures(
            title_text=f"{key_signature} Major Scale",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if scale_measures:
            first_measure_scale = scale_measures[0]
            first_measure_scale.insert(0, getattr(clef, selected_clef)())
            first_measure_scale.insert(0, major_key_obj)

        # ARPEGGIO measures
        arpeggio_measures = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if arpeggio_measures:
            first_measure_arp = arpeggio_measures[0]
            first_measure_arp.insert(0, major_key_obj)

        # Append everything
        for m in scale_measures:
            part.append(m)
        for m in arpeggio_measures:
            part.append(m)

        score.insert(0, part)

    # 5) Write the entire Score to a SINGLE PDF
    file_name = f"{key_signature}_{instrument_name}_maj_scales_arps"
    output_path = os.path.join(output_folder, f"{file_name}.pdf")

    # Write to PDF via musicxml
    score.write("musicxml.pdf", fp=output_path)
    print(f"PDF generated at: {output_path}")


# ---------------- EXAMPLE USAGE ----------------
if __name__ == "__main__":
    # Example: F# major scale + arpeggio, 1 octave, for Alto Sax
    # (Will use the approximate clef + octave from the instrument_map above)
    generate_and_save_scales_arpeggios_to_pdf("F#", 1, "Alto Saxophone")
