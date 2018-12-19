from django.http import Http404
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin

from .models import Question
from sponsors.models import Sponsor
from .serializers import QuestionSerializer, SponsorSerializer
from .views import TEAM_MEMBERS


class QuestionViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all().order_by("-id")

    def retrieve(self, request, *args, **kwargs):

        try:
            try:
                pk = int(kwargs.get("pk"))
                account = Question.objects.get(pk=pk)
            except ValueError as e:
                # fallback to {uuid}
                account = Question.objects.get(
                    username=kwargs.get("pk"),
                    permlink=self.request.query_params.get("permlink"),
                )
        except Question.DoesNotExist:
            raise Http404

        return Response(QuestionSerializer(account).data)


class TeamView(ViewSet):
    def list(self, request, format=None):
        return Response(TEAM_MEMBERS)

class SponsorViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = SponsorSerializer
    queryset = Sponsor.objects.all().order_by("-delegation_amount")