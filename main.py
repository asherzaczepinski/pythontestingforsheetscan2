import os
import shutil
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, duration
)

# Enharmonic mapping: name -> (newName, octaveAdjustment)
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", +1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}

def determine_clef_and_octave(instrument_name, part='right'):
    """
    Return a recommended clef and default octave start based on the instrument.
    For Piano, differentiate between right and left hands.
    """
    instrument_map = {
        "Piano": {"right": ("TrebleClef", 4), "left": ("BassClef", 2)},
        "Violin": ("TrebleClef", 3),
        "Cello": ("BassClef", 2),
        "Flute": ("TrebleClef", 4),
        "Clarinet": ("TrebleClef", 3),
        "Trumpet": ("TrebleClef", 4),
        "Trombone": ("BassClef", 2),
        "Guitar": ("TrebleClef", 3),
    }
    if instrument_name == "Piano":
        return instrument_map[instrument_name][part]
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

def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a stream of Measures containing:
      - A text title (above staff) at the beginning
      - The scale (up then down) split into multiple measures with the following rhythmic pattern:
        - Each measure starts with a quarter note
        - Followed by six eighth notes
      - The scale ends with a whole note in a separate measure
      - Automatic rewriting of E# -> F, B# -> C, etc.
    """
    measures_stream = stream.Stream()

    # --- Build the up-down scale pitches ---
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))  # avoid repeating top note
    all_pitches = pitches_up + pitches_down

    # Each measure: quarter (1 beat) + six eighths (6 * 0.5 = 3 beats) = 4 beats total
    notes_per_measure = 7  # 1 quarter + 6 eighths

    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        if i == len(all_pitches) - 1:
            # last pitch => separate measure with a whole note
            if current_measure.notes:
                measures_stream.append(current_measure)

            whole_note_measure = stream.Measure()

            # Add text to the *very first* measure only (i == 0)
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
            # start a new measure
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()

            if i == 0:
                # put the text expression in the first measure
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)

            # quarter note
            n = note.Note(p)
            n.duration = duration.Duration('quarter')
            fix_enharmonic_spelling(n)
            current_measure.append(n)
        else:
            # eighth note
            n = note.Note(p)
            n.duration = duration.Duration('eighth')
            fix_enharmonic_spelling(n)
            current_measure.append(n)

        note_counter += 1

    return measures_stream

# ------------------------------------------------------------------------
# NEW FUNCTION: CREATE ARPEGGIO MEASURES
# ------------------------------------------------------------------------
def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a stream of Measures for a simple major arpeggio pattern (1–3–5–8) per octave,
    going up through all octaves and then back down.
    """
    measures_stream = stream.Stream()

    # 1) Get all scale pitches across the desired octave range
    #    This array is what we'll access to pick chord tones.
    scale_pitches = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    
    # 2) Build the arpeggio (up)
    #    We'll assume the scale has 7 notes per octave in a standard major scale.
    #    For each octave, pick indices [0, 2, 4, 7] => 1, 3, 5, (octave).
    arpeggio_pitches_up = []
    for o in range(num_octaves):
        base_idx = 7 * o
        try:
            root = scale_pitches[base_idx + 0]  # 1
            third = scale_pitches[base_idx + 2] # 3
            fifth = scale_pitches[base_idx + 4] # 5
            octave_note = scale_pitches[base_idx + 7] # 8 (the next 'do')
            arpeggio_pitches_up.extend([root, third, fifth, octave_note])
        except IndexError:
            # If for some reason the scale doesn't have enough notes, just ignore
            pass

    # 3) Build the arpeggio (down), omitting the very top note to avoid duplication
    #    i.e. skip the last note from the "up" list
    #    You can omit more if you like.
    if len(arpeggio_pitches_up) > 1:
        arpeggio_pitches_down = list(reversed(arpeggio_pitches_up[:-1]))
    else:
        arpeggio_pitches_down = []

    # Combine up and down
    all_arpeggio_pitches = arpeggio_pitches_up + arpeggio_pitches_down

    # 4) Decide a rhythmic pattern for the arpeggio.
    #    Let's keep it simple: each measure = 4 quarter notes (4/4).
    #    Then the final note is a whole note in a separate measure.
    notes_per_measure = 4  # 4 quarter notes
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        # If this is the last pitch, we move it into a new measure as a whole note
        if i == len(all_arpeggio_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)

            whole_note_measure = stream.Measure()
            # Add text to the very first measure if i == 0
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
            # start a new measure
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()

            if i == 0:
                # put the text expression in the first measure
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)

        # quarter note for the arpeggio
        n = note.Note(p)
        n.duration = duration.Duration('quarter')
        fix_enharmonic_spelling(n)
        current_measure.append(n)

        note_counter += 1

    return measures_stream

def clear_output_folder(folder_path):
    """
    Removes all files and subdirectories within the given folder.
    """
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error removing {file_path}: {e}")

def generate_and_save_scales_to_pdf(key_signature, num_octaves, instrument_name):
    """
    Generates scales for the specified key, number of octaves, and instrument.
    Saves the output as a PDF in the designated output folder.
    """
    # 1) Clear the output folder
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    clear_output_folder(output_folder)

    # 2) Set up MuseScore environment
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    # 3) Determine clef & octave
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)

    # 4) Create a Score
    score = stream.Score()

    if instrument_name != "Piano":
        # Single staff
        part = stream.Part()
        instr = instrument.fromString(instrument_name)
        instr.staffCount = 1
        part.insert(0, instr)

        # Key signature & scale
        major_key_obj = key.Key(key_signature, 'major')
        major_scale_obj = scale.MajorScale(key_signature)

        # Build scale measures
        major_measures = create_scale_measures(
            title_text=f"{key_signature} Major Scale",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        # Insert clef and key signature in the first measure
        if major_measures:
            first_measure = major_measures[0]
            first_measure.insert(0, getattr(clef, selected_clef)())
            first_measure.insert(0, major_key_obj)

        # Add the measures to the part
        for m in major_measures:
            part.append(m)

        score.insert(0, part)

    else:
        # Piano => two staves
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        # Right hand major scale
        major_key_obj_right = key.Key(key_signature, 'major')
        major_scale_obj_right = scale.MajorScale(key_signature)

        major_measures_right = create_scale_measures(
            title_text=f"{key_signature} Major Scale (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        if major_measures_right:
            first_measure_right = major_measures_right[0]
            first_measure_right.insert(0, clef.TrebleClef())
            first_measure_right.insert(0, major_key_obj_right)

        for m in major_measures_right:
            right_part.append(m)

        left_part = stream.Part()
        left_instr = instrument.Piano()
        left_instr.staves = [2]
        left_part.insert(0, left_instr)

        # Left hand major scale (one octave lower)
        major_key_obj_left = key.Key(key_signature, 'major')
        major_scale_obj_left = scale.MajorScale(key_signature)

        major_measures_left = create_scale_measures(
            title_text=f"{key_signature} Major Scale (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start - 1,
            num_octaves=num_octaves
        )

        if major_measures_left:
            first_measure_left = major_measures_left[0]
            first_measure_left.insert(0, clef.BassClef())
            first_measure_left.insert(0, major_key_obj_left)

        for m in major_measures_left:
            left_part.append(m)

        score.insert(0, right_part)
        score.insert(0, left_part)

    # 5) Write Score to PDF
    file_name = f"{key_signature}_{instrument_name}_major_scales"
    output_path = os.path.join(output_folder, f"{file_name}.pdf")
    score.write("musicxml.pdf", fp=output_path)
    print(f"Scale PDF generated at: {output_path}")

# ------------------------------------------------------------------------
# NEW FUNCTION: GENERATE AND SAVE ARPEGGIOS TO PDF
# ------------------------------------------------------------------------
def generate_and_save_arpeggios_to_pdf(key_signature, num_octaves, instrument_name):
    """
    Generates a simple major arpeggio (1–3–5–8) for the specified key, 
    number of octaves, and instrument, then saves as a PDF.
    """
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    clear_output_folder(output_folder)

    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    selected_clef, octave_start = determine_clef_and_octave(instrument_name)
    score = stream.Score()

    if instrument_name != "Piano":
        # Single staff
        part = stream.Part()
        instr = instrument.fromString(instrument_name)
        instr.staffCount = 1
        part.insert(0, instr)

        # Key signature & scale
        major_key_obj = key.Key(key_signature, 'major')
        major_scale_obj = scale.MajorScale(key_signature)

        # Build arpeggio measures
        arpeggio_measures = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        # Insert clef and key signature in the first measure
        if arpeggio_measures:
            first_measure = arpeggio_measures[0]
            first_measure.insert(0, getattr(clef, selected_clef)())
            first_measure.insert(0, major_key_obj)

        # Add measures to part and add part to score
        for m in arpeggio_measures:
            part.append(m)
        score.insert(0, part)

    else:
        # Piano => two staves
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        # Right hand arpeggio
        major_key_obj_right = key.Key(key_signature, 'major')
        major_scale_obj_right = scale.MajorScale(key_signature)

        arpeggio_measures_right = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        if arpeggio_measures_right:
            first_measure_right = arpeggio_measures_right[0]
            first_measure_right.insert(0, clef.TrebleClef())
            first_measure_right.insert(0, major_key_obj_right)

        for m in arpeggio_measures_right:
            right_part.append(m)

        left_part = stream.Part()
        left_instr = instrument.Piano()
        left_instr.staves = [2]
        left_part.insert(0, left_instr)

        # Left hand arpeggio (one octave lower, for demonstration)
        major_key_obj_left = key.Key(key_signature, 'major')
        major_scale_obj_left = scale.MajorScale(key_signature)

        arpeggio_measures_left = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start - 1,
            num_octaves=num_octaves
        )

        if arpeggio_measures_left:
            first_measure_left = arpeggio_measures_left[0]
            first_measure_left.insert(0, clef.BassClef())
            first_measure_left.insert(0, major_key_obj_left)

        for m in arpeggio_measures_left:
            left_part.append(m)

        score.insert(0, right_part)
        score.insert(0, left_part)

    file_name = f"{key_signature}_{instrument_name}_major_arpeggios"
    output_path = os.path.join(output_folder, f"{file_name}.pdf")
    score.write("musicxml.pdf", fp=output_path)
    print(f"Arpeggio PDF generated at: {output_path}")


# ----------------- EXAMPLE USAGE -----------------
if __name__ == "__main__":
    # Generate a major scale PDF
    # generate_and_save_scales_to_pdf("F#", 2, "Clarinet")

    # Generate a major arpeggio PDF
    generate_and_save_arpeggios_to_pdf("F#", 2, "Clarinet")
