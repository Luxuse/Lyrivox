import os
import sys
import numpy as np
from scipy.io.wavfile import write
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading
import subprocess


def encode_rot13(text):
    return text.translate(str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    ))

# ---- Génération des sons ----

def text_to_freq(text):
    base_freq = 1000
    return [base_freq + ord(c)*10 for c in text]

def generate_tone(freqs, duration=0.1, rate=44100):
    return np.concatenate([
        0.5 * np.sin(2*np.pi*f*np.linspace(0, duration, int(rate*duration), endpoint=False))
        for f in freqs
    ])

def play_sound():
    try:
        # 1) Récupère le texte
        text = text_entry.get("1.0", "end").strip()
        if not text:
            status_var.set("❗ Entrez du texte !")
            return

        # 2) Encodage
        choice = encoding_cb.get()
        if choice == "ROT13":
            encoded = encode_rot13(text)
        else:
            encoded = text

        # 3) Affiche les fréquences
        freqs = text_to_freq(encoded)
        freq_box.config(state="normal")
        freq_box.delete("1.0", "end")
        freq_box.insert("end", f"🔄 Encodage : {choice}\n\n")
        for ch, f in zip(encoded, freqs):
            freq_box.insert("end", f"'{ch}' → {f} Hz\n")
        freq_box.config(state="disabled")

        # 4) Génère le .wav
        snd = generate_tone(freqs)
        data = (snd * 32767).astype(np.int16)
        fn = f"sound_{choice}.wav"
        write(fn, 44100, data)

        # 5) Lance la lecture avec le lecteur système
        if sys.platform.startswith("win"):
            os.startfile(fn)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", fn])
        else:
            subprocess.Popen(["xdg-open", fn])

        status_var.set(f"✔ Fichier généré : {fn} (lecture système lancée)")

    except Exception as e:
        status_var.set(f"❌ Erreur : {e}")

def on_click_play():
    # thread non-daemon : la GUI reste ouverte
    threading.Thread(target=play_sound).start()

# ---- Création de la fenêtre Tkinter ----

root = tk.Tk()
root.title("Lyrivox • 1.4.0")
root.configure(bg="#333333")  # Darker background
root.geometry("650x650")
root.minsize(550, 450)

style = ttk.Style(root)
style.theme_use("clam")

# Style des cadres
style.configure("TFrame", background="#333333")

# Style des labels
style.configure("TLabel", background="#333333", foreground="#f0f0f0", font=("Segoe UI", 12))

# Style des boutons
style.configure("TButton", font=("Segoe UI", 12, "bold"), padding=10,
                background="#5cb85c", foreground="#ffffff", relief="flat")
style.map("TButton",
          background=[('active', '#4cae4c')],
          foreground=[('disabled', '#777777')])

# Style des combobox
style.configure("TCombobox", fieldbackground="#444444", background="#444444", foreground="#f0f0f0",
                font=("Segoe UI", 11), relief="flat")
style.map("TCombobox",
          fieldbackground=[('readonly', '#444444')],
          foreground=[('readonly', '#f0f0f0')])

# Style des zones de texte
style.configure("TText", background="#444444", foreground="#f0f0f0", insertbackground="#f0f0f0",
                font=("Consolas", 11), relief="flat")

# Style des ScrolledText
style.configure("TScrolledText.TFrame", background="#444444")
style.configure("TScrolledText.Vertical.TScrollbar", background="#555555", troughcolor="#333333", borderwidth=0)

frm = ttk.Frame(root, padding=25)
frm.pack(fill="both", expand=True)

# Titre principal
title_label = ttk.Label(frm, text="Générateur de Sons Textuels", font=("Segoe UI", 16, "bold"))
title_label.pack(anchor="center", pady=(0, 20))

# Zone d'entrée de texte
ttk.Label(frm, text="Entrez votre texte :").pack(anchor="w", pady=(0, 5))
text_entry = tk.Text(frm, height=5, wrap="word", font=("Consolas", 11),
                    bg="#444444", fg="#f0f0f0", insertbackground="#f0f0f0", relief="flat")
text_entry.pack(fill="x", pady=(0, 15))

# Sélection du type d'encodage
ttk.Label(frm, text="Type d'encodage :").pack(anchor="w", pady=(0, 5))
encoding_cb = ttk.Combobox(frm, values=["Classique", "ROT13"], state="readonly", width=15)
encoding_cb.current(0)
encoding_cb.pack(fill="x", pady=(0, 15))

# Zone d'affichage des fréquences
ttk.Label(frm, text="Détails des fréquences :").pack(anchor="w", pady=(0, 5))
freq_box = ScrolledText(frm, height=10, font=("Consolas", 11),
                        bg="#444444", fg="#f0f0f0", insertbackground="#f0f0f0", relief="flat")
freq_box.pack(fill="both", expand=True, pady=(0, 15))
freq_box.config(state="disabled")

# Label de statut
status_var = tk.StringVar()
status_label = ttk.Label(frm, textvariable=status_var, font=("Segoe UI", 10))
status_label.pack(anchor="w", pady=(10, 0))

# Bouton de lancement
run_btn = ttk.Button(frm, text="▶ Générer et Jouer le Son", command=on_click_play)
run_btn.pack(fill="x", pady=(15, 0))

root.mainloop()