import time
from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from restlib2.http import codes
from serrano.tokens import token_generator, generate_random_token


class TokenTestCase(TestCase):
    def test(self):
        user1 = User.objects.create_user(username='foo', password='bar')
        user2 = User.objects.create_user(username='bar', password='baz')

        token1 = token_generator.make(user1)
        token2 = token_generator.make(user2)

        self.assertTrue(token_generator.check(user1, token1))
        self.assertTrue(token_generator.check(user2, token2))

        self.assertFalse(token_generator.check(user1, token2))
        self.assertFalse(token_generator.check(user2, token1))

    @override_settings(SERRANO_TOKEN_TIMEOUT=2)
    def test_timeout(self):
        user1 = User.objects.create_user(username='foo', password='bar')
        token1 = token_generator.make(user1)

        self.assertTrue(token_generator.check(user1, token1))
        time.sleep(3)
        self.assertFalse(token_generator.check(user1, token1))

    def test_password_change(self):
        user1 = User.objects.create_user(username='foo', password='bar')
        token1 = token_generator.make(user1)

        self.assertTrue(token_generator.check(user1, token1))
        user1.set_password('new')
        self.assertFalse(token_generator.check(user1, token1))

    def test_non_string_token_split(self):
        self.assertEqual(token_generator.split(12345), (None, 12345))

    def test_unsplitable_token_check(self):
        user1 = User.objects.create_user(username='foo', password='bar')
        token1 = token_generator.make(user1)
        token1 = token1.replace('-', '')

        self.assertFalse(token_generator.check(user1, token1))

    def test_long_base_36_check(self):
        user1 = User.objects.create_user(username='foo', password='bar')
        token1 = token_generator.make(user1)
        pk, ts_b36, hash = token1.split('-')
        token1 = "{0}-{1}{2}{3}-{4}".format(pk, ts_b36, ts_b36, ts_b36, hash)

        self.assertFalse(token_generator.check(user1, token1))

    def test_generate_random_token(self):
        falsy = lambda x: False
        self.assertRaises(ValueError, generate_random_token, test=falsy)


class TokenBackendTestCase(TestCase):
    def test(self):
        user = User.objects.create_user(username='foo', password='bar')
        token = token_generator.make(user)
        self.assertEqual(user, authenticate(token=token))

    @override_settings(SERRANO_AUTH_REQUIRED=True)
    def test_resource(self):
        user = User.objects.create_user(username='foo', password='bar')

        resp = self.client.get(reverse('serrano:root'),
                               HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, codes.unauthorized)

        self.assertTrue(self.client.login(username='foo', password='bar'))
        resp = self.client.get(reverse('serrano:root'),
                               HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, codes.ok)

        self.client.logout()
        resp = self.client.get(reverse('serrano:root'),
                               HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, codes.unauthorized)

        token = token_generator.make(user)
        resp = self.client.get(reverse('serrano:root'), {'token': token},
                               HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, codes.ok)

    @override_settings(SERRANO_AUTH_REQUIRED=True, SESSION_COOKIE_AGE=2,
                       SESSION_SAVE_EVERY_REQUEST=True)
    def test_session_timeout(self):
        User.objects.create_user(username='foo', password='bar')

        self.assertTrue(self.client.login(username='foo', password='bar'))

        # Sucessive requests to refresh session since this client supports
        # cookies.
        for i in range(3):
            resp = self.client.get(reverse('serrano:root'),
                                   HTTP_ACCEPT='application/json')
            self.assertEqual(resp.status_code, codes.ok)
            time.sleep(1)

        # Wait longer than session timeout then make another request.
        time.sleep(3)
        resp = self.client.get(reverse('serrano:root'),
                               HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, codes.unauthorized)
