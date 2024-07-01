import json
import logging
from datetime import datetime
from functools import lru_cache
from typing import Optional, List

import firebase_admin
import pytz
from fastapi import Header
from firebase_admin import auth
from firebase_admin import firestore
from firebase_admin.credentials import Certificate
from google.cloud.firestore_v1 import transactional, Transaction

from gemini_movie_detectives_api.model import QuizType

logger = logging.getLogger(__name__)


class LimitExceededError(Exception):

    def __init__(self, message: str, quiz_type: QuizType, usage: int, limit: int):
        super().__init__(message)
        self.quiz_type = quiz_type
        self.usage = usage
        self.limit = limit


class FirestoreClient:

    def __init__(self, certificate: Certificate):
        self.firebase_app = firebase_admin.initialize_app(certificate)
        self.firestore_client = firestore.client()

    def get_or_create_user(self, user_id: str, x_user_info: Optional[str] = Header(None)) -> dict:
        user_ref = self.firestore_client.collection('users').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            return user_doc.to_dict()
        else:
            user_data = {
                'user_id': user_id,
                'created_at': firestore.firestore.SERVER_TIMESTAMP,
                'score_total': 0,
                'games_total': 0,
                'score_title_detectives': 0,
                'games_title_detectives': 0,
                'score_sequel_salad': 0,
                'games_sequel_salad': 0,
                'score_bttf_trivia': 0,
                'games_bttf_trivia': 0,
                'score_trivia': 0,
                'games_trivia': 0
            }

            if x_user_info:
                user_info = json.loads(x_user_info)
                user_data['display_name'] = user_info.get('displayName')
                user_data['photo_url'] = user_info.get('photoURL')

            user_ref.set(user_data)
            return user_data

    def get_current_user(self, authorization: Optional[str] = Header(None), x_user_info: Optional[str] = Header(None)) -> Optional[str]:
        if authorization:
            try:
                token = authorization.split("Bearer ")[1]
                decoded_token = auth.verify_id_token(token)
                uid = decoded_token['uid']
                _ = self.get_or_create_user(uid, x_user_info)

                return uid
            except Exception:
                pass

        return None  # return None for unauthenticated users

    def inc_games(self, user_id: str, quiz_type: QuizType) -> None:
        try:
            user_ref = self.firestore_client.collection('users').document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()

                match quiz_type:
                    case QuizType.TITLE_DETECTIVES: user_data['games_title_detectives'] += 1
                    case QuizType.SEQUEL_SALAD: user_data['games_sequel_salad'] += 1
                    case QuizType.BTTF_TRIVIA: user_data['games_bttf_trivia'] += 1
                    case QuizType.TRIVIA: user_data['games_trivia'] += 1

                user_data['games_total'] += 1
                user_ref.update(user_data)
        except Exception as e:
            logger.error(f'Error increasing games: {e}')

    def inc_score(self, user_id: str, quiz_type: QuizType, points: int) -> None:
        try:
            user_ref = self.firestore_client.collection('users').document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()

                match quiz_type:
                    case QuizType.TITLE_DETECTIVES: user_data['score_title_detectives'] += points
                    case QuizType.SEQUEL_SALAD: user_data['score_sequel_salad'] += points
                    case QuizType.BTTF_TRIVIA: user_data['score_bttf_trivia'] += points
                    case QuizType.TRIVIA: user_data['score_trivia'] += points

                user_data['score_total'] += points
                user_ref.update(user_data)
        except Exception as e:
            logger.error(f'Error increasing score: {e}')

    # noinspection PyBroadException
    @lru_cache
    def get_franchises(self) -> List[str]:
        franchises_ref = self.firestore_client.collection('movie-data').document('franchises')
        franchises_doc = franchises_ref.get()

        if not franchises_doc.exists or 'franchises' not in franchises_doc.to_dict() or not franchises_doc.to_dict()['franchises']:
            raise ValueError('Franchises document not found or empty')

        return franchises_doc.to_dict()['franchises']

    def get_limits(self) -> dict:
        limits_doc = self.firestore_client.collection('limits').document('limits').get()
        if not limits_doc.exists:
            raise ValueError('Limits document not found')

        return limits_doc.to_dict()

    def get_usage_counts(self) -> dict:
        today = datetime.now(pytz.utc).date().isoformat()
        usage_ref = self.firestore_client.collection('limits').document(f'usage_{today}')
        usage_doc = usage_ref.get()

        if not usage_doc.exists:
            return {qt.value: 0 for qt in QuizType}

        return usage_doc.to_dict()['counts']

    def update_usage_count(self, quiz_type: QuizType) -> int:
        transaction = self.firestore_client.transaction()

        today = datetime.now(pytz.utc).date().isoformat()
        usage_ref = self.firestore_client.collection('limits').document(f'usage_{today}')

        return self._update_usage_count(transaction, self.get_limits(), quiz_type, usage_ref)

    @staticmethod
    @firestore.transactional
    def _update_usage_count(transaction: Transaction, limits: dict, quiz_type: QuizType, usage_ref: firestore.DocumentReference) -> int:
        if quiz_type not in limits:
            raise ValueError(f'No limit configured for {quiz_type}')

        usage_doc = usage_ref.get(transaction=transaction)

        if not usage_doc.exists:
            usage = {'counts': {qt.value: 0 for qt in QuizType}}
            transaction.set(usage_ref, usage)
        else:
            usage = usage_doc.to_dict()

        current_count = usage['counts'].get(quiz_type, 0)

        if current_count >= limits[quiz_type]:
            raise LimitExceededError(
                f'Usage limit exceeded for {quiz_type}',
                quiz_type,
                current_count,
                limits[quiz_type]
            )

        updated_count = current_count + 1
        usage['counts'][quiz_type] = updated_count
        transaction.set(usage_ref, usage, merge=True)

        return updated_count
