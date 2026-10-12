from __future__ import annotations


class EchoCanceller:
    def __init__(self, filter_length: int = 400, enabled: bool = True):
        self._filter_length = filter_length
        self._enabled = enabled
        self._filter: list[float] = [0.0] * filter_length
        self._buffer: list[float] = [0.0] * filter_length

    def process(self, mic_signal: bytes, speaker_ref: bytes) -> bytes:
        if not self._enabled or len(mic_signal) < 2:
            return mic_signal
        try:
            import struct
            count = len(mic_signal) // 2
            mic = struct.unpack(f"<{count}h", mic_signal[:count * 2])
            ref = struct.unpack(f"<{count}h", speaker_ref[:count * 2])
            output = []
            for i in range(min(len(mic), len(ref))):
                self._buffer.pop(0)
                self._buffer.append(ref[i] / 32768.0)
                echo_est = sum(f * b for f, b in zip(self._filter, self._buffer))
                error = (mic[i] / 32768.0) - echo_est
                for j in range(self._filter_length):
                    self._filter[j] += 0.01 * error * self._buffer[self._filter_length - 1 - j]
                output.append(int(max(-32768, min(32767, error * 32768))))
            return struct.pack(f"<{len(output)}h", *output)
        except Exception:
            return mic_signal

    def reset(self):
        self._filter = [0.0] * self._filter_length
        self._buffer = [0.0] * self._filter_length
