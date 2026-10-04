# EPUB conversion

This first converter accepts an already unpacked EPUB directory, such as an Apple Books `.epub` package. It exports a complete book, individual sections in spine order, an index, image assets, and source metadata. It checks text retention by comparing word counts after conversion to plain text.

Run from `code/`:

```sh
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python convert_epub.py "/path/to/unpacked/book.epub" ../books/book-title
```

The destination must not already exist. Book exports and local environment values are excluded from Git.
