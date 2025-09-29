# File Organizer - Professional Edition (PyQt6)

A powerful and user-friendly desktop application to automatically organize files into categorized folders.  
**Built with Python and PyQt6.**

![Version](https://img.shields.io/badge/version-2.0-blue.svg)  
![Python](https://img.shields.io/badge/python-3.8+-green.svg)  
![License](https://img.shields.io/badge/license-MIT-orange.svg)

---

## Features (PyQt6)

- **Automatic File Organization**: Intelligently sorts files by type into designated folders  
- **Multiple Categories**: Pre-configured for documents, images, videos, audio, archives, code, spreadsheets, presentations, and executables  
- **Custom Categories**: Create your own categories with custom extensions and folder names  
- **Dry Run Mode**: Preview changes before moving files  
- **Real-time Progress**: Visual progress bar and detailed logging  
- **Multi-threaded**: Non-blocking UI with background processing  
- **Category Management**: Enable/disable categories and track file counts  
- **Safe File Handling**: Automatic duplicate detection and renaming  
- **Cross-platform**: Works on Windows, macOS, and Linux  

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Clone the Repository
```bash
git clone https://github.com/yourusername/file-organizer.git
cd file-organizer
```

### Install Dependencies
```bash
pip install PyQt6
```

---

## Usage (PyQt6)

Run the application:
```bash
python file.py
```

### Basic Workflow
1. Select **Source Directory** (files to organize)  
2. Select **Destination Directory** (optional, defaults to "Organized" folder)  
3. Preview with **Dry Run**  
4. Click **Organize Files**  
5. View results summary and detailed logs  

### Managing Categories
- Go to the **Manage Categories** tab  
- Enable/disable categories with checkboxes  
- Add custom categories  
- View file counts after organizing  

---

## Default Categories

| Category      | Extensions                                   | Folder Name   |
|---------------|----------------------------------------------|---------------|
| Documents     | .pdf, .doc, .docx, .txt, .rtf, .odt          | Documents     |
| Images        | .jpg, .jpeg, .png, .gif, .bmp, .svg, .tiff   | Images        |
| Videos        | .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm    | Videos        |
| Audio         | .mp3, .wav, .flac, .aac, .ogg, .wma          | Audio         |
| Archives      | .zip, .rar, .7z, .tar, .gz, .bz2             | Archives      |
| Code          | .py, .js, .html, .css, .cpp, .java, .php     | Code          |
| Spreadsheets  | .xlsx, .xls, .csv, .ods                      | Spreadsheets  |
| Presentations | .ppt, .pptx, .odp                            | Presentations |
| Executables   | .exe, .msi, .deb, .dmg, .app                 | Executables   |

---

## Building Executable (PyQt6)

### Using PyInstaller
```bash
pip install pyinstaller

# Basic build
pyinstaller --onefile --windowed file.py

# With custom name and icon
pyinstaller --onefile --windowed --name "FileOrganizer" --icon=icon.ico file.py
```

Find the executable inside the `dist/` folder.

### Using Auto-py-to-exe (GUI)
```bash
pip install auto-py-to-exe
auto-py-to-exe
```

---

## Project Structure
```
file-organizer/
│
├── file.py                 # PyQt6 version (Main)
├── README.md
├── requirements.txt
├── LICENSE
│
├── screenshots/
│   ├── main.png
│   ├── categories.png
│   └── logs.png
│
└── dist/                   # Executable output
    └── FileOrganizer.exe
```

---

## Requirements (PyQt6)
```
PyQt6>=6.0.0
```

---

## Troubleshooting (PyQt6)

### "No module named 'PyQt6'"
```bash
pip install PyQt6
```

### "Permission Denied"
- Run with proper permissions  
- Ensure destination folder is writable  

### Files Not Moving
- Verify source directory exists  
- Check file permissions  
- Review logs tab  

### Executable Not Opening
- Run from command line for errors  
- Bundle dependencies (`--onefile`)  
- Check antivirus software  

---

## Roadmap (Upcoming PyQt6 Features)
- Undo functionality  
- File filtering (date, size)  
- Scheduled organization  
- Cloud storage integration  
- Duplicate detection  
- Batch operations  
- Config file support  
- Multi-language support  

---

## License
MIT License – see [LICENSE](LICENSE).
