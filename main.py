import os
import shutil
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, duration, layout
)
from PyPDF2 import PdfMerger

# ------------------------------------------------------------------------
# Point music21 to MuseScore 3
# NOTE: If MuseScore 3 is installed elsewhere, change this path accordingly.
# ------------------------------------------------------------------------
environment.set('musicxmlPath', '/Applications/MuseScore 3.app/Contents/MacOS/mscore')
environment.set('musescoreDirectPNGPath', '/Applications/MuseScore 3.app/Contents/MacOS/mscore')


# ------------------------------------------------------------------------
# Enharmonic mapping: name -> (newName, octaveAdjustment)
# ------------------------------------------------------------------------
ENHARM_MAP = {
    "E#": ("F", 0),
    "B#": ("C", +1),
    "Cb": ("B", -1),
    "Fb": ("E", 0),
}


def determine_clef_and_octave(instrument_name, part='right'):
    """
    Return a recommended clef and default octave start based on the instrument.
    For piano, differentiate between right and left hands.
    """
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}

    instrument_map = {
        # Strings
        "Violin":       ("TrebleClef", 3),
        "Viola":        ("AltoClef",   3),
        "Cello":        ("BassClef",   2),
        "Double Bass":  ("BassClef",   1),
        "Guitar":       ("TrebleClef", 3),
        "Harp":         ("TrebleClef", 3),

        # Woodwinds
        "Alto Saxophone":   ("TrebleClef", 3),
        "Bass Clarinet":    ("TrebleClef", 2),
        "Bassoon":          ("BassClef",   2),
        "Clarinet":         ("TrebleClef", 3),
        "English Horn":     ("TrebleClef", 4),
        "Flute":            ("TrebleClef", 4),
        "Oboe":             ("TrebleClef", 4),
        "Piccolo":          ("TrebleClef", 5),
        "Tenor Saxophone":  ("TrebleClef", 3),
        "Trumpet":          ("TrebleClef", 4),

        # Brass
        "Euphonium":    ("BassClef", 2),
        "French Horn":  ("TrebleClef", 3),
        "Trombone":     ("BassClef", 2),
        "Tuba":         ("BassClef", 1),

        # Pitched Percussion
        "Marimba":      ("TrebleClef", 3),
        "Timpani":      ("BassClef",   3),
        "Vibraphone":   ("TrebleClef", 3),
        "Xylophone":    ("TrebleClef", 4),

        # Keyboards
        "Electric Piano": ("TrebleClef", 4),
        "Organ":          ("TrebleClef", 4),

        # Voice
        "Voice":        ("TrebleClef", 4),
    }

    unpitched_percussion = {
        "Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine"
    }
    if instrument_name in unpitched_percussion:
        return ("PercussionClef", 4)

    return instrument_map.get(instrument_name, ("TrebleClef", 4))


def fix_enharmonic_spelling(n):
    """
    Rename notes like E#, B#, Cb, Fb to simpler spellings, adjusting octave as needed.
    Force accidental display if present.
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


def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Build ascending/descending major scale. 
    4/4 time: 1 quarter + 6 eighths per measure, last note is a whole note.
    """
    measures_stream = stream.Stream()
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))
    all_pitches = pitches_up + pitches_down

    notes_per_measure = 7
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        # Last pitch => whole note in new measure
        if i == len(all_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)
            m_whole = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                m_whole.insert(0, txt)

            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            m_whole.append(n)
            measures_stream.append(m_whole)
            break

        pos_in_measure = note_counter % notes_per_measure
        if pos_in_measure == 0:
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


def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Build a major arpeggio (1–3–5–8) up and then down (omit final top note).
    All are eighth notes except the final note, which is a whole note.
    """
    measures_stream = stream.Stream()
    scale_pitches = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )

    # Ascending (1,3,5) per octave, final octave adds the 8 (octave).
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
                octave_tone = scale_pitches[base_idx + 7]
                arpeggio_up.extend([root, third, fifth, octave_tone])
        except IndexError:
            pass

    # Descending (omit final top note).
    arpeggio_down = list(reversed(arpeggio_up[:-1])) if len(arpeggio_up) > 1 else []
    all_arpeggio_pitches = arpeggio_up + arpeggio_down

    notes_per_measure = 8
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        if i == len(all_arpeggio_pitches) - 1:
            # Final pitch => whole note in a new measure
            if current_measure.notes:
                measures_stream.append(current_measure)
            m_whole = stream.Measure()
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                m_whole.insert(0, txt)

            n = note.Note(p)
            n.duration = duration.Duration('whole')
            fix_enharmonic_spelling(n)
            m_whole.append(n)
            measures_stream.append(m_whole)
            break

        pos_in_measure = note_counter % notes_per_measure
        if pos_in_measure == 0:
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


def create_custom_line_measures(
    title_text,
    notes_list,
    note_duration='quarter'
):
    """
    Create measures of user-defined notes, each with a specified duration.
    Text label is inserted at the very beginning.
    """
    measures_stream = stream.Stream()
    current_measure = stream.Measure()
    note_counter = 0
    notes_per_measure = 8

    for i, note_name in enumerate(notes_list):
        if i == 0:
            txt = expressions.TextExpression(title_text)
            txt.placement = 'above'
            current_measure.insert(0, txt)

        if note_counter % notes_per_measure == 0 and note_counter != 0:
            measures_stream.append(current_measure)
            current_measure = stream.Measure()

        n = note.Note(note_name)
        fix_enharmonic_spelling(n)
        n.duration = duration.Duration(note_duration)
        current_measure.append(n)
        note_counter += 1

    if current_measure.notes:
        measures_stream.append(current_measure)

    return measures_stream


def create_part_for_single_key_scales_arpeggios(key_signature, num_octaves, instrument_name):
    """
    Builds ONE Part for the given key.
    1) System break
    2) Major Scale
    3) System break
    4) Major Arpeggio

    The scale + arpeggio won't be attached by continuing barlines,
    but they're in the same Part so they appear grouped for that key.
    """
    part = stream.Part()
    instr_obj = instrument.fromString(instrument_name)
    part.insert(0, instr_obj)

    # Insert system break so each key starts fresh
    part.insert(0, layout.SystemLayout(isNew=True))

    major_key_obj = key.Key(key_signature, 'major')
    major_scale_obj = scale.MajorScale(key_signature)

    # Decide clef + octave
    clef_octave = determine_clef_and_octave(instrument_name)
    if isinstance(clef_octave, dict):
        selected_clef, octave_start = clef_octave.get('right', ("TrebleClef", 4))
    else:
        selected_clef, octave_start = clef_octave

    # --- Major Scale ---
    scale_measures = create_scale_measures(
        title_text=f"{key_signature} Major Scale",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    if scale_measures:
        first_m = scale_measures[0]
        first_m.insert(0, getattr(clef, selected_clef)())  # add clef
        first_m.insert(0, major_key_obj)                   # add key signature
        for m in scale_measures:
            part.append(m)

    # Insert a system break to prevent barline connections
    part.append(layout.SystemLayout(isNew=True))

    # --- Major Arpeggio ---
    arpeggio_measures = create_arpeggio_measures(
        title_text=f"{key_signature} Major Arpeggio",
        scale_object=major_scale_obj,
        octave_start=octave_start,
        num_octaves=num_octaves
    )
    if arpeggio_measures:
        # On the first measure, re-insert the key signature so that
        # the new system is labeled properly
        first_arp = arpeggio_measures[0]
        first_arp.insert(0, major_key_obj)
        for m in arpeggio_measures:
            part.append(m)

    return part


def create_part_for_custom_notes(
    title_text,
    custom_notes,
    instrument_name,
    key_signature="C",
    note_duration='quarter'
):
    """
    Build a Part with user-defined notes. 
    Starts on a fresh system so it doesn't connect to previous staves.
    """
    part = stream.Part()
    instr_obj = instrument.fromString(instrument_name)
    part.insert(0, instr_obj)

    # Force a new system break
    part.insert(0, layout.SystemLayout(isNew=True))

    major_key_obj = key.Key(key_signature, 'major')

    clef_octave = determine_clef_and_octave(instrument_name)
    if isinstance(clef_octave, dict):
        selected_clef, octave_start = clef_octave.get('right', ("TrebleClef", 4))
    else:
        selected_clef, octave_start = clef_octave

    measures = create_custom_line_measures(
        title_text=title_text,
        notes_list=custom_notes,
        note_duration=note_duration
    )
    if measures:
        first_m = measures[0]
        first_m.insert(0, getattr(clef, selected_clef)())
        first_m.insert(0, major_key_obj)
        for m in measures:
            part.append(m)

    return part


if __name__ == "__main__":
    # Adjust this output folder as needed
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    os.makedirs(output_folder, exist_ok=True)

    # Configuration
    multiple_keys = ["F#", "C", "G"]   # The keys you want
    num_octaves = 1
    instrument_name = "Alto Saxophone"
    custom_line = ["C4", "D#4", "F4", "G4", "A4", "Bb4", "B#4", "C5"]
    final_pdf = "All_in_One_Page.pdf"

    # Create a single Score
    score = stream.Score()

    # For each key, make one Part that includes Scale + Arpeggio
    # in separate systems, but grouped for that key.
    for key_sig in multiple_keys:
        part_for_key = create_part_for_single_key_scales_arpeggios(
            key_signature=key_sig,
            num_octaves=num_octaves,
            instrument_name=instrument_name
        )
        score.append(part_for_key)  # add the key group to the score

    # Finally, add a custom line as a separate Part
    part_for_custom = create_part_for_custom_notes(
        title_text="Custom Line",
        custom_notes=custom_line,
        instrument_name=instrument_name,
        key_signature="C",    # or whichever key
        note_duration='quarter'
    )
    score.append(part_for_custom)

    # Write out to one PDF
    out_path = os.path.join(output_folder, final_pdf)
    try:
        score.write('musicxml.pdf', fp=out_path)
        print(f"PDF created at: {out_path}")
    except Exception as e:
        print(f"Error writing PDF: {e}")
        raise
