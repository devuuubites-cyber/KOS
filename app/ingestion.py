from __future__ import annotations
import html
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
import fitz
from bs4 import BeautifulSoup
from pypdf import PdfReader
from .models import Chunk, Section

@dataclass
class TextBlock:
    text: str
    page: int | None
    level: int = 0
    heading: bool = False
    font_size: float | None = None

def _clean_text(text: str) -> str:
    text = html.unescape(text).replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _is_heading_candidate(text: str, size: float, body_size: float, page_height: float, y0: float) -> bool:
    t = text.strip()
    if not t or len(t) > 180 or len(t.split()) > 24: return False
    numbered = bool(re.match(r"^(chapter|part|section)\s+([0-9ivxlcdm]+|[a-z])\b", t, re.I))
    title_like = t[:1].isupper() and not t.endswith((".", ",", ";", ":"))
    large = size >= max(body_size * 1.22, body_size + 1.5)
    return numbered or (large and title_like)

def extract_pdf(path: Path):
    blocks=[]; doc=fitz.open(path)
    try:
        for page_index,page in enumerate(doc):
            data=page.get_text("dict"); sizes=[float(s.get("size",10)) for b in data.get("blocks",[]) if b.get("type")==0 for l in b.get("lines",[]) for s in l.get("spans",[]) if s.get("text","").strip()]
            body_size=sorted(sizes)[len(sizes)//2] if sizes else 10.0
            for b in data.get("blocks",[]):
                if b.get("type")!=0: continue
                for line in b.get("lines",[]):
                    spans=line.get("spans",[]); text=_clean_text("".join(s.get("text","") for s in spans))
                    if not text: continue
                    size=max((float(s.get("size",body_size)) for s in spans),default=body_size)
                    blocks.append(TextBlock(text,page_index+1,heading=_is_heading_candidate(text,size,body_size,page.rect.height,float(line.get("bbox",[0,0,0,0])[1])),font_size=size))
        meta={"title":None,"author":None,"pages":len(doc)}
        try:
            info=PdfReader(str(path)).metadata
            meta["title"]=str(info.title).strip() if info and info.title else None
            meta["author"]=str(info.author).strip() if info and info.author else None
        except Exception: pass
        return "\n\n".join(b.text for b in blocks),blocks,len(doc),meta
    finally: doc.close()

def _resolve_epub_paths(z):
    root=ET.fromstring(z.read("META-INF/container.xml")); rootfile=next(iter(root.findall(".//{*}rootfile")))
    opf=rootfile.attrib["full-path"]; return opf,str(Path(opf).parent)

def extract_epub(path: Path):
    blocks=[]
    with zipfile.ZipFile(path) as z:
        opf_path,base_dir=_resolve_epub_paths(z); root=ET.fromstring(z.read(opf_path)); ns={"opf":"http://www.idpf.org/2007/opf","dc":"http://purl.org/dc/elements/1.1/"}
        manifest={i.attrib["id"]:i.attrib["href"] for i in root.findall(".//opf:item",ns)}; spine=[i.attrib["idref"] for i in root.findall(".//opf:itemref",ns)]
        tn=root.find(".//dc:title",ns); an=root.find(".//dc:creator",ns); title=tn.text.strip() if tn is not None and tn.text else None; author=an.text.strip() if an is not None and an.text else None
        for sid in spine:
            href=manifest.get(sid)
            if not href: continue
            fp=(str(Path(base_dir)/href) if base_dir!="." else href).replace("\\","/")
            try: raw=z.read(fp)
            except KeyError: continue
            soup=BeautifulSoup(raw,"lxml"); body=soup.body or soup
            for el in body.find_all(["h1","h2","h3","h4","h5","h6","p","li","blockquote"]):
                text=_clean_text(el.get_text(" ",strip=True))
                if text:
                    name=el.name.lower(); blocks.append(TextBlock(text,None,int(name[1]) if name.startswith("h") else 0,name.startswith("h"),None))
        return "\n\n".join(b.text for b in blocks),blocks,len(spine),{"title":title,"author":author,"pages":None}

def _heading_pairs(blocks):
    pairs=[]
    for i in range(len(blocks)-1):
        a,b=blocks[i],blocks[i+1]; token=a.text.strip()
        if not re.fullmatch(r"\d+(?:\.\d+){0,3}",token) or not b.text.strip() or len(b.text.split())>18: continue
        depth=token.count(".")+1
        if depth==1 and ((a.font_size or 0)<13 or (b.font_size or 0)<13): continue
        pairs.append((depth,f"{token} {b.text.strip()}",b.page))
    return pairs

def detect_structure(blocks):
    chapters=[]; sections=[]; seen=set(); ci=si=0; current=None; is_epub=all(b.page is None for b in blocks) if blocks else False
    if is_epub:
        for i,b in enumerate(blocks):
            if not b.heading: continue
            level=max(b.level,1); title=b.text.strip(); key=re.sub(r"\s+"," ",title).lower()
            if key in seen: continue
            seen.add(key)
            if level==1:
                ci+=1; current=title; chapters.append(Section(f"ch-{ci:04d}",title,1,current,i,None,None))
            else:
                si+=1; sections.append(Section(f"sec-{si:05d}",title,level,current,i,None,None))
        return chapters,sections
    for seq,(depth,title,page) in enumerate(_heading_pairs(blocks)):
        key=re.sub(r"\s+"," ",title).lower()
        if key in seen: continue
        seen.add(key)
        if depth==1:
            ci+=1; current=title; chapters.append(Section(f"ch-{ci:04d}",title,1,current,seq,page,page))
        else:
            si+=1; sections.append(Section(f"sec-{si:05d}",title,depth,current,seq,page,page))
    if not chapters and blocks:
        for idx,page in enumerate(sorted({b.page for b in blocks if b.page is not None}),1): chapters.append(Section(f"ch-{idx:04d}",f"Page {page}",1,f"Page {page}",idx,page,page))
    return chapters,sections

def _active_heading(blocks,index,chapters,sections):
    chapter=section=None
    for s in chapters:
        if s.sequence<=index: chapter=s.title
    for s in sections:
        if s.sequence<=index: section=s.title
    return chapter,section

def chunk_blocks(blocks,chapters,sections,target_words=900,max_words=1400):
    chunks=[]; buf=[]; words=0; start_page=end_page=None; start_index=0; sequence=0
    def flush(end_index):
        nonlocal buf,words,start_page,end_page,start_index,sequence
        if not buf:return
        chapter,section=_active_heading(blocks,start_index,chapters,sections); sequence+=1
        chunks.append(Chunk(f"chunk-{sequence:06d}","",chapter,section,start_page,end_page,sequence,"\n\n".join(buf).strip()))
        buf=[];words=0;start_page=end_page=None;start_index=end_index+1
    for i,b in enumerate(blocks):
        n=len(b.text.split())
        if not buf: start_index=i;start_page=b.page
        if buf and words>=target_words and (b.heading or words+n>max_words): flush(i-1);start_index=i;start_page=b.page
        buf.append(b.text);words+=n;end_page=b.page
        if words>=max_words: flush(i)
    flush(len(blocks)-1); return chunks

def extract_book(path):
    if path.suffix.lower()==".pdf": text,blocks,count,meta=extract_pdf(path)
    elif path.suffix.lower()==".epub": text,blocks,count,meta=extract_epub(path)
    else: raise ValueError("Unsupported book format. Use PDF or EPUB.")
    chapters,sections=detect_structure(blocks); chunks=chunk_blocks(blocks,chapters,sections)
    return text,blocks,count,meta,chapters,sections,chunks
