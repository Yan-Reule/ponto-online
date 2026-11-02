"""Testa regras e persistência com um adaptador facial controlado, sem baixar IA."""
import io
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
from backend.app import create_app
from backend.face import FaceError


class FakeFace:
    def __init__(self):
        self.identity = 1
        self.error = False
        self.ambiguous = False

    def embedding(self, photo):
        if self.error:
            raise FaceError('A foto deve conter exatamente um rosto.')
        return [self.identity]

    def matches(self, embedding, employees):
        import json
        return [e for e in employees if self.ambiguous or json.loads(e['embedding']) == embedding]


class AppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.face = FakeFace()
        self.now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        self.config = {'TESTING': True, 'DATABASE': str(Path(self.temp.name) / 'test.db'), 'NOW': lambda: self.now}
        self.app = create_app(self.config, self.face)
        self.client = self.app.test_client()

    def photo(self):
        data = io.BytesIO()
        Image.new('RGB', (20, 20), 'white').save(data, format='JPEG')
        data.seek(0)
        return data, 'photo.jpg'

    def register(self, registration='001'):
        return self.client.post('/api/employees', data={
            'name': 'Ana Silva', 'registration': registration, 'role': 'Analista', 'photo': self.photo()})

    def punch(self, kind):
        return self.client.post('/api/punches', data={'kind': kind, 'photo': self.photo()})

    def advance(self):
        self.now += timedelta(seconds=31)

    def test_registration_persisted_without_exposing_biometrics(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('embedding', response.json)
        second = create_app(self.config, self.face).test_client()
        self.assertEqual(len(second.get('/api/employees').json), 1)
        self.assertEqual(second.get('/api/employees/1/photo').mimetype, 'image/jpeg')

    def test_duplicate_registration_and_face(self):
        self.register()
        self.face.identity = 2
        self.assertEqual(self.register().status_code, 409)
        self.face.identity = 1
        self.assertEqual(self.register('002').status_code, 409)

    def test_complete_workday(self):
        self.register()
        for kind in ('entrada', 'intervalo', 'retorno', 'saida'):
            response = self.punch(kind)
            self.assertEqual(response.status_code, 201, response.json)
            self.assertTrue(response.json['occurred_at'].endswith('-03:00'))
            self.advance()
        self.assertEqual(len(self.client.get('/api/punches?date=2026-10-21').json), 4)
        self.assertEqual(self.client.get('/api/punches?date=2026-10-20').json, [])

    def test_invalid_order_and_double_click(self):
        self.register()
        self.assertEqual(self.punch('saida').status_code, 409)
        self.assertEqual(self.punch('entrada').status_code, 201)
        self.assertEqual(self.punch('saida').status_code, 409)
        self.advance()
        self.assertEqual(self.punch('entrada').status_code, 409)
        self.assertEqual(self.punch('saida').status_code, 201)
        self.assertEqual(len(self.client.get('/api/punches').json), 2)

    def test_unknown_face_does_not_write_punch(self):
        self.register()
        self.face.identity = 99
        self.assertEqual(self.punch('entrada').status_code, 404)
        self.assertEqual(self.client.get('/api/punches').json, [])

    def test_ambiguous_identity_rejected(self):
        self.register()
        self.face.identity = 2
        self.register('002')
        self.face.ambiguous = True
        self.assertEqual(self.punch('entrada').status_code, 409)
        self.assertEqual(self.client.get('/api/punches').json, [])

    def test_missing_or_multiple_faces_rejected(self):
        self.face.error = True
        self.assertEqual(self.register().status_code, 422)
        self.assertEqual(self.client.get('/api/employees').json, [])

    def test_invalid_image_and_fields(self):
        data = {'name': 'Ana', 'registration': '001', 'role': 'Dev', 'photo': (io.BytesIO(b'not-image'), 'fake.jpg')}
        self.assertEqual(self.client.post('/api/employees', data=data).status_code, 400)
        self.assertEqual(self.client.post('/api/employees', data={'name': ' '}).status_code, 400)
        self.assertEqual(self.punch('invalido').status_code, 400)
        self.assertEqual(self.client.get('/api/punches?date=invalid').status_code, 400)

    def test_image_size_limit(self):
        data = {'name': 'Ana', 'registration': '001', 'role': 'Dev', 'photo': (io.BytesIO(b'x' * (5 * 1024 * 1024 + 1)), 'large.jpg')}
        self.assertEqual(self.client.post('/api/employees', data=data).status_code, 413)

    def test_overnight_shift_and_local_date(self):
        self.register()
        self.now = datetime(2026, 10, 22, 2, 59, tzinfo=timezone.utc)
        self.assertEqual(self.punch('entrada').status_code, 201)
        self.now += timedelta(hours=2)
        self.assertEqual(self.punch('saida').status_code, 201)
        self.assertEqual(len(self.client.get('/api/punches?date=2026-10-21').json), 1)
        self.assertEqual(len(self.client.get('/api/punches?date=2026-10-22').json), 1)

    def test_empty_database_and_unknown_routes(self):
        self.assertEqual(self.punch('entrada').status_code, 409)
        self.assertEqual(self.client.get('/api/no-such-route').status_code, 404)
        self.assertEqual(self.client.get('/api/employees/999/photo').status_code, 404)


if __name__ == '__main__':
    unittest.main()
