from __future__ import annotations
import json
from .storage import Store

def export_json(db:Store):
    tables=('books','chapters','sections','chunks','knowledge_objects','relationships')
    return {table:[dict(row) for row in db.conn.execute(f'SELECT * FROM {table}').fetchall()] for table in tables}

def export_markdown(db:Store):
    lines=['# KOS Knowledge Export','']
    books=db.conn.execute('SELECT id,title,author FROM books ORDER BY title').fetchall()
    for book in books:
        lines += [f'## {book["title"]}',f'**Author:** {book["author"] or "Unknown"}','']
        objects=db.conn.execute('SELECT type,title,short_statement,detailed_explanation,importance,confidence,source_json,knowledge_status,claim_status FROM knowledge_objects WHERE book_id=? ORDER BY importance DESC,title',(book['id'],)).fetchall()
        for obj in objects:
            lines += [f'### {obj["title"]}',f'- **Type:** {obj["type"]}',f'- **Importance:** {obj["importance"]}/5',f'- **Confidence:** {obj["confidence"]}',f'- **Knowledge status:** {obj["knowledge_status"]}',f'- **Claim status:** {obj["claim_status"]}','',obj['short_statement'],obj['detailed_explanation'] or '',f'**Source:** {obj["source_json"] or "Unavailable"}','']
    return '\n'.join(lines)
