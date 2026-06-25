function mixDownToMono(buffer: AudioBuffer): AudioBuffer {
  if (buffer.numberOfChannels === 1) {
    return buffer
  }
  const mono = new AudioBuffer({
    length: buffer.length,
    numberOfChannels: 1,
    sampleRate: buffer.sampleRate,
  })
  const output = mono.getChannelData(0)
  for (let i = 0; i < buffer.length; i += 1) {
    let sum = 0
    for (let ch = 0; ch < buffer.numberOfChannels; ch += 1) {
      sum += buffer.getChannelData(ch)[i] || 0
    }
    output[i] = sum / buffer.numberOfChannels
  }
  return mono
}

async function resampleTo16k(buffer: AudioBuffer): Promise<AudioBuffer> {
  if (buffer.sampleRate === 16000) {
    return buffer
  }
  const targetRate = 16000
  const offline = new OfflineAudioContext(1, Math.max(1, Math.ceil(buffer.duration * targetRate)), targetRate)
  const source = offline.createBufferSource()
  source.buffer = buffer
  source.connect(offline.destination)
  source.start(0)
  return offline.startRendering()
}

function audioBufferToPcm16(buffer: AudioBuffer): ArrayBuffer {
  const channel = buffer.getChannelData(0)
  const pcm = new Int16Array(channel.length)
  for (let i = 0; i < channel.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, channel[i] || 0))
    pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
  }
  return pcm.buffer
}

/** 将浏览器录音（webm/opus 等）转为 16kHz 单声道 PCM，供讯飞听写使用。 */
export async function blobToPcm16kMono(blob: Blob): Promise<Blob> {
  const ctx = new AudioContext()
  try {
    const arrayBuffer = await blob.arrayBuffer()
    const decoded = await ctx.decodeAudioData(arrayBuffer.slice(0))
    const mono = mixDownToMono(decoded)
    const resampled = await resampleTo16k(mono)
    const pcm = audioBufferToPcm16(resampled)
    return new Blob([pcm], { type: 'application/octet-stream' })
  } finally {
    await ctx.close()
  }
}
