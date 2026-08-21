import zipfile
from pathlib import Path
import fitz
from app.ingestion import extract_book

def make_pdf(path: Path):
    doc=fitz.open()
    for title,body in [("Chapter 1 — Foundations","First paragraph. "*25),("Chapter 2 — Retrieval","Second paragraph. "*25)]:
        page=doc.new_page();page.insert_text((72,72),title,fontsize=20);page.insert_textbox((72,110,520,740),body,fontsize=11)
    doc.save(path);doc.close()

def make_epub(path: Path):
    files={"META-INF/container.xml":'''<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>''',"OEBPS/content.opf":'''<package xmlns="http://www.idpf.org/2007/opf"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Fixture Book</dc:title><dc:creator>Test Author</dc:creator></metadata><manifest><item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/><item id="c2" href="chapter2.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>''',"OEBPS/chapter1.xhtml":'<html><body><h1>Chapter One</h1><p>Alpha paragraph.</p><h2>Section A</h2><p>More knowledge.</p></body></html>',"OEBPS/chapter2.xhtml":'<html><body><h1>Chapter Two</h1><p>Beta paragraph.</p></body></html>'}
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
        for n,t in files.items():z.writestr(n,t)

def test_pdf_extraction(tmp_path):
    p=tmp_path/'book.pdf';make_pdf(p);text,blocks,count,meta,chapters,sections,chunks=extract_book(p)
    assert count==2 and 'Chapter 1' in text and len(chapters)>=2 and chunks[0].page_start==1

def test_epub_extraction(tmp_path):
    p=tmp_path/'book.epub';make_epub(p);text,blocks,count,meta,chapters,sections,chunks=extract_book(p)
    assert meta['title']=='Fixture Book' and meta['author']=='Test Author' and 'Alpha paragraph.' in text and len(chapters)==2 and any(s.title=='Section A' for s in sections)
