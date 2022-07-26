# CLI EPUB Reader

## Installation
- Install [`git`](https://git-scm.com/downloads) and [`python2`](https://www.python.org/download/releases/2.0/).
- Install `BeautifulSoup` Python library: `python2 -m pip install bs4`.    
  **Note:** If you are using the pre-installed system Python in a Linux distro, `pip` may not be installed. In that case, you can try to install using your 
  distro's package manager. For example, on Ubuntu, try this: `sudo apt install -y python-bs4`.
- `git clone https://github.com/rupa/epub.git`
- `cd epub`
Now verify the installation by typing `python2 epub.py --help` - it should show [this help text](#advanced-cli-parameters-usage-help).

**Optional:** You can add the path to `epub` directory to your [Environment `PATH`](https://janelbrandon.medium.com/understanding-the-path-variable-6eae0936e976)
so that you can easily use `epub.py` from anywhere.

## Basic Usage
Type `python2 epub.py "<PATH-TO-EPUB-DOCUMENT>"` to open your EPUB document in the terminal. Now you can navigate it using the following key commands:
```
Esc, q: Exit the document
Tab, Left, Right Arrow: to switch between views and chapters
Top: one row up
Down: one line down
Page Up: one page
PgDown: one page down
PgUp: one page up
```

## Advanced CLI Parameters Usage
The following help text can be seen by typing `python2 epub.py --help`:
```
usage: epub [-h] [-d] EPUB

python/curses epub reader. Requires BeautifulSoup

Keyboard commands:
    Esc/q          - quit
    Tab/Left/Right - toggle between TOC and chapter views
    TOC view:
        Up         - up a line
        Down       - down a line
        PgUp       - up a page
        PgDown     - down a page
    Chapter view:
        Up         - up a page
        Down       - down a page
        PgUp       - up a line
        PgDown     - down a line
        

positional arguments:
  EPUB        view EPUB

optional arguments:
  -h, --help  show this help message and exit
  -d, --dump  dump EPUB to text
```
