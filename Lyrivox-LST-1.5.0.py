import logging
import threading
import sounddevice as sd
import numpy as np
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import base64
import binascii

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
chunk_duration = 0.1
chunk_size = int(sample_rate * chunk_duration)

# Mappage Fréquence vers Caractère
def freq_to_char(freq):
    code = int(round((freq - 1000) / 10))
    if 32 <= code <= 126:
        return chr(code)
    return None

# Mappage Fréquence vers Bit
def freq_to_bit(freq):
    if 950 <= freq <= 1050:
        return 0
    if 1950 <= freq <= 2050:
        return 1
    return None

# Extraction de la fréquence dominante
def get_dominant_freq(data, rate):
    window = np.hanning(len(data))
    fft = np.abs(np.fft.rfft(data * window))
    freqs = np.fft.rfftfreq(len(data), d=1/rate)
    max_amplitude = np.max(fft)
    if max_amplitude < 1e-4:
        return 0
    dominant_freq_index = np.argmax(fft)
    return freqs[dominant_freq_index]

# Fonction d'encodage Inverser (copiée depuis le générateur pour le post-traitement)
def encode_reverse(text):
    """Inverse simplement la chaîne de caractères."""
    return text[::-1]

# Classe pour gérer l'écoute et le décodage audio en arrière-plan
class AudioDecoder(threading.Thread):
    def __init__(self, mode, output_widget=None, on_stop=None, status_var=None):
        super().__init__(daemon=True)
        self.root = output_widget.winfo_toplevel() if output_widget else None
        self.mode = mode
        # L'AudioDecoder utilise output_widget tel qu'il est reçu (référence au ScrolledText)
        self.output_widget = output_widget
        self.on_stop = on_stop
        self.status_var = status_var
        self._stop_event = threading.Event()
        self.stream = None
        self.bits_buffer = []
        self.text_buffer = []
        self.decoding = False

        self.last_char = None
        self.consecutive_count = 0
        self.consecutive_threshold = 3

    def run(self):
        self.decoding = True
        if self.status_var: self.status_var.set("🎙️ Démarrage du flux audio...")
        logging.info(f"Attempting to start audio stream with sample rate {sample_rate}, block size {chunk_size}.")
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
                if self.status_var: self.status_var.set(f"👂 Écoute démarrée en mode '{self.mode}'...")
                logging.info(f"Stream started successfully in '{self.mode}' mode.")
                while not self._stop_event.is_set():
                    sd.sleep(int(chunk_duration * 1000))
        except sd.PortAudioError as e:
            logging.error(f"PortAudio error during stream operation: {e}", exc_info=True)
            if self.status_var: self.status_var.set("❌ Erreur PortAudio !")
            if self.output_widget and self.output_widget.winfo_exists():
                self.output_widget.after(0, self.output_widget.insert, tk.END, f"\n\n** Erreur Audio PortAudio : {e} **\n")
                self.output_widget.after(0, self.output_widget.see, tk.END)
            if self.root and self.root.winfo_exists():
                 self.root.after(0, lambda: messagebox.showerror("Erreur Audio", f"Erreur de PortAudio. Vérifiez vos périphériques audio et la configuration du microphone.\n\nDétails : {e}"))
        except Exception as e:
            logging.error(f"An unexpected error occurred in the audio stream: {e}", exc_info=True)
            if self.status_var: self.status_var.set("❌ Erreur Inattendue !")
            if self.output_widget and self.output_widget.winfo_exists():
                self.output_widget.after(0, self.output_widget.insert, tk.END, f"\n\n** Erreur Inattendue dans le Stream Audio : {e} **\n")
                self.output_widget.after(0, self.output_widget.see, tk.END)
            if self.root and self.root.winfo_exists():
                 self.root.after(0, lambda: messagebox.showerror("Erreur Audio", f"Une erreur inattendue est survenue pendant le décodage : {e}"))
        finally:
            self.stream = None
            self.decoding = False
            logging.info("Stream stopped.")
            if self.status_var: self.status_var.set("⏹️ Écoute arrêtée.")
            if self.on_stop:
                if self.output_widget and self.output_widget.winfo_exists():
                     self.output_widget.after(0, self.on_stop)
                elif self.root and self.root.winfo_exists():
                     self.root.after(0, self.on_stop)

    def stop(self):
        """Signale au thread de s'arrêter."""
        logging.info("Stopping stream requested.")
        self._stop_event.set()
        if self.status_var: self.status_var.set("... Arrêt en cours ...")

    def callback(self, indata, frames, time, status):
        """Fonction de rappel appelée par sounddevice pour traiter les chunks audio entrants."""
        if status:
            logging.warning(f"Stream callback status: {status}")

        if not indata.any() or np.max(np.abs(indata)) < 1e-5:
             self.last_char = None
             self.consecutive_count = 0
             return

        mono_data = indata[:, 0] if indata.ndim > 1 else indata
        freq = get_dominant_freq(mono_data, sample_rate)

        if self.mode == 'text':
            char = freq_to_char(freq)
            if char:
                logging.debug(f"Detected frequency: {int(freq)} Hz -> Potential char '{char}'")

                if char == self.last_char and char != ' ':
                    self.consecutive_count += 1
                    if self.consecutive_count >= self.consecutive_threshold:
                        if self.text_buffer and self.text_buffer[-1] != ' ':
                             if self.output_widget and self.output_widget.winfo_exists():
                                self.output_widget.after(0, self.output_widget.insert, tk.END, ' ')
                                self.output_widget.after(0, self.output_widget.see, tk.END)
                             self.text_buffer.append(' ')
                             logging.info(f"Interpreted consecutive '{char}' as space.")

                elif char != self.last_char:
                    if self.output_widget and self.output_widget.winfo_exists():
                        self.output_widget.after(0, self.output_widget.insert, tk.END, char)
                        self.output_widget.after(0, self.output_widget.see, tk.END)
                    self.text_buffer.append(char)
                    self.last_char = char
                    self.consecutive_count = 1

            else:
                 if freq > 0:
                     logging.debug(f"Frequency {int(freq)} Hz does not map to a character.")
                 self.last_char = None
                 self.consecutive_count = 0

        elif self.mode == 'binary':
            bit = freq_to_bit(freq)
            if bit is not None:
                self.bits_buffer.append(str(bit))
                logging.debug(f"Detected bit: {bit}. Buffer: {''.join(self.bits_buffer)}")

                if len(self.bits_buffer) >= 8:
                    byte_str = ''.join(self.bits_buffer[:8])
                    self.bits_buffer = self.bits_buffer[8:]

                    try:
                        val = int(byte_str, 2)
                        logging.info(f"Byte received: {byte_str} -> {val:02X}")
                        if self.output_widget and self.output_widget.winfo_exists():
                            self.output_widget.after(0, self.output_widget.insert, tk.END, f"{val:02X} ")
                            self.output_widget.after(0, self.output_widget.see, tk.END)
                    except ValueError:
                        logging.error(f"Error converting bit string '{byte_str}' to integer.")
                        if self.output_widget and self.output_widget.winfo_exists():
                            self.output_widget.after(0, self.output_widget.insert, tk.END, f"** Erreur: Conversion binaire '{byte_str}' ** ")
                            self.output_widget.after(0, self.output_widget.see, tk.END)
            elif freq != 0:
                logging.debug(f"Frequency {int(freq)} Hz does not map to a binary bit.")


# Interface Graphique Tkinter pour le Décodeur
class App:
    def __init__(self, root):
        self.root = root
       
        root.title("Lyrivox : 1.5.0")
        root.geometry("700x650")
        root.configure(bg="#333333")
        root.minsize(600, 500)

        # Configuration du Style TTK (copié du générateur pour matcher)
        style = ttk.Style(root)
        style.theme_use('clam')

        style.configure("TFrame", background="#333333")
        style.configure("TLabel", background="#333333", foreground="#f0f0f0", font=("Segoe UI", 11))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8,
                        background="#5cb85c", foreground="#ffffff", relief="flat")
        style.map("TButton",
                  background=[('active', '#4cae4c')],
                  foreground=[('disabled', '#777777')])

        style.configure("TCombobox", fieldbackground="#444444", background="#444444", foreground="#f0f0f0",
                        font=("Segoe UI", 10), relief="flat")
        style.map("TCombobox",
                  fieldbackground=[('readonly', '#444444')],
                  foreground=[('readonly', '#f0f0f0')])

        # Style des zones de texte Tkinter (pour Text et ScrolledText) - Copié du générateur
        text_style_options = {
            "bg": "#444444",
            "fg": "#f0f0f0",
            "insertbackground": "#f0f0f0",
            "font": ("Consolas", 10),
            "relief": "flat"
        }
        # Style des Entry (pour les configurations) - Copié du générateur
        entry_style_options = {
            "bg": "#444444",
            "fg": "#f0f0f0",
            "insertbackground": "#f0f0f0",
            "font": ("Segoe UI", 10),
            "insertbackground": "#f0f0f0",
            "relief": "flat"
        }

        # Cadre principal (copié du générateur)
        frm = ttk.Frame(root, padding=20)
        frm.pack(fill="both", expand=True)

        # Titre principal (copié du générateur)
        title_label = ttk.Label(frm, text="Lyrivox", font=("Segoe UI", 15, "bold"))
        title_label.pack(anchor="center", pady=(0, 15))

        # Zone de sortie décodée (similaire à la zone de fréquences du générateur)
        ttk.Label(frm, text="Sortie décodée :").pack(anchor="w", pady=(0, 5))
        self.text_output = ScrolledText(frm, height=12, wrap=tk.WORD, **text_style_options)
        self.text_output.pack(fill="both", expand=True, pady=(0, 10))

        # Cadre pour les options (copié du générateur)
        options_frame = ttk.Frame(frm)
        options_frame.pack(fill="x", pady=(0, 10))

        # Sélection du Mode d'écoute (à gauche, comme l'encodage dans le générateur)
        mode_frame = ttk.Frame(options_frame)
        mode_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(mode_frame, text="Mode d'écoute :").pack(anchor="w", pady=(0, 5))
        self.mode_cb = ttk.Combobox(mode_frame, values=["Texte", "Binaire"], state='readonly', width=15, font=("Segoe UI", 10))
        self.mode_cb.current(0)
        self.mode_cb.pack(fill="x")

        # Sélection de la Transformation (à droite, comme la configuration durée dans le générateur)
        transform_frame = ttk.Frame(options_frame)
        transform_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))
        ttk.Label(transform_frame, text="Transformation post-écoute :").pack(anchor="w", pady=(0, 5))
        self.transform_cb = ttk.Combobox(transform_frame, values=["Aucun", "ROT13", "Inverser", "Base64"], state='readonly', width=15, font=("Segoe UI", 10))
        self.transform_cb.current(0)
        self.transform_cb.pack(fill="x")

        # Label de statut (copié pour cohérence)
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(frm, textvariable=self.status_var, font=("Segoe UI", 9))
        self.status_label.pack(anchor="w", pady=(10, 0))

        # Cadre pour les boutons (copié pour cohérence)
        button_frame = ttk.Frame(frm)
        button_frame.pack(fill="x", pady=(15, 0))

        # Boutons Démarrer, Arrêter, Effacer (layout et style copiés)
        self.btn_start = ttk.Button(button_frame, text="▶ Démarrer l'écoute", command=self.start_decoder, style="TButton")
        self.btn_start.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.btn_stop = ttk.Button(button_frame, text="■ Arrêter l'écoute", state=tk.DISABLED, command=self.stop_decoder, style="TButton")
        self.btn_stop.pack(side='left', fill='x', expand=True, padx=(5, 5))

        self.btn_clear = ttk.Button(button_frame, text="✕ Effacer", command=self.clear_output, style="TButton")
        self.btn_clear.pack(side='left', fill='x', expand=True, padx=(5, 0))

        self.decoder_thread = None
        self.decoder = None

    def clear_output(self, event=None):
        """Efface le contenu de la zone de sortie."""
        if self.decoder and self.decoder.decoding:
             logging.warning("Clear requested while decoding is active.")
             return

        self.text_output.delete('1.0', tk.END)
        if self.status_var: self.status_var.set("")
        logging.info("Output cleared.")

    def start_decoder(self):
        """Démarre le processus de décodage audio dans un thread séparé."""
        if self.decoder_thread and self.decoder_thread.is_alive():
            tk.messagebox.showwarning("En cours", "Un décodage est déjà en cours.")
            return

        self.clear_output()
        mode = 'text' if self.mode_cb.get() == 'Texte' else 'binary'
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.mode_cb.config(state=tk.DISABLED)
        self.transform_cb.config(state=tk.DISABLED)

        self.decoder = AudioDecoder(
            mode,
            output_widget=self.text_output, # self.text_output est le ScrolledText
            on_stop=self.on_decoder_stopped,
            status_var=self.status_var
        )
        self.decoder_thread = self.decoder
        self.decoder_thread.start()

    def stop_decoder(self):
        """Arrête le processus de décodage audio."""
        if self.decoder and self.decoder.is_alive():
            logging.info("Stopping decoder.")
            self.decoder.stop()
            self.btn_stop.config(state=tk.DISABLED)
        elif self.decoder_thread:
             logging.warning("Stop requested but decoder thread is not alive.")
             self.on_decoder_stopped()

    def on_decoder_stopped(self):
        """Fonction de rappel exécutée dans le thread principal Tkinter après l'arrêt du décodeur."""
        logging.info("Decoder thread has stopped. Updating GUI.")
        self.decoder_thread = None
        self.decoder = None
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.mode_cb.config(state='readonly')
        self.transform_cb.config(state='readonly')
        self.post_process_output()

    def post_process_output(self):
        """Applique une transformation (comme ROT13, Inverser, Base64) au texte décodé affiché."""
        transform = self.transform_cb.get()
        content = self.text_output.get('1.0', tk.END).strip()

        decoded_post = content # Initialise avec le contenu original

        if transform == 'ROT13' and content:
             logging.info("Applying ROT13 post-processing.")
             decoded_post = content.translate(str.maketrans(
                 "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                 "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
             ))
        elif transform == 'Inverser' and content:
             logging.info("Applying Reverse post-processing.")
             decoded_post = encode_reverse(content)
        elif transform == 'Base64' and content:
             logging.info("Applying Base64 post-processing.")
             # Base64 decoding is sensitive to input exactness.
             # Errors here often mean the string captured from audio is corrupted.

             decoded_post = f"ERREUR: Impossible de décoder Base64 depuis l'audio." # Message d'erreur par défaut

             # --- Nettoyage de l'entrée ---
             valid_base64_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
             cleaned_content = "".join(c for c in content if c in valid_base64_chars)
             logging.debug(f"Original Base64 input length: {len(content)}, cleaned length: {len(cleaned_content)}. Cleaned content start: {cleaned_content[:50]}...")
             # -----------------------------

             if not cleaned_content:
                 decoded_post = "ERREUR_DECODAGE_BASE64: L'entrée capturée ne contient aucun caractère Base64 valide."
                 logging.warning(decoded_post)
             else:
                 # --- Tentative 1: Décodage standard avec padding ---
                 try:
                     logging.debug("Attempting standard Base64 decode with padding.")
                     # Calculer le padding nécessaire pour que la longueur soit un multiple de 4
                     padding_needed = (4 - len(cleaned_content) % 4) % 4
                     content_padded = cleaned_content + '=' * padding_needed
                     logging.debug(f"Cleaned Base64 content length: {len(cleaned_content)}, padded length: {len(content_padded)}. Padded content start: {content_padded[:50]}...")

                     # Tenter le décodage Base64 standard
                     decoded_bytes = base64.b64decode(content_padded)
                     decoded_post = decoded_bytes.decode('utf-8', errors='replace')
                     logging.info("Base64 standard decoding successful.")

                 # --- Tentative 2: Gérer l'erreur standard (le plus souvent binascii.Error) et essayer une récupération partielle ---
                 except binascii.Error as e:
                     logging.error(f"BinASCII error during standard Base64 decode (after cleaning/padding): {e}. Trying partial decode.", exc_info=True)
                     error_message_standard = f"ERREUR_BASE64 (Format/Padding): {e}"
                     decoded_post = f"{error_message_standard}\n(La chaîne capturée, même nettoyée et paddée, n'est pas du Base64 valide.)" # Message par défaut si la récupération échoue

                     # --- Tentative 2.1: Décodage tronqué ---
                     try:
                         logging.debug("Attempting truncated Base64 decode.")
                         # Calculer la plus grande longueur multiple de 4 inférieure ou égale à la longueur nettoyée
                         truncated_length = len(cleaned_content) // 4 * 4
                         if truncated_length > 0:
                             truncated_content = cleaned_content[:truncated_length]
                             logging.debug(f"Decoding truncated content (length {truncated_length}): {truncated_content[:50]}...")
                             # Décodage de la partie tronquée (aucune padding supplémentaire n'est nécessaire ici)
                             decoded_bytes_truncated = base64.b64decode(truncated_content)
                             decoded_post = decoded_bytes_truncated.decode('utf-8', errors='replace')
                             logging.warning(f"Base64 partial decode successful (truncated to {truncated_length} chars).")
                             # Ajouter une note pour l'utilisateur que c'est un résultat partiel/spéculatif
                             decoded_post += f"\n\n(ATTENTION: Décodage partiel réussi à partir des {truncated_length} premiers caractères. Le reste a été ignoré.)" # Message plus précis
                         else:
                              # Si la longueur nettoyée est < 4, on ne peut pas tronquer utilement
                              logging.warning("Cleaned content length < 4. Cannot attempt truncated decode.")
                              decoded_post = f"{error_message_standard}\n(La chaîne nettoyée est trop courte (<4) pour un décodage Base64, même partiel.)"


                     except binascii.Error as e_truncated:
                          logging.error(f"BinASCII error during truncated Base64 decode: {e_truncated}", exc_info=True)
                          decoded_post = f"{error_message_standard}\n(La tentative de décodage partiel a échoué aussi : {e_truncated})" # Message mis à jour

                     except Exception as e_truncated_general:
                          logging.error(f"General error during truncated Base64 decode: {e_truncated_general}", exc_info=True)
                          decoded_post = f"{error_message_standard}\n(La tentative de décodage partiel a échoué avec une erreur générale : {e_truncated_general})"

                 # --- Gérer les autres exceptions générales pour le décodage standard (moins probable après nettoyage/troncature) ---
                 except Exception as e:
                     logging.error(f"General error during standard Base64 decode (after cleaning): {e}", exc_info=True)
                     decoded_post = f"ERREUR_DECODAGE_BASE64 (Erreur Générale Inattendue): {e}"


        # Ajoute le bloc de résultat transformé si la transformation n'était pas "Aucun" et qu'il y a du contenu original
        # On affiche toujours le résultat du décodage Base64 s'il y avait du contenu initial, même si c'est une erreur ou un résultat partiel.
        if transform != "Aucun" and content:
             # On affiche le résultat transformé si c'est différent de l'original OU si c'est le résultat Base64 (succès, partiel ou erreur)
             # Correction: Utiliser self.text_output pour insert et see
             if decoded_post != content or transform == 'Base64':
                 self.text_output.insert(tk.END, f"\n\n=== Transformé ({transform}) ===\n{decoded_post}")
                 self.text_output.see(tk.END)


# Point d'entrée principal du script : crée la fenêtre Tkinter et lance l'application
if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()