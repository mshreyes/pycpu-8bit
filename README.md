# 8-Bit CPU Simulator

An interactive, educational 8-bit Von Neumann CPU simulator and assembler written in Python (`cpu_core.py`) and executed directly in the browser via Pyodide (WebAssembly). 

No backend server or complex installation is required—it runs entirely client-side (thanks to Pyodide).

## Features

- **Step-by-Step Execution**: Watch instructions move through the classic **Fetch → Decode → Execute** cycle in real time.
- **Plain-English Narration**: A live status banner explains every micro-step in everyday language.
- **Interactive Tour & Wiki**: Built-in tabs guide you through how computers work, complete with hoverable `(i)` tooltips and Wikipedia links.
- **Memory & Registers**: Inspect general-purpose registers (`R0`–`R3`), pointers (`PC`, `IR`, `MAR`, `SP`), and the 256-byte RAM grid.

## Repository Files

- `index.html`: The minimalist graphical interface, tabbed views, tour, wiki, and embedded Pyodide runner.
- `cpu_core.py`: The standalone Python 8-bit CPU core and two-pass assembler (can be run directly in the terminal via `python3 cpu_core.py`).

## Local Terminal Usage

You can also run and trace sample programs directly from your command line:

```bash
python3 cpu_core.py