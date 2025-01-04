import os
import shutil
from music21 import (
    stream, note, key, scale, clef, instrument,
    environment, expressions, layout, duration
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
    # Create a Stream to hold all measures
    measures_stream = stream.Stream()

    # Create the up-then-down pattern
    pitches_up = scale_object.getPitches(
        f"{scale_object.tonic.name}{octave_start}",
        f"{scale_object.tonic.name}{octave_start + num_octaves}"
    )
    pitches_down = list(reversed(pitches_up[:-1]))  # avoid repeating top note

    # Combine the up and down pitches
    all_pitches = pitches_up + pitches_down

    # Define the rhythmic pattern for each measure
    # Each measure has: quarter, eighth, eighth, eighth, eighth, eighth, eighth
    # Total beats per measure: 1 + 0.5*6 = 4 beats (fits 4/4 time)
    notes_per_measure = 7  # 1 quarter + 6 eighths

    # Initialize variables for iteration
    current_measure = stream.Measure()
    note_counter = 0

    for i, p in enumerate(all_pitches):
        # Handle the last note separately to assign it as a whole note in a new measure
        if i == len(all_pitches) - 1:
            # Append the current measure if it has any notes
            if current_measure.notes:
                measures_stream.append(current_measure)
            
            # Create a new measure for the whole note
            whole_note_measure = stream.Measure()
            
            # Add the text expression to the whole note measure if it's the first measure
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                whole_note_measure.insert(0, txt)
            
            # Create the whole note
            n = note.Note(p)
            n.duration = duration.Duration('whole')
            # Show accidentals (like sharps, flats, naturals)
            if n.pitch.accidental:
                n.pitch.accidental.displayStatus = True
            # Fix E#, B#, etc.
            fix_enharmonic_spelling(n)
            whole_note_measure.append(n)
            
            # Append the whole note measure to the stream
            measures_stream.append(whole_note_measure)
            break

        # Determine the position within the measure
        position_in_measure = note_counter % notes_per_measure

        if position_in_measure == 0:
            # Start a new measure
            if current_measure.notes:  # If not the first measure, append to stream
                measures_stream.append(current_measure)
            current_measure = stream.Measure()

            # Add the text expression to the first measure only
            if i == 0:
                txt = expressions.TextExpression(title_text)
                txt.placement = 'above'
                current_measure.insert(0, txt)

            # Create a quarter note
            n = note.Note(p)
            n.duration = duration.Duration('quarter')
            # Show accidentals (like sharps, flats, naturals)
            if n.pitch.accidental:
                n.pitch.accidental.displayStatus = True
            # Fix E#, B#, etc.
            fix_enharmonic_spelling(n)
            current_measure.append(n)
        else:
            # Create an eighth note
            n = note.Note(p)
            n.duration = duration.Duration('eighth')
            # Show accidentals (like sharps, flats, naturals)
            if n.pitch.accidental:
                n.pitch.accidental.displayStatus = True
            # Fix E#, B#, etc.
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
    # 1) Clear the output folder so it's empty before writing new files
    output_folder = "/Users/az/Desktop/pythontestingforsheetscan2/output"
    clear_output_folder(output_folder)

    # 2) Set up MuseScore environment
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

    # 3) Determine clef & octave
    # For Piano, we'll handle both hands separately later
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)

    # 4) Create a Score
    score = stream.Score()

    if instrument_name != "Piano":
        # Create a single-staff Part for non-Piano instruments
        part = stream.Part()
        instr = instrument.fromString(instrument_name)
        instr.staffCount = 1  # Force a single staff (no braces for Piano)
        part.insert(0, instr)

        # Create the major scale key signature
        major_key_obj = key.Key(key_signature, 'major')

        # Create major scale measures
        major_scale_obj = scale.MajorScale(key_signature)
        major_measures = create_scale_measures(
            title_text=f"{key_signature} Major Scale",
            scale_object=major_scale_obj,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        # Insert Clef and Key Signature into the first measure
        if major_measures:
            first_measure = major_measures[0]
            # Insert Clef
            first_measure.insert(0, getattr(clef, selected_clef)())
            # Insert Key Signature
            first_measure.insert(0, major_key_obj)

        # Append all measures to the part individually
        for m in major_measures:
            part.append(m)

        # Add the part to the score
        score.insert(0, part)

    else:
        # Handle Piano with two staves (Grand Staff)
        # Right Hand Part
        right_part = stream.Part()
        right_instr = instrument.Piano()
        right_instr.staves = [1]
        right_part.insert(0, right_instr)

        # Create the major scale key signature
        major_key_obj_right = key.Key(key_signature, 'major')

        # Create major scale measures for right hand
        major_scale_obj_right = scale.MajorScale(key_signature)
        major_measures_right = create_scale_measures(
            title_text=f"{key_signature} Major Scale (RH)",
            scale_object=major_scale_obj_right,
            octave_start=octave_start,
            num_octaves=num_octaves
        )

        # Insert Clef and Key Signature into the first measure for right hand
        if major_measures_right:
            first_measure_right = major_measures_right[0]
            # Insert Treble Clef
            first_measure_right.insert(0, clef.TrebleClef())
            # Insert Key Signature
            first_measure_right.insert(0, major_key_obj_right)

        # Append all measures to the right hand part
        for m in major_measures_right:
            right_part.append(m)

        # Left Hand Part
        left_part = stream.Part()
        left_instr = instrument.Piano()
        left_instr.staves = [2]
        left_part.insert(0, left_instr)

        # Create the major scale key signature for left hand
        major_key_obj_left = key.Key(key_signature, 'major')

        # Create major scale measures for left hand, possibly an octave lower
        major_scale_obj_left = scale.MajorScale(key_signature)
        major_measures_left = create_scale_measures(
            title_text=f"{key_signature} Major Scale (LH)",
            scale_object=major_scale_obj_left,
            octave_start=octave_start - 1,  # Lower octave for left hand
            num_octaves=num_octaves
        )

        # Insert Bass Clef and Key Signature into the first measure for left hand
        if major_measures_left:
            first_measure_left = major_measures_left[0]
            # Insert Bass Clef
            first_measure_left.insert(0, clef.BassClef())
            # Insert Key Signature
            first_measure_left.insert(0, major_key_obj_left)

        # Append all measures to the left hand part
        for m in major_measures_left:
            left_part.append(m)

        # Add both parts to the score
        score.insert(0, right_part)
        score.insert(0, left_part)

    # 5) Write the Score to a PDF
    file_name = f"{key_signature}_{instrument_name}_major_scales"
    output_path = os.path.join(output_folder, f"{file_name}.pdf")
    score.write("musicxml.pdf", fp=output_path)

    print(f"PDF generated at: {output_path}")

# Example usage:
if __name__ == "__main__":
    # For non-Piano instruments
    # generate_and_save_scales_to_pdf("F#", 1, "Trombone")

    # For Piano with two staves
    generate_and_save_scales_to_pdf("F#", 1, "Piano")
