import os
from music21 import (
    stream, note, key, scale, clef, layout,
    environment, expressions, duration
)

# ------------------------------------------------------------------------
# Point music21 to MuseScore 3 (adjust if your MuseScore is in a different path)
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

def fix_enharmonic_spelling(n):
    """Adjust enharmonic spelling using ENHARM_MAP if needed."""
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

def determine_clef_and_octave(instrument_name, part='right'):
    """
    Return a tuple (ClefName, OctaveStart) or a dict if instrument is Piano.
    """
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}
    instrument_map = {
        "Violin":          ("TrebleClef", 3),
        "Viola":           ("AltoClef",   3),
        "Cello":           ("BassClef",   2),
        "Double Bass":     ("BassClef",   1),
        "Guitar":          ("TrebleClef", 3),
        "Harp":            ("TrebleClef", 3),
        "Alto Saxophone":  ("TrebleClef", 4),
        "Bass Clarinet":   ("TrebleClef", 2),
        "Bassoon":         ("BassClef",   2),
        "Clarinet":        ("TrebleClef", 3),
        "English Horn":    ("TrebleClef", 4),
        "Flute":           ("TrebleClef", 4),
        "Oboe":            ("TrebleClef", 4),
        "Piccolo":         ("TrebleClef", 5),
        "Tenor Saxophone": ("TrebleClef", 3),
        "Trumpet":         ("TrebleClef", 4),
        "Euphonium":       ("BassClef",   2),
        "French Horn":     ("TrebleClef", 3),
        "Trombone":        ("BassClef",   2),
        "Tuba":            ("BassClef",   1),
        "Marimba":         ("TrebleClef", 3),
        "Timpani":         ("BassClef",   3),
        "Vibraphone":      ("TrebleClef", 3),
        "Xylophone":       ("TrebleClef", 4),
        "Electric Piano":  ("TrebleClef", 4),
        "Organ":           ("TrebleClef", 4),
        "Voice":           ("TrebleClef", 4),
    }
    unpitched_percussion = {"Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine"}
    if instrument_name in unpitched_percussion:
        return ("PercussionClef", 4)
    return instrument_map.get(instrument_name, ("TrebleClef", 4))

def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a series of measures containing ascending and descending scales
    for the specified scale object, starting octave, and number of octaves.
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
        # If we're at the very last note, give it a whole note measure
        if i == len(all_pitches) - 1:
            # Append the current measure if it has notes
            if current_measure.notes:
                measures_stream.append(current_measure)
            m_whole = stream.Measure()
            # Only add title for the very first scale; omit for subsequent measures
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
            # If current_measure has notes, push it to the stream and start new
            if current_measure.notes:
                measures_stream.append(current_measure)
            current_measure = stream.Measure()
            # Only add title for the very first scale; omit for subsequent measures
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

if __name__ == "__main__":
    # Output base directory
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    os.makedirs(output_folder, exist_ok=True)

    instrument_names = [
        "Violin", "Viola", "Cello", "Double Bass", "Guitar", "Harp", "Alto Saxophone",
        "Bass Clarinet", "Bassoon", "Clarinet", "English Horn", "Flute", "Oboe",
        "Piccolo", "Tenor Saxophone", "Trumpet", "Euphonium", "French Horn",
        "Trombone", "Tuba", "Marimba", "Timpani", "Vibraphone", "Xylophone",
        "Electric Piano", "Organ", "Voice",
        "Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine", "Piano"
    ]

    instrument_octave_ranges = {
        "Violin":          (3, 7),
        "Viola":           (2, 6),
        "Cello":           (2, 5),
        "Double Bass":     (1, 4),
        "Guitar":          (3, 6),
        "Harp":            (0, 7),
        "Alto Saxophone":  (3, 6),
        "Bass Clarinet":   (2, 5),
        "Bassoon":         (2, 5),
        "Clarinet":        (3, 6),
        "English Horn":    (3, 6),
        "Flute":           (4, 7),
        "Oboe":            (4, 7),
        "Piccolo":         (5, 8),
        "Tenor Saxophone": (3, 6),
        "Trumpet":         (3, 6),
        "Euphonium":       (2, 5),
        "French Horn":     (3, 6),
        "Trombone":        (2, 5),
        "Tuba":            (1, 4),
        "Marimba":         (3, 6),
        "Timpani":         (2, 4),
        "Vibraphone":      (3, 6),
        "Xylophone":       (4, 7),
        "Electric Piano":  (3, 6),
        "Organ":           (3, 6),
        "Voice":           (3, 6),
        "Bass Drum":       (4, 4),  # Percussive, octave doesn't matter
        "Cymbals":         (4, 4),
        "Snare Drum":      (4, 4),
        "Triangle":        (4, 4),
        "Tambourine":      (4, 4),
        "Piano":           (0, 7),
    }

    all_key_signatures = [
        "C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"
    ]

    num_octaves = 3  # Number of octaves for each scale

    for instrument in instrument_names:
        instrument_folder = os.path.join(output_folder, instrument.replace(" ", "_"))
        os.makedirs(instrument_folder, exist_ok=True)

        min_octave, max_octave = instrument_octave_ranges.get(instrument, (3, 6))

        for octave in range(min_octave, max_octave + 1):
            octave_folder = os.path.join(instrument_folder, f"Octave_{octave}")
            os.makedirs(octave_folder, exist_ok=True)

            part = stream.Part()
            part.insert(0, layout.SystemLayout(isNew=True))

            # Determine clef and starting octave for instrument once per part
            clef_octave = determine_clef_and_octave(instrument)
            if isinstance(clef_octave, dict):
                selected_clef, default_octave = clef_octave.get('right', ("TrebleClef", 4))
            else:
                selected_clef, default_octave = clef_octave
            # Insert clef at the very beginning of the part
            part.insert(0, getattr(clef, selected_clef)())

            # Loop over all key signatures
            for idx, key_sig in enumerate(all_key_signatures):
                major_key_obj = key.Key(key_sig, 'major')
                major_scale_obj = scale.MajorScale(key_sig)

                scale_measures = create_scale_measures(
                    title_text=f"{key_sig} Major Scale",
                    scale_object=major_scale_obj,
                    octave_start=octave,
                    num_octaves=num_octaves
                )

                if scale_measures:
                    first_m = scale_measures[0]
                    # For first scale, we already set clef, so only set key signature
                    first_m.insert(0, major_key_obj)
                    # Insert a system break for each new scale
                    first_m.insert(0, layout.SystemLayout(isNew=True))

                for m in scale_measures:
                    part.append(m)

            scales_score = stream.Score([part])
            pdf_filename = f"All_Major_Scales_Octave_{octave}.pdf"
            pdf_path = os.path.join(octave_folder, pdf_filename)
            scales_score.write('musicxml.pdf', fp=pdf_path)

            print(f"Created all major scales for {instrument} in octave {octave}: {pdf_path}")
