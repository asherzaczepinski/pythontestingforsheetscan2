from music21 import stream, note, key, environment

# Set up the environment for music21
env = environment.Environment()
env['musicxmlPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'
env['musescoreDirectPNGPath'] = '/Applications/MuseScore 4.app/Contents/MacOS/mscore'

# Create a new stream for the score
score = stream.Score()

# Set the key signature for F# Major
f_sharp_major_key = key.Key('F#')
score.append(f_sharp_major_key)

# Create the F# Major scale
scale_notes = ["F#", "G#", "A#", "B", "C#", "D#", "E#", "F#"]

# Add notes to the score with explicit accidentals
for pitch in scale_notes:
    # Create a note with the given pitch
    n = note.Note(pitch)
    # Check if the note has an accidental and ensure it displays explicitly
    if n.pitch.accidental:
        n.pitch.accidental.displayStatus = True
    # Add the note to the score
    score.append(n)

# Save the score as a PNG image on the Desktop
png_path = '/Users/az/Desktop/f_sharp_major_scale.png'
score.write('musicxml.png', fp=png_path)
print(f'Score saved to {png_path}')
