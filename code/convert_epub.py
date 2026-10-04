"""Convert an unpacked EPUB directory to chapter and combined Markdown files."""
import argparse
import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import pypandoc


def convert(source, output):
    source = source.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    container = ET.parse(source / "META-INF/container.xml")
    package_path = next(e.attrib["full-path"] for e in container.iter()
                        if e.tag.endswith("rootfile"))
    package = source / package_path
    root = ET.parse(package).getroot()
    ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
    metadata = root.find("opf:metadata", ns)
    title = metadata.findtext("dc:title", namespaces=ns)
    author = metadata.findtext("dc:creator", namespaces=ns)
    manifest = {e.attrib["id"]: e for e in root.find("opf:manifest", ns)}
    paths = [(package.parent / unquote(manifest[e.attrib["idref"]].attrib["href"])).resolve()
             for e in root.find("opf:spine", ns)]
    sections = []
    for i, path in enumerate(paths):
        soup = BeautifulSoup(path.read_text(), "html.parser")
        heading = soup.find(re.compile(r"^h[1-6]$")) or soup.find("title")
        name = heading.get_text(" ", strip=True) if heading else path.stem
        slug = re.sub(r"[^a-z0-9]+", "-", path.parent.name.lower()).strip("-")
        if path.name == "toc.xhtml":
            slug = "contents"
        sections.append({"path": path, "soup": soup, "title": name,
                         "file": f"{i:02d}-{slug}.md", "anchor": f"section-{i:02d}"})
    by_path = {s["path"]: s for s in sections}
    (output / "chapters").mkdir(parents=True)
    asset_paths = {}
    for item in manifest.values():
        if item.attrib["media-type"].startswith("image/"):
            path = (package.parent / unquote(item.attrib["href"])).resolve()
            relative = path.relative_to(package.parent)
            dest = output / "assets" / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            asset_paths[path] = "assets/" + relative.as_posix()
    combined = [f"# {title}\n\nBy {author}\n"]
    report = []
    for s in sections:
        chapter_results = {}
        for mode in ("chapter", "book"):
            body = copy.deepcopy(s["soup"].body)
            for el in list(body.find_all(True)):
                ident = el.get("id")
                if ident:
                    anchor = BeautifulSoup("", "html.parser").new_tag("a")
                    anchor["id"] = s["anchor"] + "-" + ident
                    el.insert_before(anchor)
                # Remove layout attributes, keeping semantic content and links.
                el.attrs = {k: v for k, v in el.attrs.items()
                            if k in ("href", "src", "alt", "colspan", "rowspan")}
                if el.name == "img":
                    target = (s["path"].parent / unquote(el.get("src", ""))).resolve()
                    if target not in asset_paths:
                        raise ValueError(f"Missing image: {target}")
                    el["src"] = ("../" if mode == "chapter" else "") + asset_paths[target]
                if el.name == "a" and el.get("href"):
                    link = urlsplit(el["href"])
                    if not link.scheme and not link.netloc:
                        target = (s["path"].parent / unquote(link.path)).resolve() if link.path else s["path"]
                        if target in by_path:
                            dest = by_path[target]
                            fragment = dest["anchor"] + "-" + unquote(link.fragment) if link.fragment else dest["anchor"]
                            el["href"] = (dest["file"] if mode == "chapter" else "") + "#" + fragment
                        else:
                            raise ValueError(f"Unresolved local link: {el['href']}")
            # Unwrap presentation containers so Markdown does not retain layout HTML.
            for el in list(body.find_all(["div", "span", "main", "section", "article", "nav", "figure"])):
                el.unwrap()
            for el in body.find_all("figcaption"):
                el.name = "p"
            html = str(body)
            result = pypandoc.convert_text(html, "gfm", format="html", extra_args=["--wrap=none"])
            if not result.strip():
                raise ValueError(f"Empty conversion: {s['path']}")
            chapter_results[mode] = f'<a id="{s["anchor"]}"></a>\n\n' + result
        (output / "chapters" / s["file"]).write_text(chapter_results["chapter"])
        combined.append(chapter_results["book"])
        # Round-trip through plain text to check retained words, ignoring markup.
        original_plain = pypandoc.convert_text(str(s["soup"].body), "plain", format="html")
        rendered_html = pypandoc.convert_text(chapter_results["book"], "html", format="gfm")
        converted_plain = pypandoc.convert_text(rendered_html, "plain", format="html")
        words = lambda t: re.findall(r"\w+", t.casefold())
        from collections import Counter
        missing = Counter(words(original_plain)) - Counter(words(converted_plain))
        if missing:
            raise ValueError(f"Text verification failed in {s['file']}: {dict(missing)}")
        report.append({"file": "chapters/" + s["file"], "title": s["title"],
                       "source": str(s["path"].relative_to(source)),
                       "source_sha256": hashlib.sha256(s["path"].read_bytes()).hexdigest(),
                       "words": len(words(original_plain)), "text_verified": True})
    (output / "book.md").write_text("\n\n---\n\n".join(combined))
    index = f"# {title}\n\nBy {author}\n\n[Complete book](book.md)\n\n"
    index += "\n".join(f'- [{s["title"]}](chapters/{s["file"]})' for s in sections)
    index += "\n\nConverted from the local EPUB in its spine reading order. This is source text, not an AI summary. Illustrations remain image files; their contents have not been transcribed.\n"
    (output / "README.md").write_text(index)
    (output / "metadata.json").write_text(json.dumps({"title": title, "author": author,
        "source": str(source), "converter": "Pandoc " + str(pypandoc.get_pandoc_version()),
        "sections": report, "images": len(asset_paths)}, indent=2) + "\n")
    print(json.dumps({"output": str(output), "sections": len(sections),
                      "images": len(asset_paths), "words": sum(s["words"] for s in report)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    convert(args.source, args.output)
