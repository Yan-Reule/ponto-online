"""Adaptador real do DeepFace; carregamento tardio evita bloquear a interface."""
import threading


class FaceError(Exception):
    pass


class FaceService:
    def __init__(self):
        self.lock = threading.Lock()

    def embedding(self, photo):
        import io
        import numpy as np
        from PIL import Image
        from deepface import DeepFace

        image = np.array(Image.open(io.BytesIO(photo)).convert('RGB'))[:, :, ::-1].copy()
        with self.lock:
            try:
                faces = DeepFace.represent(
                    img_path=image, model_name='Facenet512',
                    detector_backend='opencv', enforce_detection=True, align=True,
                )
            except ValueError as exc:
                raise FaceError('Nenhum rosto detectado. Melhore a iluminação e tente novamente.') from exc
        if len(faces) != 1:
            raise FaceError('A foto deve conter exatamente um rosto.')
        return faces[0]['embedding']

    def matches(self, embedding, employees):
        import json
        from deepface import DeepFace

        matches = []
        with self.lock:
            for employee in employees:
                result = DeepFace.verify(
                    img1_path=embedding, img2_path=json.loads(employee['embedding']),
                    model_name='Facenet512', distance_metric='cosine', silent=True,
                )
                if result['verified']:
                    matches.append(employee)
        return matches
