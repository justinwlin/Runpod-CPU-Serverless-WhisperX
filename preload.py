import whisperx
import os

device = os.environ.get('DEVICE', 'cpu') # cpu if on Mac
compute_type = os.environ.get('COMPUTE_TYPE', 'int8') #int8 if on Mac
batch_size = 8 # reduce if low on GPU mem
language_code = "en"

# 1. Transcribe with original whisper (batched)
model = whisperx.load_model("small", device, compute_type=compute_type, language="en")
# Load the audio
audio = whisperx.load_audio("test_audio.mp3")
# Transcribe the audio
result = model.transcribe(audio, batch_size=batch_size, language=language_code, print_progress=True)

# 2. Align whisper output
model_a, metadata = whisperx.load_align_model(language_code=language_code, device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device)
print(result)