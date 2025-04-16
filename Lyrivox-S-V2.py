import numpy as np
from scipy.io.wavfile import write
import tkinter as tk
import simpleaudio as sa  # pip install simpleaudio si nécessaire

def text_to_freq(text):
    """
    Convertit chaque caractère du texte en une fréquence.
    On part d'une fréquence de base de 1000 Hz et on ajoute 10 fois la valeur ASCII du caractère.
    """
    base_freq = 1000
    return [base_freq + ord(c) * 10 for c in text]

def generate_tone(freqs, duration=0.1, rate=44100):
    """
    Génère un signal audio pour chaque fréquence de la liste 'freqs'.
    Chaque fréquence est émise pendant 'duration' secondes.
    Les ondes sinusoïdales générées sont concaténées en un seul signal.
    """
    audio = np.array([], dtype=np.float32)
    for f in freqs:
        t = np.linspace(0, duration, int(rate * duration), endpoint=False)
        wave = 0.5 * np.sin(2 * np.pi * f * t)
        audio = np.concatenate((audio, wave))
    return audio

def play_sound():
    """
    Fonction principale qui :
    - Récupère le texte entré par l'utilisateur.
    - Calcule pour chaque caractère une fréquence.
    - Affiche les détails (caractère -> fréquence) dans l'interface.
    - Génère le signal sonore et le sauvegarde en format WAV.
    - Joue le son généré.
    """
    text = text_entry.get("1.0", tk.END).strip()
    if not text:
        output_text.set("Veuillez saisir un texte.")
        return

    # Calcul des fréquences
    freqs = text_to_freq(text)

    # Préparation de l'affichage des fréquences
    details = "Détails des fréquences pour chaque caractère:\n"
    for char, f in zip(text, freqs):
        details += f"'{char}' -> {f} Hz\n"
    frequency_details.configure(state=tk.NORMAL)
    frequency_details.delete("1.0", tk.END)
    frequency_details.insert(tk.END, details)
    frequency_details.configure(state=tk.DISABLED)

    # Génération de l'onde sonore et conversion du signal en int16
    sound = generate_tone(freqs)
    audio_data = (sound * 32767).astype(np.int16)

    # Sauvegarde du signal au format WAV
    wav_filename = "IRL.wav"
    write(wav_filename, 44100, audio_data)

    # Lecture du son
    play_obj = sa.play_buffer(audio_data, 1, 2, 44100)
    play_obj.wait_done()

    # Mise à jour de l'interface avec un message de confirmation
    output_text.set(f"Lecture terminée. Fichier sauvegardé : {wav_filename}")

# Création de la fenêtre principale
root = tk.Tk()
root.title("Text To Sound Converter - Format WAV")

# Zone de saisie du texte
label_entry = tk.Label(root, text="Entrez votre texte :", font=("Arial", 12))
label_entry.pack(padx=10, pady=(10, 0))
text_entry = tk.Text(root, height=5, width=50, font=("Arial", 12))
text_entry.pack(padx=10, pady=5)

# Zone d'affichage des détails des fréquences
label_freq = tk.Label(root, text="Détails des fréquences :", font=("Arial", 12))
label_freq.pack(padx=10, pady=(10, 0))
frequency_details = tk.Text(root, height=10, width=50, font=("Arial", 10))
frequency_details.pack(padx=10, pady=5)
frequency_details.configure(state=tk.DISABLED)

# Label pour afficher les messages de confirmation ou d'erreur
output_text = tk.StringVar()
label_output = tk.Label(root, textvariable=output_text, font=("Arial", 12), fg="blue")
label_output.pack(padx=10, pady=5)

# Bouton pour lancer la génération et la lecture
button = tk.Button(root, text="Lancer le son", command=play_sound, font=("Arial", 12))
button.pack(pady=10)

# Boucle principale de l'interface
root.mainloop()
