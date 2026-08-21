from __future__ import annotations
import html
import posixpath
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
    index: int = 0

def clean_text(text: str) -> str:
    text=html.unescape(text).replace("\u00a0"," ")
    text=re.sub(r"[ \t]+"," ",text)
    return re.sub(r"\n{3,}","\n\n",text).strip()

def numbered_heading(text: str):
    m=re.match(r"^(\d+(?:\.\d+){0,3})\s+(.+?)\s*$",text.strip())
    if not m or len(m.group(2))>160 or len(m.group(2).split())>22:return None
    return m.group(1).count(".")+1,f"{m.group(1)} {m.group(2)}"

def heading_candidate(text,size,body_size):
    t=text.strip()
    if not t or len(t)>180 or len(t.split())>24:return False
    if re.match(r"^(chapter|part|section)\s+([0-9ivxlcdm]+|[a-z])\b",t,re.I):return True
    if numbered_heading(t):return True
    return size>=max(body_size*1.22,body_size+1.5) and t[:1].isupper() and not t.endswith((".",",",";",":"))

def extract_pdf(path: Path):
    blocks=[];doc=fitz.open(path)
    try:
        for pi,page in enumerate(doc):
            data=page.get_text("dict"); sizes=[float(s.get("size",10)) for b in data.get("blocks",[]) if b.get("type")==0 for l in b.get("lines",[]) for s in l.get("spans",[]) if s.get("text","").strip()]
            body=sorted(sizes)[len(sizes)//2] if sizes else 10.0
            for b in data.get("blocks",[]):
                if b.get("type")!=0:continue
                for line in b.get("lines",[]):
                    spans=line.get("spans",[]);text=clean_text("".join(s.get("text","") for s in spans))
                    if not text:continue
                    size=max((float(s.get("size",body)) for s in spans),default=body)
                    blocks.append(TextBlock(text,pi+1,0,heading_candidate(text,size,body),size,len(blocks)))
        meta={"title":None,"author":None,"pages":len(doc)}
        try:
            info=PdfReader(str(path)).metadata
            meta["title"]=str(info.title).strip() if info and info.title else None
            meta["author"]=str(info.author).strip() if info and info.author else None
        except Exception:pass
        return "\n\n".join(b.text for b in blocks),blocks,len(doc),meta
    finally:doc.close()

def extract_epub(path: Path):
    blocks=[]
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read("META-INF/container.xml"));rf=root.find(".//{*}rootfile")
        if rf is None:raise ValueError("Invalid EPUB container")
        opf=rf.attrib["full-path"];base=posixpath.dirname(opf);pkg=ET.fromstring(z.read(opf));ns={"opf":"http://www.idpf.org/2007/opf","dc":"http://purl.org/dc/elements/1.1/"}
        manifest={x.attrib["id"]:x.attrib["href"] for x in pkg.findall(".//opf:item",ns)};spine=[x.attrib["idref"] for x in pkg.findall(".//opf:itemref",ns)]
        tn=pkg.find(".//dc:title",ns);an=pkg.find(".//dc:creator",ns);title=tn.text.strip() if tn is not None and tn.text else None;author=an.text.strip() if an is not None and an.text else None
        for sid in spine:
            href=manifest.get(sid)
            if not href:continue
            member=posixpath.normpath(posixpath.join(base,href.split("#",1)[0]))
            try:raw=z.read(member)
            except KeyError:continue
            soup=BeautifulSoup(raw,"lxml");body=soup.body or soup
            for el in body.find_all(["h1","h2","h3","h4","h5","h6","p","li","blockquote"]):
                text=clean_text(el.get_text(" ",strip=True))
                if not text:continue
                name=el.name.lower();head=name.startswith("h")
                blocks.append(TextBlock(text,None,int(name[1]) if head else 0,head,None,len(blocks)))
        return "\n\n".join(b.text for b in blocks),blocks,len(spine),{"title":title,"author":author,"pages":None}

def detect_structure(blocks):
    chapters=[];sections=[];seen=set();current=None;ci=si=0
    for b in blocks:
        if not b.heading:continue
        nh=numbered_heading(b.text);level=nh[0] if nh else max(b.level,1);title=nh[1] if nh else b.text.strip();key=re.sub(r"\s+"," ",title).lower()
        if key in seen:continue
        seen.add(key)
        if level==1:
            ci+=1;current=title;chapters.append(Section(f"ch-{ci:04d}",title,1,current,b.index,b.page,b.page))
        else:
            si+=1;sections.append(Section(f"sec-{si:05d}",title,level,current,b.index,b.page,b.page))
    if not chapters and blocks:
        pages=sorted({b.page for b in blocks if b.page is not None})
        for i,page in enumerate(pages,1):
            title=f"Page {page}";idx=next(j for j,b in enumerate(blocks) if b.page==page);chapters.append(Section(f"ch-{i:04d}",title,1,title,idx,page,page))
    return chapters,sections

def chunk_blocks(blocks,chapters,sections,target_words=900,max_words=1400):
    chunks=[];buf=[];words=0;start_page=end_page=None;start_index=0;seq=0
    def active(i):
        ch=sec=None
        for x in chapters:
            if x.sequence<=i:ch=x.title
        for x in sections:
            if x.sequence<=i:sec=x.title
        return ch,sec
    def flush(end):
        nonlocal buf,words,start_page,end_page,start_index,seq
        if not buf:return
        ch,sec=active(start_index);seq+=1;chunks.append(Chunk(f"chunk-{seq:06d}","",ch,sec,start_page,end_page,seq,"\n\n".join(buf).strip()))
        buf=[];words=0;start_page=end_page=None;start_index=end+1
    for i,b in enumerate(blocks):
        n=len(b.text.split())
        if not buf:start_index=i;start_page=b.page
        if buf and words>=target_words and b.heading:flush(i-1);start_index=i;start_page=b.page
        buf.append(b.text);words+=n;end_page=b.page
        if words>=max_words:flush(i)
    flush(len(blocks)-1);return chunks

def extract_book(path: Path):
    if path.suffix.lower()==".pdf":text,blocks,count,meta=extract_pdf(path)
    elif path.suffix.lower()==".epub":text,blocks,count,meta=extract_epub(path)
    else:raise ValueError("Unsupported book format. Use PDF or EPUB.")
    chapters,sections=detect_structure(blocks);chunks=chunk_blocks(blocks,chapters,sections)
    return text,blocks,count,meta,chapters,sections,chunks
