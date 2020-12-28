from django.contrib import auth
from drfutils.decorators import require_params
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from .. import serializers as s


class AuthAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request):
        return Response(self.serialized_user)

    @require_params(essentials=['username', 'password'])
    def post(self, request: Request, params):
        if not (user := auth.authenticate(username=params['username'], password=params['password'])):
            raise AuthenticationFailed()
        auth.login(request, user)
        return Response(self.serialized_user, status=HTTP_201_CREATED)

    def delete(self, request: Request):
        auth.logout(request)
        return Response(status=HTTP_204_NO_CONTENT)

    @property
    def serialized_user(self):
        return s.UserSerializer(self.request.user).data
