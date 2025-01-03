from music21 import stream, scale, clef, key, note, instrument, environment

def determine_clef_and_octave(instrument_name):
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
    return instruments.get(instrument_name, ("TrebleClef", 4))

def create_scale(key_signature, num_octaves, instrument_name, scale_type="major"):
    selected_clef, octave_start = determine_clef_and_octave(instrument_name)
    
    s = stream.Score()
    s.append(instrument.__dict__[instrument_name]())
    s.append(clef.__dict__[selected_clef]())
    
    if scale_type == "major":
        ks = key.Key(key_signature)
        sc = scale.MajorScale(key_signature)
    else:
        ks = key.Key(key_signature)
        relative_minor_key = ks.getRelativeMinor()
        sc = scale.MinorScale(relative_minor_key.tonic.name)
        ks = key.Key(relative_minor_key.tonic.name, 'minor')

    s.append(ks)

    notes_up = sc.getPitches(f"{sc.tonic.name}{octave_start}", f"{sc.tonic.name}{octave_start + num_octaves}")
    notes_down = list(reversed(notes_up[:-1]))
    all_notes = notes_up + notes_down

    for pitch in all_notes:
        n = note.Note(pitch)
        if n.pitch.accidental:
            n.pitch.accidental.displayStatus = True
        s.append(n)
    
    return s

def save_scale(scale_stream, file_name):
    output_path = f'/Users/az/Desktop/pythontestingforsheetscan2/output/{file_name}.png'
    scale_stream.write('musicxml.png', fp=output_path)
    print(f'{file_name.capitalize()} scale saved to {output_path}')

def generate_and_save_scales(key_signature, num_octaves, instrument_name):
    env = environment.Environment()
    env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
    
    major_scale = create_scale(key_signature, num_octaves, instrument_name, "major")
    minor_scale = create_scale(key_signature, num_octaves, instrument_name, "minor")

    save_scale(major_scale, f"{key_signature}_major_{instrument_name}")
    save_scale(minor_scale, f"{key_signature}_relative_minor_{instrument_name}")

# Example usage
generate_and_save_scales('F#', 2, 'Piano')
