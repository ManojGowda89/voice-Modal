from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)

tts.tts_to_file(
    text="Hello Manoj, your Docker voice setup is working!",
    file_path="output.wav"
)

print("Voice generated: output.wav")