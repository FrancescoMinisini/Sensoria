Ecco il file `README.md` completo, scritto interamente in Markdown:

# Video Player with Interactive Graphs

Questa applicazione è un video player avanzato con grafici interattivi che permette di visualizzare dati sincronizzati da sensori insieme al video, con funzionalità aggiuntive per il controllo della riproduzione e l'analisi dei dati.

## Caratteristiche

- **Sincronizzazione Video-Dati**: Visualizza dati provenienti da file CSV in tempo reale accanto al video.
- **Tema Chiaro e Scuro**: Possibilità di passare dal tema chiaro a quello scuro.
- **Salvataggio dello Stato**: Memorizza l'ultima cartella aperta e le impostazioni dell'utente.
- **Icona Personalizzata**: Mostra un'icona personalizzata nella barra delle applicazioni.

## Requisiti

- Python 3.x
- `pip` per la gestione dei pacchetti

## Installazione

1. **Clona il repository**

   ```bash
   git clone https://github.com/tuo-username/tuo-repository.git
   cd tuo-repository
   ```

2. **Crea un ambiente virtuale (opzionale ma consigliato)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```

3. **Installa `pip` se non è già installato**

   ```bash
   python -m ensurepip --upgrade
   ```

4. **Installa le dipendenze**

   Assicurati di avere un file `requirements.txt` con tutte le librerie necessarie. Ecco un esempio delle librerie principali usate:

   ```plaintext
   PyQt5
   opencv-python
   numpy
   pandas
   pyqtgraph
   pillow
   ```

   Poi esegui:

   ```bash
   pip install -r requirements.txt
   ```

## Esecuzione dell'applicazione

Dopo aver installato tutte le dipendenze, puoi avviare l'applicazione con il seguente comando:

```bash
python main.py
```

## Uso

- **Aprire una Cartella**: Usa il menu `File > Apri` per selezionare una cartella contenente un file video e due file CSV. Questi verranno caricati e visualizzati nell'applicazione.
- **Sincronizzazione**: Puoi sincronizzare i dati con il video per visualizzare i grafici interattivi in tempo reale.
- **Tema Chiaro/Scuro**: Cambia il tema dell'applicazione dal menu `Opzioni > Tema Scuro/Chiaro`.
- **Reset delle Impostazioni**: Se necessario, puoi reimpostare tutte le impostazioni predefinite dal menu `Opzioni > Reimposta Impostazioni Predefinite`.

## Struttura dei File

- **`main.py`**: File principale per l'esecuzione dell'applicazione.
- **`.video_player_app/`**: Cartella creata nella home dell'utente per contenere la configurazione e l'icona dell'applicazione.
  - **`config.json`**: File di configurazione per memorizzare l'ultima cartella aperta e altre impostazioni.
  - **`app_icon.png`**: Icona dell'applicazione che appare nella barra delle applicazioni.

## Problemi Comuni

- **Problema con le Dipendenze**: Se incontri errori durante l'installazione delle dipendenze, verifica di avere l'ultima versione di `pip` installata. Usa `python -m pip install --upgrade pip` per aggiornare.
- **Errore di Caricamento Video**: Assicurati che il file video sia in un formato supportato (come `.mp4`, `.avi`, o `.mov`).
- **File Mancanti**: La cartella selezionata deve contenere esattamente un file video e due file CSV per funzionare correttamente.

## Contatti

Per domande o assistenza, contatta [il tuo nome] a [tuo.email@example.com].
```

Assicurati di aggiungere il file `requirements.txt` e di sostituire l'URL del repository e i dettagli di contatto con i tuoi dati.