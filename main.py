"""Inicia a aplicação local usando um servidor WSGI."""
import os
from waitress import serve
from backend.app import create_app

app = create_app()

if __name__ == '__main__':
    print('PontoFace disponível em http://localhost:8000', flush=True)
    serve(app, host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8000')), threads=4)
