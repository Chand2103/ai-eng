# import sounddevice as sd
# import soundfile as sf
import numpy as np
from stt import STT
from llm import LLM
from tts import TTS

SAMPLE_RATE = 16000

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

    turn_count = 0
    
    while True:
        turn_count += 1
        audio_file = "input.wav"

        # User prompts
        print("\nPress ENTER to speak...")
        input()

        print("Hit ENTER to send...")
        input()

        # STT
        print("\n[STT]")
        text = stt.transcribe(audio_file)
        if not text:
            print("No speech detected. Try again.")
            continue
        print("You said:", text)

        # LLM - use history after first turn
        print("\n[LLM]")
        use_history = turn_count > 1
        response = llm.generate(text, use_history=use_history)
        print("AI:", response)

        # TTS - only for the last response
        print("\n[TTS]")
        audio_out = tts.synthesize(response)

        print(f"\n[Turn {turn_count} complete - Audio saved to {audio_out}]")

        # print("\n[PLAYING]")
        # play_audio(audio_out)


if __name__ == "__main__":
    main()