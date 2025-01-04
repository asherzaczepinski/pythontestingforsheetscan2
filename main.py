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
        "Guitar": ("TrebleClef", 3),
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

def create_scale_measures(title_text, scale_object, octave_start, num_octaves):
    """
    Create a stream of Measures containing:
      - A text title (above staff) at the beginning
      - The scale (up then down) split into multiple measures with the following rhythmic pattern:
        - Each measure starts with a quarter note
        - Followed by six eighth notes
      - The scale ends with a whole note
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
        # Handle the last note separately to assign it as a whole note
        if i == len(all_pitches) - 1:
            # Create the whole note
            n = note.Note(p)
            n.duration = duration.Duration('whole')
            # Show accidentals (like sharps, flats, naturals)
            if n.pitch.accidental:
                n.pitch.accidental.displayStatus = True
            # Fix E#, B#, etc.
            fix_enharmonic_spelling(n)
            current_measure.append(n)
            measures_stream.append(current_measure)
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
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)

    # 4) Create a single-staff Part
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
    
    # 5) Append all measures to the part individually
    for m in major_measures:
        part.append(m)

    # Optional: If you want to add a system break after the major scale
    # Since there's no minor scale, this might not be necessary
    # If you still want to include it, ensure it's within a measure
    # For example, add an empty measure with a system break
    # sys_break_measure = stream.Measure()
    # sys_break = layout.SystemLayout()
    # sys_break.systemBreak = True
    # sys_break_measure.append(sys_break)
    # part.append(sys_break_measure)

    # 6) Put Part in a Score
    score = stream.Score()
    score.insert(0, part)

    # 7) Write the Score to a PDF
    file_name = f"{key_signature}_{instrument_name}_major_scales"
    output_path = os.path.join(output_folder, f"{file_name}.pdf")
    score.write("musicxml.pdf", fp=output_path)

    print(f"PDF generated at: {output_path}")

# Example usage:
if __name__ == "__main__":
    # e.g. "F#" => measure #1: F# major, 
    # with E# automatically displayed as F natural, etc.
    generate_and_save_scales_to_pdf("F#", 2, "Clarinet")
