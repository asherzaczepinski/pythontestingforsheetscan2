from music21 import stream, scale, clef, key, note, instrument, environment

def determine_clef_and_octave(instrument_name):
    # Mapping of instruments to clef and octave start
    instruments = {
        "Piano": ("TrebleClef", 4),
        "Violin": ("TrebleClef", 3),
        "Cello": ("BassClef", 2),
        "Flute": ("TrebleClef", 4),
        "Clarinet": ("TrebleClef", 3),
        "Trumpet": ("TrebleClef", 4),
        "Trombone": ("BassClef", 2),
        "Guitar": ("TrebleClef", 3)
    }
    return instruments.get(instrument_name, ("TrebleClef", 4))  # Default to TrebleClef and middle C octave if not found
def create_scale(key_signature, num_octaves, instrument_name, scale_type="major"):
    # Determine the clef and starting octave based on the instrument
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)
    
    # Create a new stream and set the instrument and clef
    s = stream.Score()
    s.append(instrument.__dict__[instrument_name]())  # Set the instrument
    s.append(clef.__dict__[selected_clef]())  # Set the clef
    
    # Generate the scale based on key signature and scale type
    if scale_type == "major":
        sc = scale.MajorScale(key_signature)
    else:
        major_key = key.Key(key_signature)
        relative_minor_key = major_key.getRelativeMinor()  # Correct method to get the relative minor key
        sc = scale.MinorScale(relative_minor_key.tonic.name)

    # Get pitches for the scale going up and back down
    notes_up = sc.getPitches(f"{sc.tonic.name}{octave_start}", f"{sc.tonic.name}{octave_start + num_octaves}")
    notes_down = list(reversed(notes_up[:-1]))  # Avoid repeating the top note
    all_notes = notes_up + notes_down

    # Add notes to the stream with explicit accidentals
    for pitch in all_notes:
        n = note.Note(pitch)
        if n.pitch.accidental:
            n.pitch.accidental.displayStatus = True
        s.append(n)
    
    # Return the stream object
    return s

def save_scale(scale_stream, file_name):
    # Define the path
    png_path = f'/Users/az/Desktop/{file_name}.png'
    # Save the score as a PNG image
    scale_stream.write('musicxml.png', fp=png_path)
    print(f'{file_name.capitalize()} scale saved to {png_path}')

# Set up the environment for music21
env = environment.Environment()
env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

# User inputs
key_signature = input("Enter the key (e.g., 'C', 'G#', 'F'): ")
num_octaves = int(input("Enter the number of octaves (1, 2, etc.): "))
instrument_name = input("Enter the instrument (e.g., Piano, Violin, Flute): ")

# Create scales
major_scale = create_scale(key_signature, num_octaves, instrument_name, "major")
minor_scale = create_scale(key_signature, num_octaves, instrument_name, "minor")

# Save scales
save_scale(major_scale, f"{key_signature}_major_{instrument_name}")
save_scale(minor_scale, f"{key_signature}_relative_minor_{instrument_name}")
