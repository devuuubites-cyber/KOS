"""KOS launcher for Pyto/iPadOS.
Run this file from the KOS project directory.

Pyto ships an older global typing-extensions package that can conflict with
Pydantic. KOS therefore prefers a small project-local dependency directory.
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
LOCAL_DEPS = os.path.join(BASE, '.kos_deps')
if os.path.isdir(LOCAL_DEPS):
    sys.path.insert(0, LOCAL_DEPS)

import uvicorn

if __name__ == '__main__':
    os.environ.setdefault('KOS_HOME', BASE)
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='info')
