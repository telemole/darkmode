# Dark Mode Any App (Python)

Save your eyes on apps that have no dark mode!

This is a Windows-specific Python application that provides a per-window color inversion effect. It effectively creates a "dark mode" for applications that lack native support by using the Windows Magnification API (`Magnification.dll`).

## Requirements

- Python 3.x
- Windows OS (Requires Windows Magnification API)
- `keyboard` library (included in `requirements.txt`)

## Installation

1. Clone or download this repository.
2. Open a terminal or command prompt in the project directory.
3. Install the required dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the application script:
   ```bash
   python dark_mode.py
   ```
2. Bring the target application (the one you want to invert colors for) to the foreground.
3. Press `Ctrl+Alt+Q` to toggle the inversion effect on/off for that specific window.

To exit the application and restore all colors, simply press `Ctrl+C` in the terminal where the script is running.
