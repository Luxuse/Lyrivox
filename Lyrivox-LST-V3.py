import logging
import threading
import sounddevice as sd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("sound_log.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Audio parameters
sample_rate = 44100
chunk_duration = 0.1  # seconds
chunk_size = int(sample_rate * chunk_duration)

# Frequency-to-character mapping
def freq_to_char(freq):
    code = int(round((freq - 1000) / 10))
    if 32 <= code <= 126:
        return chr(code)
    return '?'

# Frequency-to-bit mapping
def freq_to_bit(freq):
    # 1000 Hz -> 0, 2000 Hz -> 1
    if abs(freq - 1000) < 100:
        return 0
    if abs(freq - 2000) < 100:
        return 1
    return None

# Dominant frequency extraction
def get_dominant_freq(data, rate):
    window = np.hanning(len(data))
    fft = np.abs(np.fft.rfft(data * window))
    freqs = np.fft.rfftfreq(len(data), d=1/rate)
    if np.max(fft) < 1e-3:
        return 0
    return freqs[np.argmax(fft)]

class AudioDecoder(threading.Thread):
    def __init__(self, mode, output_widget=None, on_stop=None):
        super().__init__(daemon=True)
        self.mode = mode  # 'text' or 'binary'
        self.output_widget = output_widget
        self.on_stop = on_stop
        self._stop_event = threading.Event()
        self.stream = None

    def run(self):
        try:
            self.stream = sd.InputStream(
                channels=1,
                samplerate=sample_rate,
                blocksize=chunk_size,
                callback=self.callback
            )
            self.stream.start()
            logging.info(f"Stream started in {self.mode} mode.")
            while not self._stop_event.is_set():
                sd.sleep(100)
        except Exception as e:
            logging.error(f"Erreur du flux audio: {e}")
            messagebox.showerror("Erreur Audio", str(e))
        finally:
            if self.stream:
                self.stream.stop()
                self.stream.close()
            logging.info("Stream arrêté.")
            if self.on_stop:
                self.on_stop()

    def stop(self):
        self._stop_event.set()

    def callback(self, indata, frames, time, status):
        if status:
            logging.warning(f"Statut: {status}")
        mono = indata[:, 0] if indata.ndim > 1 else indata
        freq = get_dominant_freq(mono, sample_rate)
        if freq <= 0:
            return

        if self.mode == 'text':
            char = freq_to_char(freq)
            msg = f"{int(freq)} Hz -> '{char}'"
            logging.info(msg)
            if self.output_widget:
                self.output_widget.insert(tk.END, char)
        else:  # binary mode
            bit = freq_to_bit(freq)
            if bit is None:
                return
            # accumulate bits into bytes
            if not hasattr(self, 'bits'):
                self.bits = []
            self.bits.append(str(bit))
            if len(self.bits) >= 8:
                byte_str = ''.join(self.bits[:8])
                self.bits = self.bits[8:]
                val = int(byte_str, 2)
                self._append_binary_byte(val)

    def _append_binary_byte(self, byte_val):
        if self.output_widget:
            self.output_widget.insert(tk.END, f"{byte_val:02X} ")
        logging.info(f"Byte reçu: {byte_val:02X}")

class App:
    def __init__(self, root):
        self.root = root
        root.title("Audio Decoder GUI")
        root.geometry("500x400")

        # Widgets
        self.text_output = scrolledtext.ScrolledText(root, wrap=tk.WORD)
        self.text_output.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        frm = tk.Frame(root)
        frm.pack(pady=5)

        self.btn_text = tk.Button(frm, text="Écouter Texte", command=self.start_text)
        self.btn_text.grid(row=0, column=0, padx=5)

        self.btn_binary = tk.Button(frm, text="Écouter Binaire", command=self.start_binary)
        self.btn_binary.grid(row=0, column=1, padx=5)

        self.btn_stop = tk.Button(frm, text="Arrêter", state=tk.DISABLED, command=self.stop)
        self.btn_stop.grid(row=0, column=2, padx=5)

        self.decoder = None

    def start_text(self):
        self._start_decoder('text')

    def start_binary(self):
        self._start_decoder('binary')

    def _start_decoder(self, mode):
        if self.decoder:
            messagebox.showwarning("En cours", "Un décodage est déjà en cours.")
            return
        self.text_output.delete(1.0, tk.END)
        self.btn_text.config(state=tk.DISABLED)
        self.btn_binary.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.decoder = AudioDecoder(mode, output_widget=self.text_output, on_stop=self.on_decoder_stop)
        self.decoder.start()

    def stop(self):
        if self.decoder:
            self.decoder.stop()

    def on_decoder_stop(self):
        self.decoder = None
        self.btn_text.config(state=tk.NORMAL)
        self.btn_binary.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
