# books-md

convert an unpacked, drm-free epub into markdown you can give an agent as context to discuss a book and work through its ideas.

## what it creates

- one complete `book.md`
- individual chapters in reading order
- an index linking to each chapter
- image assets and source metadata
- a text-retention check that fails if words are missing after conversion

## quick start

requires python 3 and an unpacked, drm-free epub directory containing `META-INF/container.xml`. if your epub is a zip file, unzip it into a directory first.

```sh
cd code
python3 -m venv ../.venv
../.venv/bin/pip install -r requirements.txt
../.venv/bin/python convert_epub.py "/path/to/unpacked/book.epub" ../books/book-title
```

the output directory must not already exist. pandoc is included through `pypandoc_binary`.

then give your agent `book.md`, or the relevant chapters, as context. ask questions, explore ideas, and discuss how they apply to your own situation. this provides context to the agent; it does not train a new model.

## scope

this is a small personal tool. it converts unpacked epubs; it does not remove drm or convert kindle downloads directly. illustrations stay as images and are not transcribed. text-retention checks do not guarantee perfect formatting or interpretation.

converted books, source ebooks, credentials, and local extraction experiments are excluded from this repository. bring your own book files.

## license

mit; applies to the code in this repository, not to books you convert.
