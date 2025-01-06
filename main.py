import os
import shutil
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, duration
)
from PyPDF2 import PdfMerger

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
# Determine Clef and Octave
# ------------------------------------------------------------------------
def determine_clef_and_octave(instrument_name, part='right'):
    """
    Return a recommended clef and default octave start based on the instrument.
    For piano, differentiate between right and left hands.
    """

    # Piano logic
    if instrument_name == "Piano":
        return {"right": ("TrebleClef", 4), "left": ("BassClef", 2)}[part]

    # Electric Piano (if needed)
    if instrument_name == "Electric Piano":
        return ("TrebleClef", 4)

    # More instruments mapped:
    instrument_map = {
        # Strings
        "Violin":       ("TrebleClef", 3),
        "Viola":        ("AltoClef",   3),
        "Cello":        ("BassClef",   2),
        "Double Bass":  ("BassClef",   1),
        "Guitar":       ("TrebleClef", 3),
        "Harp":         ("TrebleClef", 3),  # often grand staff, simplified

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
        "Organ":        ("TrebleClef", 4),

        # Voice
        "Voice":        ("TrebleClef", 4),
    }

    # For unpitched percussion or unknown, default:
    unpitched_percussion = {
        "Bass Drum", "Cymbals", "Snare Drum", "Triangle", "Tambourine"
    }
    if instrument_name in unpitched_percussion:
        return ("PercussionClef", 4)

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
# Create Scale Measures
# ------------------------------------------------------------------------
def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Build an ascending + descending major scale (up to num_octaves).
    Returns a Stream of measures (each measure 4/4, with 1 quarter + 6 eighths,
    final note as a whole note).
    """
    measures_stream = stream.Stream()

    # Ascending pitches
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    # Descending omits repeated top
    pitches_down = list(reversed(pitches_up[:-1]))
    all_pitches = pitches_up + pitches_down

    notes_per_measure = 7  # 1 quarter + 6 eighths
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        # If this is the last pitch => make it a whole note in a new measure
        if i == len(all_pitches) - 1:
            if current_measure.notes:
                measures_stream.append(current_measure)
            whole_note_measure = stream.Measure()

            if i == 0:
                # Insert text for the very first measure
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
                # Insert text if it's the very first note
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
# Create Arpeggio Measures
# ------------------------------------------------------------------------
def create_arpeggio_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a major arpeggio (1–3–5–8), skipping repeated top notes between octaves.
    - All notes except the final are 8th notes in 4/4.
    - Final note is a whole note in a new measure.
    """
    measures_stream = stream.Stream()

    # Gather scale pitches
    scale_pitches = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )

    # Build ascending arpeggio
    arpeggio_up = []
    for o in range(num_octaves):
        base_idx = 7 * o  # each octave: 7 notes apart in the major scale
        try:
            root = scale_pitches[base_idx + 0]  # 1
            third = scale_pitches[base_idx + 2] # 3
            fifth = scale_pitches[base_idx + 4] # 5

            if o < num_octaves - 1:
                arpeggio_up.extend([root, third, fifth])
            else:
                # final octave => add top note (the octave)
                octave_tone = scale_pitches[base_idx + 7]
                arpeggio_up.extend([root, third, fifth, octave_tone])
        except IndexError:
            pass  # out of range, ignore

    # Build descending portion (omit final top note)
    arpeggio_down = list(reversed(arpeggio_up[:-1])) if len(arpeggio_up) > 1 else []

    all_arpeggio_pitches = arpeggio_up + arpeggio_down

    notes_per_measure = 8  # 8 eighth notes per measure => 4 beats
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_arpeggio_pitches):
        # Last pitch => whole note in new measure
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

        # All are eighth notes until final
        n = note.Note(p)
        n.duration = duration.Duration('eighth')
        fix_enharmonic_spelling(n)
        current_measure.append(n)

        note_counter += 1

    return measures_stream

# ------------------------------------------------------------------------
# Create Custom Line
# ------------------------------------------------------------------------
def create_custom_line_measures(
    title_text,
    notes_list,
    note_duration='quarter'
):
    """
    Create one (or multiple) measures of user-defined notes, each with
    a specified duration. Inserts a text label at the start.
    """
    measures_stream = stream.Stream()
    current_measure = stream.Measure()
    note_counter = 0
    notes_per_measure = 8  # Adjust based on desired measure capacity

    for i, note_name in enumerate(notes_list):
        if i == 0:
            # Insert text on the very first note
            txt = expressions.TextExpression(title_text)
            txt.placement = 'above'
            current_measure.insert(0, txt)

        # Start new measure if we've hit the measure capacity
        if note_counter % notes_per_measure == 0 and note_counter != 0:
            measures_stream.append(current_measure)
            current_measure = stream.Measure()

        # Create note
        n = note.Note(note_name)
        fix_enharmonic_spelling(n)
        n.duration = duration.Duration(note_duration)
        current_measure.append(n)
        note_counter += 1

    # Append last measure if not empty
    if current_measure.notes:
        measures_stream.append(current_measure)

    return measures_stream

# ------------------------------------------------------------------------
# Clear Output Folder
# ------------------------------------------------------------------------
def clear_output_folder(folder_path):
    """
    Removes all files and subfolders in the specified folder.
    Be sure you REALLY want to do this before calling!
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

# ------------------------------------------------------------------------
# Create Score for a Single Key (Scales and Arpeggios)
# ------------------------------------------------------------------------
def create_score_for_single_key_scales_arpeggios(
    key_signature,
    num_octaves,
    instrument_name
):
    """
    Build and return a music21.stream.Score for a single key + instrument.
    Includes:
      - Major Scale (up/down)
      - Major Arpeggio (up/down)
    """
    # We'll build a Score, but won't write to disk here.
    sc = stream.Score()

    # Decide on clef and octave
    clef_octave = determine_clef_and_octave(instrument_name)

    # If it's piano: 2 parts (RH, LH)
    if instrument_name == "Piano":
        # Right Hand
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        major_key_obj_right = key.Key(key_signature, 'major')
        major_scale_obj_right = scale.MajorScale(key_signature)

        # Scale (RH)
        selected_clef_right, octave_start_right = clef_octave['right']
        scale_measures_right = create_scale_measures(
            title_text=f"{key_signature} Major Scale (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start_right,
            num_octaves=num_octaves
        )
        if scale_measures_right:
            first_m = scale_measures_right[0]
            first_m.insert(0, getattr(clef, selected_clef_right)())
            first_m.insert(0, major_key_obj_right)
        for m in scale_measures_right:
            right_part.append(m)

        # Arpeggio (RH)
        arpeggio_measures_right = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start_right,
            num_octaves=num_octaves
        )
        if arpeggio_measures_right:
            first_arp = arpeggio_measures_right[0]
            first_arp.insert(0, major_key_obj_right)
        for m in arpeggio_measures_right:
            right_part.append(m)

        # Left Hand
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
            first_m_left = scale_measures_left[0]
            first_m_left.insert(0, getattr(clef, selected_clef_left)())
            first_m_left.insert(0, major_key_obj_left)
        for m in scale_measures_left:
            left_part.append(m)

        arpeggio_measures_left = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start_left,
            num_octaves=num_octaves
        )
        if arpeggio_measures_left:
            first_arp_left = arpeggio_measures_left[0]
            first_arp_left.insert(0, major_key_obj_left)
        for m in arpeggio_measures_left:
            left_part.append(m)

        # Add both parts to the score
        sc.insert(0, right_part)
        sc.insert(0, left_part)

    else:
        # Single-staff instrument
        part = stream.Part()
        instr_obj = instrument.fromString(instrument_name)
        part.insert(0, instr_obj)

        major_key_obj = key.Key(key_signature, 'major')
        major_scale_obj = scale.MajorScale(key_signature)

        # If determine_clef_and_octave is just a tuple:
        if isinstance(clef_octave, tuple):
            selected_clef, octave_start = clef_octave
        else:
            selected_clef, octave_start = ("TrebleClef", 4)

        # Scale
        scale_measures = create_scale_measures(
            title_text=f"{key_signature} Major Scale",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if scale_measures:
            first_scale_m = scale_measures[0]
            first_scale_m.insert(0, getattr(clef, selected_clef)())
            first_scale_m.insert(0, major_key_obj)
        for m in scale_measures:
            part.append(m)

        # Arpeggio
        arpeggio_measures = create_arpeggio_measures(
            title_text=f"{key_signature} Major Arpeggio",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )
        if arpeggio_measures:
            first_arp_m = arpeggio_measures[0]
            first_arp_m.insert(0, major_key_obj)
        for m in arpeggio_measures:
            part.append(m)

        # Add part to score
        sc.insert(0, part)

    return sc

# ------------------------------------------------------------------------
# Create Score for Custom Notes
# ------------------------------------------------------------------------
def create_score_for_custom_notes(
    title_text,
    custom_notes,
    instrument_name,
    key_signature="C",
    note_duration='quarter'
):
    """
    Build and return a music21.stream.Score containing only custom notes.
    """
    sc = stream.Score()

    # Single-staff instrument
    part = stream.Part()
    instr_obj = instrument.fromString(instrument_name)
    part.insert(0, instr_obj)

    major_key_obj = key.Key(key_signature, 'major')

    # Determine clef and octave
    clef_octave = determine_clef_and_octave(instrument_name)
    if isinstance(clef_octave, dict):
        # For instruments like Piano, default to 'right' hand
        selected_clef, octave_start = clef_octave.get('right', ("TrebleClef", 4))
    else:
        selected_clef, octave_start = clef_octave

    # Create custom measures
    custom_measures = create_custom_line_measures(
        title_text=title_text,
        notes_list=custom_notes,
        note_duration=note_duration
    )
    if custom_measures:
        first_custom_m = custom_measures[0]
        first_custom_m.insert(0, getattr(clef, selected_clef)())
        first_custom_m.insert(0, major_key_obj)
    for m in custom_measures:
        part.append(m)

    sc.insert(0, part)

    return sc

# ------------------------------------------------------------------------
# Generate PDF for Scales and Arpeggios (One Key per PDF)
# ------------------------------------------------------------------------
def generate_scales_arpeggios_pdf(
    key_signature,
    num_octaves,
    instrument_name,
    output_folder,
    pdf_filename
):
    """
    Generates a PDF for a single key's scales and arpeggios.
    """
    sc = create_score_for_single_key_scales_arpeggios(
        key_signature=key_signature,
        num_octaves=num_octaves,
        instrument_name=instrument_name
    )
    out_path = os.path.join(output_folder, pdf_filename)
    try:
        sc.write('musicxml.pdf', fp=out_path)
        print(f"PDF for {key_signature} created at: {out_path}")
    except Exception as e:
        print(f"Error writing PDF for {key_signature}: {e}")
        raise
    return out_path

# ------------------------------------------------------------------------
# Generate Custom Notes PDF
# ------------------------------------------------------------------------
def generate_custom_notes_pdf(
    title_text,
    custom_notes,
    instrument_name,
    output_folder,
    pdf_filename,
    key_signature="C",
    note_duration='quarter'
):
    """
    Generates a separate PDF for custom notes.
    """
    sc = create_score_for_custom_notes(
        title_text=title_text,
        custom_notes=custom_notes,
        instrument_name=instrument_name,
        key_signature=key_signature,
        note_duration=note_duration
    )
    out_path = os.path.join(output_folder, pdf_filename)
    try:
        sc.write('musicxml.pdf', fp=out_path)
        print(f"Custom notes PDF created at: {out_path}")
    except Exception as e:
        print(f"Error writing custom notes PDF: {e}")
        raise

    return out_path

# ------------------------------------------------------------------------
# Merge PDFs into Final PDF
# ------------------------------------------------------------------------
def merge_pdfs(
    pdf_paths,
    output_pdf_path
):
    """
    Merges multiple PDFs into a single PDF.
    """
    merger = PdfMerger()
    try:
        for pdf in pdf_paths:
            if os.path.exists(pdf):
                merger.append(pdf)
                print(f"Added '{pdf}' to the merger.")
            else:
                print(f"Warning: '{pdf}' does not exist and will be skipped.")
        merger.write(output_pdf_path)
        merger.close()
        print(f"Final merged PDF created at: {output_pdf_path}")
    except Exception as e:
        print(f"Error merging PDFs: {e}")
        raise

# ------------------------------------------------------------------------
# Clear Output Folder (Optional)
# ------------------------------------------------------------------------
def clear_output(output_folder):
    """
    Clears the output folder. Use with caution.
    """
    confirm = input(f"Are you sure you want to clear the folder '{output_folder}'? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_output_folder(output_folder)
        print(f"Output folder '{output_folder}' has been cleared.")
    else:
        print("Clearing output folder skipped.")

# ------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------
if __name__ == "__main__":
    # Configuration
    multiple_keys = ["F#", "C", "G"]  # List of keys to generate
    num_octaves = 1
    instrument_name = "Alto Saxophone"
    custom_line = ["C4", "D#4", "F4", "G4", "A4", "Bb4", "B#4", "C5"]
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    final_pdf = "Final_Sheet.pdf"

    # Ensure output directory exists
    os.makedirs(output_folder, exist_ok=True)

    # Optional: Clear the output folder
    # Uncomment the line below to enable clearing the output folder
    # clear_output(output_folder)

    try:
        # List to hold paths of all individual PDFs
        all_pdf_paths = []

        # Generate individual PDFs for each key
        for key_sig in multiple_keys:
            pdf_filename = f"{instrument_name.replace(' ', '_')}_{key_sig}_Scale_Arpeggio.pdf"
            pdf_path = generate_scales_arpeggios_pdf(
                key_signature=key_sig,
                num_octaves=num_octaves,
                instrument_name=instrument_name,
                output_folder=output_folder,
                pdf_filename=pdf_filename
            )
            all_pdf_paths.append(pdf_path)

        # Generate custom notes PDF
        custom_notes_pdf = f"{instrument_name.replace(' ', '_')}_Custom_Notes.pdf"
        custom_notes_path = generate_custom_notes_pdf(
            title_text="Custom Line",
            custom_notes=custom_line,
            instrument_name=instrument_name,
            output_folder=output_folder,
            pdf_filename=custom_notes_pdf,
            key_signature="C",  # You can adjust this as needed
            note_duration='quarter'
        )
        all_pdf_paths.append(custom_notes_path)

        # Merge all PDFs into a single final PDF
        final_pdf_path = os.path.join(output_folder, final_pdf)
        merge_pdfs(
            pdf_paths=all_pdf_paths,
            output_pdf_path=final_pdf_path
        )

    except Exception as e:
        print(f"An error occurred during PDF generation or merging: {e}")
