
# Video Player with Interactive Graphs

Questa applicazione è un video player avanzato con grafici interattivi che permette di visualizzare dati sincronizzati da sensori insieme al video, con funzionalità aggiuntive per il controllo della riproduzione e l'analisi dei dati.

## Caratteristiche

- **Sincronizzazione Video-Dati**: Visualizza dati provenienti da file CSV in tempo reale accanto al video.
- **Tema Chiaro e Scuro**: Possibilità di passare dal tema chiaro a quello scuro.
- **Salvataggio dello Stato**: Memorizza l'ultima cartella aperta e le impostazioni dell'utente.
- **Icona Personalizzata**: Mostra un'icona personalizzata nella barra delle applicazioni.
- **Eseguibile Standalone**: Possibilità di creare un eseguibile standalone con un'icona personalizzata.

## Requisiti

- Python 3.x
- pip per la gestione dei pacchetti

## Installazione

1. **Clona il repository**

   ```bash
   git clone https://github.com/FrancescoMinisini/Sensoria.git
   cd tuo-repository
2. **Crea un ambiente virtuale (opzionale ma consigliato)**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
3. **Installa le dipendenze**
   Assicurati di avere un file requirements.txt con tutte le librerie necessarie:
   
   ```plaintext
   PyQt5
   pandas
   numpy
   pyqtgraph
   opencv-python
   platformdirs
   pyinstaller
Poi esegui:   
   ```bash
   pip install -r requirements.txt 
   ```


4. **Creazione dell'Eseguibile**
Per creare un eseguibile standalone della tua applicazione:

Assicurati di avere PyInstaller installato

   ```bash
   pip install pyinstaller
   ```
Verifica che il tuo file icona sia nella directory principale

L'icona dovrebbe essere in formato .ico (per Windows) o .icns (per macOS).
Nome del file: app_icon.ico
Crea l'eseguibile

Esegui il seguente comando:

   ```bash
   pyinstaller --onefile --windowed --icon=app_icon.ico main.py
   ```
   Questo creerà una cartella dist contenente l'eseguibile main.exe (su Windows) o main (su macOS/Linux).
   Esegui l'applicazione

   Su Windows:

   ```bash
      dist\main.exe
   ```
Su macOS/Linux:

   ```bash
      ./dist/main
   ```

5. **Creazione di un Collegamento sul Desktop**

Per creare un collegamento sul desktop:

5.1. **Windows:**

- Vai alla cartella dist.
- Fai clic con il tasto destro su main.exe e seleziona Crea collegamento.
- Trascina il collegamento sul desktop.
- Puoi rinominare il collegamento e assegnare l'icona personalizzata se non è già impostata.

5.2. **MacOS:**
- Trascina l'eseguibile nella cartella Applicazioni.
- Puoi creare un alias (collegamento) e posizionarlo sul desktop.
- Esecuzione dell'Applicazione
- Dopo aver creato l'eseguibile, puoi avviare l'applicazione semplicemente facendo doppio clic sull'eseguibile o sul collegamento che hai creato.

**Uso**:
- Aprire una Cartella: Usa il menu File > Apri per selezionare una cartella contenente un file video e due file CSV. Questi verranno caricati e visualizzati nell'applicazione.
- Sincronizzazione: Puoi sincronizzare i dati con il video per visualizzare i grafici interattivi in tempo reale.
- Tema Chiaro/Scuro: Cambia il tema dell'applicazione dal menu Opzioni > Tema Scuro/Chiaro.
- Reset delle Impostazioni: Se necessario, puoi reimpostare tutte le impostazioni predefinite dal menu Opzioni > Reimposta Impostazioni Predefinite.

**Struttura dei File**
- main.py: File principale per l'esecuzione dell'applicazione.
- app_icon.ico: Icona dell'applicazione utilizzata per l'eseguibile.
- assets/: (Facoltativo) Cartella per altre risorse come immagini o file aggiuntivi.
- requirements.txt: File con tutte le dipendenze necessarie.

**Problemi Comuni**
- Problema con le Dipendenze: Se incontri errori durante l'installazione delle dipendenze, verifica di avere l'ultima versione di pip installata. Usa python -m pip install --upgrade pip per aggiornare.
- Errore di Caricamento Video: Assicurati che il file video sia in un formato supportato (come .mp4, .avi, o .mov).
- File Mancanti: La cartella selezionata deve contenere esattamente un file video e due file CSV per funzionare correttamente.
- Eseguibile non Funzionante: Assicurati di aver eseguito PyInstaller con i parametri corretti e che tutte le dipendenze siano installate.

**Contatti:**
Per domande o assistenza, contatta Francesco Giuseppe Minisini a fg.minisini@gmail.com.