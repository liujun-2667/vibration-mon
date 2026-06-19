function nextPow2(n) {
  return Math.pow(2, Math.ceil(Math.log2(n)));
}

function fftRadix2(real, imag) {
  const n = real.length;
  if (n === 1) return { real, imag };

  const half = n / 2;
  const evenReal = new Array(half);
  const evenImag = new Array(half);
  const oddReal = new Array(half);
  const oddImag = new Array(half);

  for (let i = 0; i < half; i++) {
    evenReal[i] = real[2 * i];
    evenImag[i] = imag[2 * i];
    oddReal[i] = real[2 * i + 1];
    oddImag[i] = imag[2 * i + 1];
  }

  const even = fftRadix2(evenReal, evenImag);
  const odd = fftRadix2(oddReal, oddImag);

  const resultReal = new Array(n);
  const resultImag = new Array(n);

  for (let k = 0; k < half; k++) {
    const angle = -2 * Math.PI * k / n;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    const tReal = cos * odd.real[k] - sin * odd.imag[k];
    const tImag = sin * odd.real[k] + cos * odd.imag[k];
    resultReal[k] = even.real[k] + tReal;
    resultImag[k] = even.imag[k] + tImag;
    resultReal[k + half] = even.real[k] - tReal;
    resultImag[k + half] = even.imag[k] - tImag;
  }

  return { real: resultReal, imag: resultImag };
}

export function computeFFT(signal, sampleRate) {
  const n = nextPow2(signal.length);
  const real = new Array(n).fill(0);
  const imag = new Array(n).fill(0);

  const mean = signal.reduce((a, b) => a + b, 0) / signal.length;
  for (let i = 0; i < signal.length && i < n; i++) {
    real[i] = (signal[i] - mean) * (0.5 - 0.5 * Math.cos(2 * Math.PI * i / (signal.length - 1 || 1)));
  }

  const result = fftRadix2(real, imag);

  const halfN = n / 2;
  const frequencies = [];
  const amplitudes = [];

  for (let k = 0; k < halfN; k++) {
    frequencies.push((k * sampleRate) / n);
    const amp = 2 * Math.sqrt(result.real[k] ** 2 + result.imag[k] ** 2) / (signal.length || 1);
    amplitudes.push(amp);
  }

  return { frequencies, amplitudes };
}

export function computeSpectrumBars(frequencies, amplitudes, maxFreq = 500, numBars = 50) {
  const barWidth = maxFreq / numBars;
  const bars = [];
  const labels = [];

  for (let i = 0; i < numBars; i++) {
    const startFreq = i * barWidth;
    const endFreq = (i + 1) * barWidth;
    let maxAmp = 0;
    let count = 0;

    for (let j = 0; j < frequencies.length; j++) {
      if (frequencies[j] >= startFreq && frequencies[j] < endFreq) {
        if (amplitudes[j] > maxAmp) {
          maxAmp = amplitudes[j];
        }
        count++;
      }
      if (frequencies[j] >= endFreq) {
        break;
      }
    }

    bars.push(maxAmp);
    labels.push(startFreq.toFixed(0));
  }

  return { labels, bars };
}

export function findDominantFrequency(frequencies, amplitudes, maxFreq = 500) {
  let maxAmp = 0;
  let maxIdx = 0;

  for (let i = 0; i < frequencies.length; i++) {
    if (frequencies[i] > maxFreq) break;
    if (amplitudes[i] > maxAmp) {
      maxAmp = amplitudes[i];
      maxIdx = i;
    }
  }

  return {
    frequency: frequencies[maxIdx] || 0,
    amplitude: maxAmp,
    index: maxIdx,
  };
}
