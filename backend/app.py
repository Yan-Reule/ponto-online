import io
import json
import os
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request, send_file, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException

from backend.face import FaceError, FaceService

ROOT = Path(__file__).resolve().parent.parent
KINDS = {'entrada': 'Entrada', 'intervalo': 'Início do intervalo',
         'retorno': 'Retorno do intervalo', 'saida': 'Saída'}
NEXT = {None: {'entrada'}, 'entrada': {'intervalo', 'saida'},
        'intervalo': {'retorno'}, 'retorno': {'saida'}, 'saida': {'entrada'}}


class ApiError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def create_app(test_config=None, face_service=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATABASE=os.getenv('DATABASE_PATH', str(ROOT / 'data' / 'ponto.sqlite3')),
        MAX_CONTENT_LENGTH=6 * 1024 * 1024,
        TIMEZONE=os.getenv('APP_TIMEZONE', 'America/Araguaina'),
        NOW=lambda: datetime.now(timezone.utc),
    )
    if test_config:
        app.config.update(test_config)
    local_tz = ZoneInfo(app.config['TIMEZONE'])
    faces = face_service or FaceService()
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def connect():
        db = sqlite3.connect(app.config['DATABASE'], timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        return db

    from contextlib import contextmanager

    @contextmanager
    def database():
        db = connect()
        try:
            with db:
                yield db
        finally:
            db.close()

    with database() as db:
        db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                registration TEXT NOT NULL UNIQUE COLLATE NOCASE,
                role TEXT NOT NULL, photo BLOB NOT NULL,
                embedding TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS punches (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                kind TEXT NOT NULL CHECK(kind IN ('entrada','intervalo','retorno','saida')),
                occurred_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS punches_employee ON punches(employee_id, id);
        ''')

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(FaceError)
    def face_error(error):
        return jsonify(error=str(error)), 422

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = 'Envie uma imagem de até 5 MB.' if error.code == 413 else error.description
        return jsonify(error=message), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception('Falha ao processar solicitação')
        return jsonify(error='Não foi possível processar a solicitação. Consulte o terminal do servidor.'), 500

    def read_photo():
        upload = request.files.get('photo')
        if not upload:
            raise ApiError('Envie uma fotografia facial no campo photo.')
        raw = upload.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            raise ApiError('A fotografia deve ter no máximo 5 MB.', 413)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as original:
                    if original.format not in {'JPEG', 'PNG', 'WEBP'}:
                        raise ApiError('Use uma imagem JPEG, PNG ou WebP.')
                    if original.width * original.height > 16_000_000:
                        raise ApiError('A imagem deve ter no máximo 16 megapixels.')
                    from PIL import ImageOps
                    normalized = ImageOps.exif_transpose(original).convert('RGB')
                    normalized.thumbnail((1280, 1280))
                    output = io.BytesIO()
                    normalized.save(output, format='JPEG', quality=90)
                    return output.getvalue()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise ApiError('Arquivo de imagem inválido.') from exc

    def get_embedding(photo):
        try:
            return faces.embedding(photo)
        except FaceError:
            raise
        except Exception as exc:
            app.logger.exception('DeepFace indisponível')
            raise ApiError('Reconhecimento indisponível. Verifique as dependências e o download do modelo no servidor.', 503) from exc

    def public_employee(row):
        return {key: row[key] for key in ('id', 'name', 'registration', 'role', 'created_at')}

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', timezone=app.config['TIMEZONE'], model='Facenet512')

    @app.get('/api/employees')
    def employees():
        with database() as db:
            return jsonify([public_employee(row) for row in db.execute('SELECT * FROM employees ORDER BY name')])

    @app.post('/api/employees')
    def register():
        fields = {}
        for key, label, limit in [('name', 'Nome', 120), ('registration', 'Matrícula', 40), ('role', 'Cargo', 100)]:
            value = request.form.get(key, '').strip()
            if not value or len(value) > limit:
                raise ApiError(f'{label} é obrigatório e deve ter até {limit} caracteres.')
            fields[key] = value
        photo = read_photo()
        embedding = get_embedding(photo)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM employees WHERE registration = ?', (fields['registration'],)).fetchone():
                raise ApiError('Essa matrícula já está cadastrada.', 409)
            if faces.matches(embedding, db.execute('SELECT * FROM employees').fetchall()):
                raise ApiError('Este rosto já corresponde a um funcionário cadastrado.', 409)
            cursor = db.execute(
                'INSERT INTO employees(name, registration, role, photo, embedding, created_at) VALUES(?,?,?,?,?,?)',
                (*fields.values(), photo, json.dumps(embedding), app.config['NOW']().isoformat()),
            )
            row = db.execute('SELECT * FROM employees WHERE id=?', (cursor.lastrowid,)).fetchone()
            return jsonify(public_employee(row)), 201

    @app.get('/api/employees/<int:employee_id>/photo')
    def employee_photo(employee_id):
        with database() as db:
            row = db.execute('SELECT photo FROM employees WHERE id=?', (employee_id,)).fetchone()
        if row is None:
            raise ApiError('Funcionário não encontrado.', 404)
        response = send_file(io.BytesIO(row['photo']), mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.post('/api/punches')
    def punch():
        kind = request.form.get('kind')
        if kind not in KINDS:
            raise ApiError('Selecione um tipo de registro válido.')
        with database() as db:
            registered = db.execute('SELECT * FROM employees').fetchall()
        if not registered:
            raise ApiError('Cadastre um funcionário antes de registrar o ponto.', 409)
        embedding = get_embedding(read_photo())
        matches = faces.matches(embedding, registered)
        if not matches:
            raise ApiError('Rosto não reconhecido. Tente novamente ou cadastre o funcionário.', 404)
        if len(matches) != 1:
            raise ApiError('Identificação ambígua. Capture outra foto com melhor iluminação.', 409)
        employee = matches[0]
        now = app.config['NOW']()
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            last = db.execute('SELECT * FROM punches WHERE employee_id=? ORDER BY id DESC LIMIT 1', (employee['id'],)).fetchone()
            if last and (now - datetime.fromisoformat(last['occurred_at'])).total_seconds() < 30:
                raise ApiError('Aguarde 30 segundos entre registros para evitar duplicidade.', 409)
            previous = last['kind'] if last else None
            if kind not in NEXT[previous]:
                allowed = ', '.join(KINDS[k] for k in sorted(NEXT[previous]))
                raise ApiError(f'Sequência inválida. Próximo registro permitido: {allowed}.', 409)
            cursor = db.execute('INSERT INTO punches(employee_id, kind, occurred_at) VALUES(?,?,?)',
                                (employee['id'], kind, now.isoformat()))
            return jsonify(id=cursor.lastrowid, employee=public_employee(employee), kind=kind,
                           occurred_at=now.astimezone(local_tz).isoformat()), 201

    @app.get('/api/punches')
    def history():
        day = request.args.get('date', '')
        if day:
            try:
                datetime.strptime(day, '%Y-%m-%d')
            except ValueError:
                raise ApiError('Data inválida. Use AAAA-MM-DD.')
        with database() as db:
            rows = db.execute('''SELECT p.*, e.name, e.registration, e.role FROM punches p
                                 JOIN employees e ON p.employee_id=e.id ORDER BY p.id DESC''').fetchall()
        result = []
        for row in rows:
            item = dict(row)
            local = datetime.fromisoformat(item['occurred_at']).astimezone(local_tz)
            if day and local.date().isoformat() != day:
                continue
            item['occurred_at'] = local.isoformat()
            result.append(item)
        return jsonify(result)

    @app.get('/')
    @app.get('/<path:path>')
    def frontend(path='index.html'):
        if path.startswith('api/'):
            raise ApiError('Rota não encontrada.', 404)
        if not (ROOT / 'frontend/dist/index.html').exists():
            return 'Interface não compilada. Execute npm install e npm run build em frontend/.', 503
        return send_from_directory(ROOT / 'frontend/dist', path)

    return app
