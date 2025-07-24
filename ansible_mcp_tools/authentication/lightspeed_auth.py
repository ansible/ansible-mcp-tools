from typing import List

from .base_auth import BaseAuthenticationBackend
from .protocols.validator import AuthenticationValidator


class LightspeedAuthenticationBackend(BaseAuthenticationBackend):
    def __init__(self, authentication_validators: List[AuthenticationValidator]):
        super().__init__(authentication_validators)
