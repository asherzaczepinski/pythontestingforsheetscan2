import os
from music21 import stream, note, key, scale, clef, instrument, expressions, duration

# ------------------------------------------------------------------------
# Enharmonic mapping: name -> (newName, octaveAdjustment)
# ------------------------------------------------------------------------
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", 1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}

# ------------------------------------------------------------------------
# Fix Enharmonic Spelling
# ------------------------------------------------------------------------
def fix_enharmonic_spelling(n):
    """
    For notes spelled as E#, B#, Cb, or Fb, rename them to F, C, B, or E,
    adjusting octave if needed. Also ensures accidentals are displayed.
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
# Create Scale Measures (Major Scale up/down)
# ------------------------------------------------------------------------
def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Build an ascending + descending major scale (up to num_octaves).
    Each measure: 1 quarter note + 6 eighths, with the final note as a whole note.
    Returns a Stream of measures.
    """
    measures_stream = stream.Stream()
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))
    all_pitches = pitches_up + pitches_down

    notes_per_measure = 7  # 1 quarter + 6 eighths
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        # If it's the last pitch => whole note in a fresh measure
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
            # Start a new measure
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
# Create Arpeggio Measures (Major Arpeggio up/down)
# ------------------------------------------------------------------------
def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a major arpeggio (1–3–5–8) repeated for each octave,
    ascending then descending (omitting the very top note on the way down).
    All are eighth notes except the last note (whole note).
    """
    measures_stream = stream.Stream()
    scale_pitches = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
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
                # final octave => add the top note (the octave)
                octave_tone = scale_pitches[base_idx + 7]
                arpeggio_up.extend([root, third, fifth, octave_tone])
        except IndexError:
            pass
    arpeggio_down = list(reversed(arpeggio_up[:-1])) if len(arpeggio_up) > 1 else []
    all_arpeggio_pitches = arpeggio_up + arpeggio_down

    notes_per_measure = 8
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        # Last pitch => whole note
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
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)
        n = note.Note(p)
        n.duration = duration.Duration('eighth')
        fix_enharmonic_spelling(n)
        current_measure.append(n)
        note_counter += 1

    return measures_stream

# ------------------------------------------------------------------------
# Create a Custom Line (user-defined notes)
# ------------------------------------------------------------------------
def create_custom_line_measures(title_text, notes_list, note_duration='quarter'):
    """
    Creates measures that contain user-defined notes, each with the specified duration.
    Returns a Stream of measures.
    """
    measures_stream = stream.Stream()
    current_measure = stream.Measure()
    note_counter = 0
    notes_per_measure = 8  # Adjust if you want fewer/more notes per measure

    for i, note_name in enumerate(notes_list):
        if i == 0:
            txt = expressions.TextExpression(title_text)
            txt.placement = 'above'
            current_measure.insert(0, txt)
        # start a new measure if needed
        if note_counter % notes_per_measure == 0 and note_counter != 0:
            measures_stream.append(current_measure)
            current_measure = stream.Measure()
        n = note.Note(note_name)
        fix_enharmonic_spelling(n)
        n.duration = duration.Duration(note_duration)
        current_measure.append(n)
        note_counter += 1

    # append final measure if anything is in it
    if current_measure.notes:
        measures_stream.append(current_measure)

    return measures_stream

# ------------------------------------------------------------------------
# Determine Clef and Octave
# ------------------------------------------------------------------------
def determine_clef_and_octave(instrument_name, part='right'):
    """
    Returns a recommended clef and default octave start
    based on the instrument name.
    """
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}[part]
    # Could expand if needed
    instrument_map = {
        "Violin":       ("TrebleClef", 3),
        "Viola":        ("AltoClef",   3),
        "Cello":        ("BassClef",   2),
        "Double Bass":  ("BassClef",   1),
        "Guitar":       ("TrebleClef", 3),
        "Flute":        ("TrebleClef", 4),
        "Alto Saxophone": ("TrebleClef", 3),
        # etc...
    }
    return instrument_map.get(instrument_name, ("TrebleClef", 4))

# ------------------------------------------------------------------------
# Create One Big Score (all keys on one staff/part)
# ------------------------------------------------------------------------
def create_single_page_score_all_keys(
    multiple_keys,
    instrument_name,
    custom_notes,
    num_octaves=1,
    custom_line_title="Custom Line",
    key_mode='major'
):
    """
    Builds a single Score object (with one Part if single-staff instrument,
    or two Parts if Piano). Appends all scales/arpeggios for each key
    in sequence, then the custom line at the end.
    """
    # We'll create one Score
    sc = stream.Score()

    # If it's piano, build two parts. Otherwise just one.
    if instrument_name == "Piano":
        # Right-hand part
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        # Left-hand part
        left_part = stream.Part()
        left_instr = instrument.Piano()
        left_instr.staves = [2]
        left_part.insert(0, left_instr)

        # For each key, add scale + arpeggio to both parts
        for key_sig in multiple_keys:
            major_key_obj = key.Key(key_sig, key_mode)
            major_scale_obj = scale.MajorScale(key_sig)

            # Right hand
            rh_clef, rh_octave = determine_clef_and_octave("Piano", part='right')
            scale_measures_rh = create_scale_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Scale (RH)",
                scale_object=major_scale_obj,
                octave_start=rh_octave,
                num_octaves=num_octaves
            )
            # Insert key & clef on the first measure
            if scale_measures_rh:
                scale_measures_rh[0].insert(0, getattr(clef, rh_clef)())
                scale_measures_rh[0].insert(0, major_key_obj)

            for m in scale_measures_rh:
                right_part.append(m)

            arpeggio_measures_rh = create_arpeggio_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Arpeggio (RH)",
                scale_object=major_scale_obj,
                octave_start=rh_octave,
                num_octaves=num_octaves
            )
            if arpeggio_measures_rh:
                arpeggio_measures_rh[0].insert(0, major_key_obj)
            for m in arpeggio_measures_rh:
                right_part.append(m)

            # Left hand
            lh_clef, lh_octave = determine_clef_and_octave("Piano", part='left')
            scale_measures_lh = create_scale_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Scale (LH)",
                scale_object=major_scale_obj,
                octave_start=lh_octave,
                num_octaves=num_octaves
            )
            if scale_measures_lh:
                scale_measures_lh[0].insert(0, getattr(clef, lh_clef)())
                scale_measures_lh[0].insert(0, major_key_obj)
            for m in scale_measures_lh:
                left_part.append(m)

            arpeggio_measures_lh = create_arpeggio_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Arpeggio (LH)",
                scale_object=major_scale_obj,
                octave_start=lh_octave,
                num_octaves=num_octaves
            )
            if arpeggio_measures_lh:
                arpeggio_measures_lh[0].insert(0, major_key_obj)
            for m in arpeggio_measures_lh:
                left_part.append(m)

        # Finally, add the custom line for the right hand (or both, if you prefer).
        custom_measures_rh = create_custom_line_measures(
            title_text=custom_line_title,
            notes_list=custom_notes,
            note_duration='quarter'
        )
        if custom_measures_rh:
            # Insert key (C major by default) & clef on the first measure
            default_key = key.Key("C", key_mode)
            custom_measures_rh[0].insert(0, getattr(clef, rh_clef)())
            custom_measures_rh[0].insert(0, default_key)
        for m in custom_measures_rh:
            right_part.append(m)

        # If you also want the custom line on the left hand, repeat it:
        # custom_measures_lh = create_custom_line_measures(...)

        # Insert both parts
        sc.insert(0, right_part)
        sc.insert(0, left_part)

    else:
        # Single-staff instrument
        part = stream.Part()
        instr_obj = instrument.fromString(instrument_name)
        part.insert(0, instr_obj)

        # For each key, add scale + arpeggio
        for key_sig in multiple_keys:
            major_key_obj = key.Key(key_sig, key_mode)
            major_scale_obj = scale.MajorScale(key_sig)

            # Determine clef + octave
            selected_clef, octave_start = determine_clef_and_octave(instrument_name)
            scale_measures = create_scale_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Scale",
                scale_object=major_scale_obj,
                octave_start=octave_start,
                num_octaves=num_octaves
            )
            if scale_measures:
                scale_measures[0].insert(0, getattr(clef, selected_clef)())
                scale_measures[0].insert(0, major_key_obj)
            for m in scale_measures:
                part.append(m)

            # Arpeggio
            arpeggio_measures = create_arpeggio_measures(
                title_text=f"{key_sig} {key_mode.capitalize()} Arpeggio",
                scale_object=major_scale_obj,
                octave_start=octave_start,
                num_octaves=num_octaves
            )
            if arpeggio_measures:
                arpeggio_measures[0].insert(0, major_key_obj)
            for m in arpeggio_measures:
                part.append(m)

        # Finally, add the custom line
        custom_measures = create_custom_line_measures(
            title_text=custom_line_title,
            notes_list=custom_notes,
            note_duration='quarter'
        )
        if custom_measures:
            # Insert a default clef + key on the first custom measure
            default_key = key.Key("C", key_mode)
            custom_measures[0].insert(0, getattr(clef, selected_clef)())
            custom_measures[0].insert(0, default_key)
        for m in custom_measures:
            part.append(m)

        # Insert single part into the score
        sc.insert(0, part)

    return sc


# ------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------
if __name__ == "__main__":
    # Example configuration:
    multiple_keys = ["F#", "C", "G"]     # Keys to include
    instrument_name = "Alto Saxophone"   # Could be Piano, Violin, etc.
    custom_line = ["C4", "D#4", "F4", "G4", "A4", "Bb4", "B4", "C5"]  # Your custom notes
    num_octaves = 1
    output_pdf_path = "All_in_One_Sheet.pdf"

    # Create the single big Score
    my_score = create_single_page_score_all_keys(
        multiple_keys=multiple_keys,
        instrument_name=instrument_name,
        custom_notes=custom_line,
        num_octaves=num_octaves,
        custom_line_title="Custom Line",
        key_mode='major'
    )

    # Write it out as a single PDF
    try:
        my_score.write('musicxml.pdf', fp=output_pdf_path)
        print(f"Created single PDF with all keys and custom line: {output_pdf_path}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
