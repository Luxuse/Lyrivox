import os
import sys
import numpy as np
from scipy.io.wavfile import write
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import subprocess
import traceback
import base64 # Import du module base64

# ---- Fonctions d'encodage ----

def encode_rot13(text):
    """Applique l'encodage ROT13 au texte."""
    return text.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    ))

def encode_reverse(text):
    """Inverse simplement la chaîne."""
    return text[::-1]

def encode_base64(text):
    """Encode le texte en Base64."""
    try:
        # Base64 opère sur des octets, donc on encode d'abord la chaîne en bytes (UTF-8 est courant)
        encoded_bytes = base64.b64encode(text.encode('utf-8'))
        # Decode les bytes résultants en chaîne ASCII
        return encoded_bytes.decode('ascii')
    except Exception as e:
        logging.error(f"Erreur lors de l'encodage Base64 : {e}")
        return f"ERREUR_BASE64:{e}" # Signale une erreur d'encodage

# ---- Mappage Fréquence & Génération Son ----

# Ces paramètres sont configurables dans l'interface du générateur
# Note: Le décodeur a une fréquence de base fixe de 1000 Hz pour le mode texte
# Pour que le décodage fonctionne en mode "Classique", utilisez 1000 Hz ici.
# Pour que le décodage fonctionne avec d'autres encodages, il faudrait un accord sur la base_freq
# ou l'inclure dans le signal ou un en-tête.

def text_to_freq(text, base_freq):
    """Convertit chaque caractère d'un texte en une fréquence basée sur une fréquence de base."""
    # Mappage simple : fréquence de base + valeur ord * 10
    return [base_freq + ord(c)*10 for c in text]

def generate_tone(freqs, duration, rate=44100):
    """Génère une séquence de tons WAV à partir d'une liste de fréquences."""
    if duration <= 0:
         return np.array([])

    note_duration_factor = 0.9
    silence_duration_factor = 1 - note_duration_factor

    note_duration = duration * note_duration_factor
    silence_duration = duration * silence_duration_factor

    all_samples = []

    samples_per_silence = int(rate * silence_duration)
    silence_segment = np.zeros(samples_per_silence)

    samples_per_note = int(rate * note_duration)
    t_note = np.linspace(0, note_duration, samples_per_note, endpoint=False) if samples_per_note > 0 else np.array([])


    for f in freqs:
        if samples_per_note > 0:
            tone = 0.4 * np.sin(2 * np.pi * f * t_note)
            all_samples.append(tone)

        if samples_per_silence > 0:
            all_samples.append(silence_segment)

    if not all_samples:
        return np.array([])

    return np.concatenate(all_samples)


def play_sound():
    """Génère le son basé sur le texte et les paramètres, écrit un fichier WAV et le joue."""
    status_var.set("...")
    try:
        # 1) Récupère le texte et les configurations
        status_var.set("💬 Récupération du texte et des paramètres...")
        text = text_entry.get("1.0", "end").strip()
        if not text:
            status_var.set("❗ Entrez du texte !")
            return

        try:
            # Récupère la fréquence de base et la durée (configurables dans cette version du générateur)
            base_freq = float(base_freq_entry.get())
            note_duration = float(duration_entry.get())
            if base_freq <= 0 or note_duration <= 0:
                 status_var.set("❗ Fréquence de base et durée doivent être positives.")
                 return
        except ValueError:
            status_var.set("❗ Veuillez entrer des nombres valides pour la fréquence et la durée.")
            return


        # 2) Encodage
        status_var.set("🔐 Application de l'encodage...")
        choice = encoding_cb.get()
        if choice == "ROT13":
            encoded = encode_rot13(text)
        elif choice == "Inverser":
             encoded = encode_reverse(text)
        elif choice == "Base64": # Ajout de la gestion Base64
             encoded = encode_base64(text)
             if encoded.startswith("ERREUR_BASE64:"):
                 status_var.set(f"❌ {encoded}")
                 return
        else: # Classique (aucun encodage spécial)
            encoded = text

        if not encoded:
             status_var.set("❗ Le texte encodé est vide.")
             return

        # 3) Affiche les fréquences
        status_var.set("🎶 Calcul des fréquences...")
        # Utilise la fréquence de base configurable
        freqs = text_to_freq(encoded, base_freq)

        freq_box.config(state="normal")
        freq_box.delete("1.0", "end")
        freq_box.insert("end", f"🔄 Encodage : {choice}\n")
        freq_box.insert("end", f"📻 Fréquence de base : {base_freq} Hz\n")
        freq_box.insert("end", f"⏱️ Durée par caractère : {note_duration} s\n\n")

        # Limite l'affichage des fréquences pour les longs textes
        max_display_chars = 200
        display_text = encoded
        display_freqs = freqs
        if len(encoded) > max_display_chars:
             display_text = encoded[:max_display_chars] + "..."
             display_freqs = freqs[:max_display_chars]
             freq_box.insert("end", f"(Affichage limité aux {max_display_chars} premiers caractères)\n\n")

        for ch, f in zip(display_text, display_freqs):
            freq_box.insert("end", f"'{ch}' → {f:.2f} Hz\n")

        freq_box.config(state="disabled")

        # 4) Génère le .wav
        status_var.set("🔊 Génération des données audio...")
        snd = generate_tone(freqs, note_duration)

        if snd.size == 0:
             status_var.set("❗ Pas de données audio générées. Texte trop court ou durée nulle ?")
             return

        # Assurez-vous que les valeurs sont dans la plage int16
        data = (snd * 32767).astype(np.int16)

        fn = f"sound_{choice.replace(' ', '_').replace('/', '_')}.wav" # Nom de fichier plus sûr
        status_var.set(f"💾 Écriture du fichier : {fn}...")
        write(fn, 44100, data)

        # 5) Lance la lecture avec le lecteur système
        status_var.set(f"▶️ Lancement de la lecture système...")
        try:
            if sys.platform.startswith("win"):
                os.startfile(fn)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", fn])
            else:
                subprocess.Popen(["xdg-open", fn])
            status_var.set(f"✅ Fichier généré : {fn} (lecture système lancée)")
        except FileNotFoundError:
             status_var.set(f"⚠️ Impossible de lancer la lecture système. Fichier généré : {fn}")
        except Exception as e:
             status_var.set(f"⚠️ Erreur lors du lancement de la lecture système : {e}. Fichier généré : {fn}")


    except Exception as e:
        traceback.print_exc()
        status_var.set(f"❌ Erreur : {type(e).__name__} - {e}")
        messagebox.showerror("Erreur Générateur", f"Une erreur est survenue : {e}\nVoir la console pour plus de détails.")


def on_click_play():
    # Lance la génération et la lecture dans un thread pour garder la GUI réactive
    threading.Thread(target=play_sound).start()

def clear_text():
    """Efface les zones de texte et de statut."""
    text_entry.delete("1.0", "end")
    freq_box.config(state="normal")
    freq_box.delete("1.0", "end")
    freq_box.insert("end", "Détails des fréquences apparaîtront ici...")
    freq_box.config(state="disabled")
    status_var.set("") # Efface le statut

def on_click_decode():
    """Lance le script de décodage externe."""
    status_var.set("▶️ Lancement de l'outil de décodage externe...")
    decoder_script_name = "decoder.py" # Assurez-vous que ce nom correspond à votre fichier

    # Vérifie si le fichier décodeur existe
    if not os.path.exists(decoder_script_name):
        msg = f"❌ Erreur : Le script du décodeur '{decoder_script_name}' n'a pas été trouvé dans le même répertoire.\nAssurez-vous que '{decoder_script_name}' est bien présent à côté de '{os.path.basename(__file__)}'."
        status_var.set(msg)
        messagebox.showerror("Erreur de lancement", msg)
        return

    try:
        # Lance le décodeur. On pourrait passer des arguments ici si le décodeur
        # était conçu pour les recevoir (par exemple, la base_freq utilisée).
        subprocess.Popen([sys.executable, decoder_script_name])
        status_var.set(f"✅ Outil de décodage externe ({decoder_script_name}) lancé.")
    except Exception as e:
        msg = f"❌ Erreur lors du lancement du décodeur : {type(e).__name__} - {e}"
        status_var.set(msg)
        messagebox.showerror("Erreur de lancement", msg)


# ---- Création de la fenêtre Tkinter ----

root = tk.Tk()
root.title("Lyrivox : V1.5.0") # Version mise à jour
root.configure(bg="#333333")
root.geometry("700x650") # Taille ajustée
root.minsize(600, 500)

# Configuration du Style TTK
style = ttk.Style(root)
style.theme_use("clam")

# Styles personnalisés (copiés pour cohérence)
style.configure("TFrame", background="#333333")
style.configure("TLabel", background="#333333", foreground="#f0f0f0", font=("Segoe UI", 11))
style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8,
                background="#5cb85c", foreground="#ffffff", relief="flat")
style.map("TButton",
          background=[('active', '#4cae4c')],
          foreground=[('disabled', '#777777')])

style.configure("Decode.TButton", background="#f0ad4e", foreground="#ffffff")
style.map("Decode.TButton",
          background=[('active', '#ec971f')])

style.configure("TCombobox", fieldbackground="#444444", background="#444444", foreground="#f0f0f0",
                font=("Segoe UI", 10), relief="flat")
style.map("TCombobox",
          fieldbackground=[('readonly', '#444444')],
          foreground=[('readonly', '#f0f0f0')])

# Style des zones de texte Tkinter (pour Text et ScrolledText)
text_style_options = {
    "bg": "#444444",
    "fg": "#f0f0f0",
    "insertbackground": "#f0f0f0",
    "font": ("Consolas", 10),
    "relief": "flat"
}
# Style des Entry (pour les configurations)
entry_style_options = {
    "bg": "#444444",
    "fg": "#f0f0f0",
    "insertbackground": "#f0f0f0",
    "font": ("Segoe UI", 10),
    "insertbackground": "#f0f0f0", # Added missing insertbackground
    "relief": "flat"
}


frm = ttk.Frame(root, padding=20)
frm.pack(fill="both", expand=True)

# Titre principal
title_label = ttk.Label(frm, text="Lyrivox", font=("Segoe UI", 15, "bold"))
title_label.pack(anchor="center", pady=(0, 15))

# Zone d'entrée de texte
ttk.Label(frm, text="Entrez votre texte :").pack(anchor="w", pady=(0, 5))
text_entry = tk.Text(frm, height=5, wrap="word", **text_style_options)
text_entry.pack(fill="x", pady=(0, 10))

# Cadre pour les options d'encodage et de configuration
options_frame = ttk.Frame(frm)
options_frame.pack(fill="x", pady=(0, 10))

# Sélection du type d'encodage (colonne 0)
encoding_frame = ttk.Frame(options_frame)
encoding_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
ttk.Label(encoding_frame, text="Type d'encodage :").pack(anchor="w", pady=(0, 5))
# Ajout de "Base64" aux options
encoding_cb = ttk.Combobox(encoding_frame, values=["Classique", "ROT13", "Inverser", "Base64"], state="readonly", width=15)
encoding_cb.current(0)
encoding_cb.pack(fill="x")

# Options de configuration (colonne 1) - Fréquence de base et Durée sont configurables ici
config_frame = ttk.Frame(options_frame)
config_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))

# Fréquence de base
base_freq_frame = ttk.Frame(config_frame)
base_freq_frame.pack(fill="x", pady=(0, 5))
ttk.Label(base_freq_frame, text="Fréquence de base (Hz) :").pack(side="left", padx=(0, 5))
base_freq_entry = tk.Entry(base_freq_frame, width=10, **entry_style_options)
# Valeur par défaut 1000 pour correspondre au décodeur par défaut
base_freq_entry.insert(0, "1000")
base_freq_entry.pack(side="left", fill="x", expand=True)

# Durée par caractère
duration_frame = ttk.Frame(config_frame)
duration_frame.pack(fill="x", pady=(0, 5))
ttk.Label(duration_frame, text="Durée par caractère (s) :").pack(side="left", padx=(0, 5))
duration_entry = tk.Entry(duration_frame, width=10, **entry_style_options)
duration_entry.insert(0, "0.1") # Valeur par défaut
duration_entry.pack(side="left", fill="x", expand=True)


# Zone d'affichage des fréquences (similaire à la sortie du décodeur)
ttk.Label(frm, text="Détails des fréquences générées :").pack(anchor="w", pady=(0, 5))
freq_box = ScrolledText(frm, height=12, **text_style_options) # Hauteur ajustée
freq_box.pack(fill="both", expand=True, pady=(0, 10)) # Padding ajusté
freq_box.insert("end", "Détails des fréquences apparaîtront ici...")
freq_box.config(state="disabled")


# Label de statut (copié pour cohérence)
status_var = tk.StringVar()
status_label = ttk.Label(frm, textvariable=status_var, font=("Segoe UI", 9)) # Police ajustée
status_label.pack(anchor="w", pady=(10, 0))

# Cadre pour les boutons (copié pour cohérence)
button_frame = ttk.Frame(frm)
button_frame.pack(fill="x", pady=(15, 0))

# Boutons Générer/Jouer, Effacer, Décoder (layout et style copiés)
run_btn = ttk.Button(button_frame, text="▶ Générer et Jouer le Son", command=on_click_play, style="TButton")
run_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

clear_btn = ttk.Button(button_frame, text="✕ Effacer", command=clear_text, style="TButton")
clear_btn.pack(side="left", fill="x", expand=True, padx=(5, 5))

decode_btn = ttk.Button(button_frame, text="🔍 Décoder (Externe)", command=on_click_decode, style="Decode.TButton")
decode_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))


root.mainloop()