# import sounddevice as sd
import soundfile as sf
import numpy as np
from stt import STT
from llm import LLM
from tts import TTS

SAMPLE_RATE = 16000
DURATION_LIMIT = 10

# def record_audio(filename="input.wav"):
#     print("\nPress ENTER to start recording...")
#     input()

#     print("Recording... Press ENTER again to stop.")
#     recording = []

#     def callback(indata, frames, time, status):
#         recording.append(indata.copy())

#     stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=callback)
#     stream.start()

#     input()  # stop recording

#     stream.stop()
#     stream.close()

#     audio = np.concatenate(recording, axis=0)
#     sf.write(filename, audio, SAMPLE_RATE)

#     return filename


# def play_audio(file):
#     data, sr = sf.read(file)
#     sd.play(data, sr)
#     sd.wait()


def main():
    print("Loading models...")

    stt = STT()
    llm = LLM()
    tts = TTS()

    print("Ready!")

    while True:
        audio_file = "input.wav"

        print("\n[STT]")
        text = stt.transcribe(audio_file)
        print("You said:", text)

        if not text:
            continue

        print("\n[LLM]")
        response = llm.generate(text)
        print("AI:", response)

        print("\n[TTS]")
        audio_out = tts.synthesize(response)

        # print("\n[PLAYING]")
        # play_audio(audio_out)


if __name__ == "__main__":
    main()