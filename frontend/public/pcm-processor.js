class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.sampleRate = options.processorOptions?.sampleRate || 44100;
    this.chunkSize = this.sampleRate / 50;
    this.buffer = [];
    this.isRunning = true;
    this.port.onmessage = (event) => {
      if (event.data.type === "flush") {
        if (this.buffer.length > 0) {
          const chunk = this.buffer.splice(0);
          const int16 = this.float32ToInt16(chunk);
          this.port.postMessage({
            type: "pcm",
            pcm: int16,
          });
        }
        this.isRunning = false;
        this.port.postMessage({ type: "flush_done" });
      }
    };
  }

  process(inputs, _outputs) {
    if (!this.isRunning) {
      return false;
    }
    const input = inputs[0];
    if (input && input.length > 0) {
      const channelData = input[0];
      for (let i = 0; i < channelData.length; i++) {
        this.buffer.push(channelData[i]);
      }
      if (this.buffer.length >= this.chunkSize) {
        const chunk = this.buffer.splice(0, this.chunkSize);
        const int16 = this.float32ToInt16(chunk);
        this.port.postMessage({
          type: "pcm",
          pcm: int16,
        });
      }
    }
    return true;
  }

  float32ToInt16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16Array.buffer;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
