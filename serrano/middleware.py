from django.urls import reverse
from .cors import is_preflight
from .tokens import get_request_token


class SessionMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_request(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            return

        # Token-based authentication is attempting to be used, bypass CSRF
        # check. Allow POST requests to the root endpoint for authentication.
        # TODO sgithens https://stackoverflow.com/questions/19581110/exception-you-cannot-access-body-after-reading-from-requests-data-stream
        if get_request_token(request) or is_preflight(request) or \
                (request.method == 'POST' and
                 request.path == reverse('serrano:root')):
            request.csrf_processing_done = True
            return

        session = request.session
        # Ensure the session is created view processing, but only if a cookie
        # had been previously set. This is to prevent creating exorbitant
        # numbers of sessions for non-browser clients, such as bots.
        if session.session_key is None:
            if session.test_cookie_worked():
                session.delete_test_cookie()
                request.session.create()
            else:
                session.set_test_cookie()
