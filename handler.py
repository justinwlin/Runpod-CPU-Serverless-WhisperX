import os
import asyncio
import runpod
import time
import whisperx
import gc 
import base64
import tempfile
import requests

# Use the MODEL environment variable; fallback to a default if not set
model_name = os.getenv("MODEL", "mistralai/Mistral-7B-Instruct-v0.1")
concurrency_modifier = int(os.getenv("CONCURRENCY_MODIFIER", 1))
mode_to_run = os.getenv("MODE_TO_RUN", "pod")
model_length_default = 25000

# CHECK THE ENV VARIABLES FOR DEVICE AND COMPUTE TYPE
device = os.environ.get('DEVICE', 'cpu') # cpu if on Mac
compute_type = os.environ.get('COMPUTE_TYPE', 'int8') #int8 if on Mac
batch_size = 8 # reduce if low on GPU mem
language_code = "en"

print("------- ENVIRONMENT VARIABLES -------")
print("Concurrency: ", concurrency_modifier)
print("Mode running: ", mode_to_run)
print("------- -------------------- -------")

# Grab the model
model = whisperx.load_model("small", device, compute_type=compute_type, language="en")

def mp3_to_base64(file_path):
    """
    Convert an MP3 file to a Base64-encoded string.

    Args:
        file_path (str): The path to the MP3 file.

    Returns:
        str: The Base64-encoded string of the MP3 file.
    """
    # Read the file in binary mode
    with open(file_path, 'rb') as file:
        audio_data = file.read()

    # Encode the binary data to Base64
    return base64.b64encode(audio_data).decode('utf-8')
    
def base64_to_tempfile(base64_data):
    """
    Decode base64 data and write it to a temporary file.
    Returns the path to the temporary file.
    """
    # Decode the base64 data to bytes
    audio_data = base64.b64decode(base64_data)

    # Create a temporary file and write the decoded data
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    with open(temp_file.name, 'wb') as file:
        file.write(audio_data)

    return temp_file.name

def download_file(url):
    """
    Download a file from a URL to a temporary file and return its path.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Failed to download file from URL")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    temp_file.write(response.content)
    temp_file.close()
    return temp_file.name

async def handler(event):
    """
    Run inference on the model.

    Args:
        event (dict): The input event containing the audio data.
            The event should have the following structure:
            {
                "input": {
                    "audio_base_64": str,  # Base64-encoded audio data (optional)
                    "audio_url": str       # URL of the audio file (optional)
                }
            }
            Either "audio_base_64" or "audio_url" must be provided.
    """
    job_input = event['input']
    job_input_audio_base_64 = job_input.get('audio_base_64')
    job_input_audio_url = job_input.get('audio_url')

    if job_input_audio_base_64:
        # If there is base64 data
        audio_input = base64_to_tempfile(job_input_audio_base_64)
    elif job_input_audio_url and job_input_audio_url.startswith('http'):
        # If there is an URL
        audio_input = download_file(job_input_audio_url)
    else:
        return "No audio input provided"

    try:
        # Load the audio
        audio = whisperx.load_audio(audio_input)
        # Transcribe the audio
        result = model.transcribe(audio, batch_size=batch_size, language=language_code, print_progress=True)

        # 2. Align whisper output
        model_a, metadata = whisperx.load_align_model(language_code=language_code, device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device)
        print(result["segments"])

        # after alignment
        return result
    except:
        return "Error transcribing audio"

# https://docs.runpod.io/serverless/workers/handlers/handler-concurrency
# MAKE SURE RUNPOD VERSION PIP IS UPDATED PROPERLY!!!
def adjust_concurrency(current_concurrency):
    return concurrency_modifier

if mode_to_run in ["both", "serverless"]:
    # Assuming runpod.serverless.start is correctly implemented elsewhere
    runpod.serverless.start({
        "handler": handler,
        "concurrency_modifier": adjust_concurrency,
        "return_aggregate_stream": True,
    })

if mode_to_run == "pod":
    async def main():
        prompt = "What is the capital of France?"
        requestObject = {"input": {"audio_base_64": mp3_to_base64("test_audio.mp3")}}
        
        response = await handler(requestObject)
        print(response)

    asyncio.run(main())
