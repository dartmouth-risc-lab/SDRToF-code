import numpy as np
import soundfile as sf
from gnuradio import gr

class blk(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name="wav_writer",
            in_sig=[np.float32],
            out_sig=None
        )

        self.fs = 48000
        self.filename = "/home/risc/ram/USRP/output.wav"

        # buffer to accumulate samples
        self.buffer = []

    def work(self, input_items, output_items):
        x = input_items[0]

        # remove DC (important for phase signals)
        x = x - np.mean(x)

        self.buffer.extend(x.tolist())

        return len(x)

    def stop(self):
        data = np.array(self.buffer, dtype=np.float32)

        # normalize safely
        if len(data) > 0:
            data = data / (np.max(np.abs(data)) + 1e-8)

            sf.write(self.filename, data, self.fs)
            print(f"Saved WAV to {self.filename}")

        return True
