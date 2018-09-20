from steemconnect.client import Client
from django.contrib.auth import get_user_model


class SteemConnectBackend:

    def authenticate(self, **kwargs):

        if 'username' in kwargs:
            return None

        # validate the access token with /me endpoint and get user information
        client = Client(access_token=kwargs.get("access_token"))

        user = client.me()
        if 'name' not in user:
            return None

        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=user["name"])
        except user_model.DoesNotExist:
            user = user_model.objects.create_user(
                username=user["name"],
                name=user["name"])
        return user

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
