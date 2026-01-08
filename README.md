
# 📺 YouTube AI Briefing Bot

Ein automatisierter Python-Bot, der deine abonnierten YouTube-Kanäle überwacht, die Inhalte neuer Videos mittels **Google Gemini AI** analysiert und dir eine strukturierte Zusammenfassung per E-Mail sendet. Optional können Audio-Zusammenfassungen (TTS) generiert und angehängt werden.

## ✨ Features

*   **RSS-Überwachung:** Nutzt leichtgewichtige RSS-Feeds statt der komplexen YouTube Data API (spart API-Quota).
*   **KI-Analyse:** Verwendet Google Gemini (via `google-generativeai`), um Transkripte zu analysieren.
*   **Individuelle Prompts:** Definiere für jeden Kanal eigene Analyse-Instruktionen (z.B. "Fasse technische Details zusammen" vs. "Analysiere Finanz-Tipps").
*   **Audio-Feature (TTS):** Generiert auf Wunsch MP3-Zusammenfassungen für unterwegs (via `gTTS`).
*   **Smart History:** Speichert verarbeitete Videos lokal (`seen_videos.txt`), um Duplikate zu vermeiden.
*   **Sicher:** Sensible Daten (Passwörter, API-Keys) werden über Umgebungsvariablen (`.env`) verwaltet.

## 🚀 Installation

### 1. Repository klonen
```bash
git clone https://github.com/bluechip0815/https://github.com/bluechip0815/NewsLogger.git.git
cd NewsLogger
```

### 2. Abhängigkeiten installieren
Es wird empfohlen, ein virtuelles Environment zu nutzen.

```bash
# Optional: Virtual Environment erstellen
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Pakete installieren
pip install google-generativeai youtube-transcript-api feedparser gTTS python-dotenv
```

## ⚙️ Konfiguration

Das Projekt benötigt drei Konfigurationsdateien im Hauptverzeichnis.

### 1. `.env` (Secrets)
Erstelle eine Datei namens `.env` für deine Zugangsdaten. Diese Datei darf **nicht** auf GitHub hochgeladen werden (sie steht normalerweise in der `.gitignore`).

```env
GEMINI_API_KEY=Dein_Google_Gemini_Key
EMAIL_PASSWORD=Dein_App_Passwort_für_Email
```
*   **Gemini Key:** Erhältlich im [Google AI Studio](https://aistudio.google.com/).
*   **Email Passwort:** Bei Gmail musst du oft ein "App-Passwort" erstellen, wenn 2FA aktiviert ist.

### 2. `general_config.json` (Einstellungen)
Allgemeine Settings für Mail-Server und KI.

```json
{
  "project_name": "Daily YouTube AI Briefing",
  "email_settings": {
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "deine.email@gmail.com",
    "receiver": "empfaenger.email@example.com"
  },
  "ai_settings": {
    "model": "gemini-1.5-flash"
  },
  "working_options": {
    "max_videos_per_channel": 3,
    "enable_tts": true,
    "tts_lang": "de"
  }
}
```

### 3. `project_config.json` (Kanäle)
Hier definierst du, welche Kanäle überwacht werden sollen.

```json
{
  "subscriptions": [
    {
      "channel_name": "Tech News",
      "channel_id": "UCxxxxxxxxxxxx", 
      "analysis_prompt": "Fasse die Hardware-Neuerungen kurz zusammen."
    },
    {
      "channel_name": "Finanzen",
      "channel_id": "UCyyyyyyyyyyyy",
      "analysis_prompt": "Welche Aktien werden empfohlen? Liste Pro und Contra."
    }
  ]
}
```

#### 💡 Tipp: Channel ID finden
Die `channel_id` beginnt meist mit `UC`.
*   Gehe auf die YouTube-Kanalseite.
*   Rechtsklick -> "Seitenquelltext anzeigen".
*   Suche (Strg+F) nach `channel_id` oder `externalId`.
*   Alternativ nutze Online-Tools wie "YouTube Channel ID Finder".

## ▶️ Nutzung

Führe das Skript einfach manuell aus:

```bash
python main.py
```

Das Skript wird:
1.  Die RSS-Feeds der konfigurierten Kanäle prüfen.
2.  Neue Videos mit der `seen_videos.txt` abgleichen.
3.  Transkripte ziehen und an Gemini senden.
4.  Eine HTML-Email mit den Ergebnissen senden.

## 🤖 Automatisierung

Damit der Bot regelmäßig läuft, richte einen Cronjob oder Task ein.

**Linux / Mac (Crontab):**
Führt das Skript alle 4 Stunden aus.
```bash
0 */4 * * * /pfad/zum/venv/bin/python /pfad/zum/projekt/main.py >> /pfad/zum/projekt/logfile.log 2>&1
```

**Windows (Aufgabenplanung):**
*   Erstelle eine neue Aufgabe.
*   Trigger: Täglich / Alle X Stunden.
*   Aktion: Programm starten -> Pfad zu deiner `python.exe` (im venv), Argument: `main.py`.

## ⚠️ Hinweise & Limits

*   **Kein Transkript:** Wenn ein Video keine Untertitel (CC) hat, wird es übersprungen.
*   **API Kosten:** Gemini 1.5 Flash hat ein großzügiges kostenloses Tier, beachte aber die Limits bei sehr vielen Videos.
*   **Email:** Google blockiert manchmal SMTP-Zugriffe von "weniger sicheren Apps". Nutze App-Passwörter.

## 📄 Lizenz

Dieses Projekt ist unter der MIT Lizenz veröffentlicht. Feel free to fork!