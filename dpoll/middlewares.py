from urllib.parse import urlparse

from django.utils.deprecation import MiddlewareMixin


class LoginReferrerMiddleware(MiddlewareMixin):

    def process_request(self, request):
        referer = request.META.get('HTTP_REFERER', None)
        if not request.path == '/login/' or not referer:
            return
        try:
            referer = urlparse(referer).path.split('/')[1]
            if referer == 'detail':
                request.session['initial_referer'] = request.META[
                    'HTTP_REFERER']
        except IndexError as e:
            pass
