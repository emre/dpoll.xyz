from steemconnect.client import Client
from django.contrib.auth import get_user_model


class SteemConnectBackend:

    def authenticate(self, request, **kwargs):

        if 'username' in kwargs:
            return None

        # validate the access token with /me endpoint and get user information
        client = Client(access_token=kwargs.get("access_token"), oauth_base_url="https://hivesigner.com/oauth2/", sc2_api_base_url="https://hivesigner.com/api/")

        user = client.me()
        if 'name' not in user:
            return None

        user_model = get_user_model()
        try:
            user_instance = user_model.objects.get(username=user["name"])
            user_instance.save()
        except user_model.DoesNotExist:
            user_instance = user_model.objects.create_user(
                username=user["name"])
        return user_instance

    def get_user(self, user_id):
        user_model = get_user_model()
        try:
            return user_model.objects.get(pk=user_id)
        except user_model.DoesNotExist:
            return None
