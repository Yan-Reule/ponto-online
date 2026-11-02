"""Verificação opcional com IA real: python -m tests.smoke_deepface /caminho/foto.jpg."""
import argparse
import io
import tempfile
from pathlib import Path

from PIL import Image
from backend.app import create_app


def main():
    parser = argparse.ArgumentParser(description='Testar integração DeepFace em banco temporário.')
    parser.add_argument('photo', type=Path, help='Imagem com exatamente um rosto')
    args = parser.parse_args()
    photo = args.photo.read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        app = create_app({'TESTING': True, 'DATABASE': str(Path(directory) / 'smoke.db')})
        client = app.test_client()
        result = client.post('/api/employees', data={
            'name': 'Teste de integração', 'registration': 'QA', 'role': 'Demonstração',
            'photo': (io.BytesIO(photo), 'face.jpg'),
        })
        assert result.status_code == 201, (result.status_code, result.json)
        result = client.post('/api/punches', data={
            'kind': 'entrada', 'photo': (io.BytesIO(photo), 'face.jpg'),
        })
        assert result.status_code == 201, (result.status_code, result.json)
        assert len(client.get('/api/punches').json) == 1
        blank = io.BytesIO()
        Image.new('RGB', (300, 300), 'white').save(blank, 'JPEG')
        blank.seek(0)
        result = client.post('/api/punches', data={'kind': 'saida', 'photo': (blank, 'blank.jpg')})
        assert result.status_code == 422, (result.status_code, result.json)
        print('OK: cadastro, verificação facial real, persistência do ponto e rejeição de imagem sem rosto.')


if __name__ == '__main__':
    main()
