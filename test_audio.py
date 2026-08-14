from brain.audio import AudioService
from brain.audio.analysis import AudioAnalyzer

audio = AudioService().load("test.wav")

analyzer = AudioAnalyzer(audio)

peak = analyzer.peak()
rms = analyzer.rms()
tempo = analyzer.tempo()
pitch = analyzer.pitch()
lufs = analyzer.lufs()

spectrum = analyzer.spectrum()
spectrogram = analyzer.spectrogram()
mel = analyzer.mel_spectrogram()
mfcc = analyzer.mfcc()
chroma = analyzer.chroma()

print("=" * 60)
print("NØISYNE Audio Analysis")
print("=" * 60)

print(f"Filename            : {audio.metadata.filename}")
print(f"Sample Rate         : {audio.metadata.sample_rate}")
print(f"Channels            : {audio.metadata.channels}")
print(f"Duration            : {audio.metadata.duration:.2f}s")

print()

print(f"Peak                : {peak:.6f}")
print(f"RMS                 : {rms:.6f}")
print(f"Tempo               : {tempo:.2f} BPM")
print(f"Pitch               : {pitch:.2f} Hz")
print(f"LUFS                : {lufs:.2f}")

print()

print(f"Spectrum            : {spectrum.shape}")
print(f"Spectrogram         : {spectrogram.shape}")
print(f"Mel Spectrogram     : {mel.shape}")
print(f"MFCC                : {mfcc.shape}")
print(f"Chroma              : {chroma.shape}")
