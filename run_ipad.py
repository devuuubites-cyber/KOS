"""KOS launcher for Pyto/iPadOS.
Run this file from the KOS project directory.
"""
import os
import uvicorn

if __name__ == '__main__':
    os.environ.setdefault('KOS_HOME', os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='info')
