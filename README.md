# pyAVRSimulartor
AVR microcontroller simulator. The GUI is designed to support different AVR
models; the ATmega328P is the only CPU implementation currently available.

## Run the simulator

Launch the Tkinter interface from the repository root:

```powershell
python .\AVRSimulator\AVRSimulator.py
```

The program editor accepts hexadecimal bytes separated by spaces or newlines.
Use `#` for comments. The application starts with an empty editor and CPU.
Choose **File > New Project** to clear the editor and reset the CPU; **Load**
validates and loads the program; **Step** executes one instruction; **Run**
executes until `BREAK`; **Stop** pauses execution; and **Reset** reloads the
current program and clears CPU state. The register view shows R0-R31 in decimal
and hexadecimal.
