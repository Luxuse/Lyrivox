import logging
import threading
import sounddevice as sd
import numpy as np
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import re

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
    return None

# Frequency-to-bit mapping
def freq_to_bit(freq):
    if 950 <= freq <= 1050:
        return 0
    if 1950 <= freq <= 2050:
        return 1
    return None

# Dominant frequency extraction with more robust handling of low energy
def get_dominant_freq(data, rate):
    window = np.hanning(len(data))
    fft = np.abs(np.fft.rfft(data * window))
    freqs = np.fft.rfftfreq(len(data), d=1/rate)
    max_amplitude = np.max(fft)
    if max_amplitude < 1e-4:
        return 0
    return freqs[np.argmax(fft)]

class AudioDecoder(threading.Thread):
    def __init__(self, mode, output_widget=None, on_stop=None):
        super().__init__(daemon=True)
        self.mode = mode
        self.output_widget = output_widget
        self.on_stop = on_stop
        self._stop_event = threading.Event()
        self.stream = None
        self.bits_buffer = []
        self.text_buffer = []
        self.decoding = False
        self.last_char = None # To detect consecutive identical characters (potential spaces)
        self.consecutive_count = 0

    def run(self):
        self.decoding = True
        try:
            with sd.InputStream(
                channels=1,
                samplerate=sample_rate,
                blocksize=chunk_size,
                callback=self.callback,
                dtype='float32',
                latency='low'
            ) as stream:
                self.stream = stream
                logging.info(f"Stream started in {self.mode} mode.")
                while not self._stop_event.is_set():
                    sd.sleep(int(chunk_duration * 1000))
        except sd.PortAudioError as e:
            logging.error(f"PortAudio error during stream operation: {e}")
            if self.output_widget:
                self.output_widget.insert(tk.END, f"\n\n** Erreur Audio: {e} **\n")
            tk.messagebox.showerror("Erreur Audio", f"Erreur de PortAudio: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred in the audio stream: {e}")
            if self.output_widget:
                self.output_widget.insert(tk.END, f"\n\n** Erreur Inattendue: {e} **\n")
            tk.messagebox.showerror("Erreur Audio", f"Erreur inattendue: {e}")
        finally:
            self.stream = None
            self.decoding = False
            logging.info("Stream stopped.")
            if self.on_stop:
                self.on_stop()

    def stop(self):
        self._stop_event.set()

    def callback(self, indata, frames, time, status):
        if status:
            logging.warning(f"Status: {status}")
            if self.output_widget:
                self.output_widget.insert(tk.END, f"\n\n** Statut du Stream: {status} **\n")
        if not indata.any():
            return

        mono_data = indata[:, 0] if indata.ndim > 1 else indata
        freq = get_dominant_freq(mono_data, sample_rate)

        if self.mode == 'text':
            char = freq_to_char(freq)
            if char:
                if char == self.last_char:
                    self.consecutive_count += 1
                    if self.consecutive_count >= 3 and char != ' ': # Adjust the threshold as needed
                        if self.text_buffer and self.text_buffer[-1] != ' ':
                            self.text_buffer.append(' ')
                            logging.info(f"Interpreted consecutive '{char}' as space.")
                            if self.output_widget:
                                self.output_widget.insert(tk.END, ' ')
                else:
                    self.text_buffer.append(char)
                    logging.info(f"{int(freq)} Hz -> '{char}'")
                    if self.output_widget:
                        self.output_widget.insert(tk.END, char)
                    self.last_char = char
                    self.consecutive_count = 1
            else:
                self.last_char = None
                self.consecutive_count = 0
        elif self.mode == 'binary':
            bit = freq_to_bit(freq)
            if bit is not None:
                self.bits_buffer.append(str(bit))
                if len(self.bits_buffer) >= 8:
                    byte_str = ''.join(self.bits_buffer[:8])
                    self.bits_buffer = self.bits_buffer[8:]
                    try:
                        val = int(byte_str, 2)
                        logging.info(f"Byte received: {val:02X}")
                        if self.output_widget:
                            self.output_widget.insert(tk.END, f"{val:02X} ")
                    except ValueError:
                        logging.error(f"Error converting bit string '{byte_str}' to integer.")
                        if self.output_widget:
                            self.output_widget.insert(tk.END, f"** Erreur: Conversion binaire '{byte_str}' ** ")
        elif freq != 0:
            logging.debug(f"Frequency {int(freq)} Hz does not map to a binary bit.")

class App:
    def __init__(self, root):
        self.root = root
        root.title("Lyrivox")
        root.geometry("850x650")
        root.configure(bg="#2e2e2e")

        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#2e2e2e', foreground='#ececec', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 11, 'bold'), padding=8)
        style.map('TButton', background=[('active', '#5383EC')]) # Brighter blue
        style.configure('TCombobox', fieldbackground='#404040', background='#404040', foreground='#ffffff', font=('Segoe UI', 11))
        style.configure('TFrame', background='#2e2e2e')

        # Title Label
        title_label = ttk.Label(root, text="Lyrivox-1.4.0", font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=15)

        # Output
        self.text_output = ScrolledText(root, wrap=tk.WORD, bg='#333333', fg='#f0f0f0', insertbackground='#f0f0f0', font=('Consolas', 11))
        self.text_output.pack(expand=True, fill=tk.BOTH, padx=15, pady=10)

        # Controls frame
        ctrl = ttk.Frame(root)
        ctrl.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Mode Selection
        ttk.Label(ctrl, text="Mode d'écoute:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.mode_cb = ttk.Combobox(ctrl, values=["Texte", "Binaire"], state='readonly', width=12, font=('Segoe UI', 11))
        self.mode_cb.current(0)
        self.mode_cb.grid(row=0, column=1, padx=5)
        self.mode_cb.bind("<<ComboboxSelected>>", self.clear_output)

        # Transform Selection (Base64 Removed)
        ttk.Label(ctrl, text="Transformation post-écoute:").grid(row=0, column=2, padx=10, pady=5, sticky='w')
        self.transform_cb = ttk.Combobox(ctrl, values=["Aucun", "ROT13"], state='readonly', width=12, font=('Segoe UI', 11))
        self.transform_cb.current(0)
        self.transform_cb.grid(row=0, column=3, padx=5)

        # Buttons
        self.btn_start = ttk.Button(ctrl, text="▶ Démarrer", command=self.start_decoder)
        self.btn_start.grid(row=0, column=4, padx=10)
        self.btn_stop = ttk.Button(ctrl, text="■ Arrêter", state=tk.DISABLED, command=self.stop_decoder)
        self.btn_stop.grid(row=0, column=5, padx=5)

        self.decoder_thread = None

    def clear_output(self, event=None):
        self.text_output.delete('1.0', tk.END)

    def start_decoder(self):
        if self.decoder_thread and self.decoder_thread.is_alive():
            tk.messagebox.showwarning("En cours", "Un décodage est déjà en cours.")
            return
        self.clear_output()
        mode = 'text' if self.mode_cb.get() == 'Texte' else 'binary'
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.decoder = AudioDecoder(mode, output_widget=self.text_output, on_stop=self.on_decoder_stopped)
        self.decoder_thread = self.decoder
        self.decoder_thread.start()

    def stop_decoder(self):
        if self.decoder and self.decoder.is_alive():
            self.decoder.stop()
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_start.config(state=tk.NORMAL)
        elif self.decoder_thread:
            self.decoder_thread.join(timeout=1) # Wait briefly for thread to stop
            if self.decoder_thread and self.decoder_thread.is_alive():
                logging.warning("Decoder thread did not stop gracefully.")
                # Optionally add more forceful termination if needed

    def on_decoder_stopped(self):
        self.decoder_thread = None
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.post_process_output()

    def post_process_output(self):
        transform = self.transform_cb.get()
        content = self.text_output.get('1.0', tk.END).strip()

        if transform == 'ROT13' and content:
            decoded = content.translate(str.maketrans(
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
            ))
            self.text_output.insert(tk.END, f"\n\n=== Transformé (ROT13) ===\n{decoded}")

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()