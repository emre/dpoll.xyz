from django.http import Http404
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ViewSet
from rest_framework.views import APIView
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin
from rest_framework.decorators import action

from .models import Question, User, VoteAudit
from sponsors.models import Sponsor
from .serializers import (
    QuestionSerializer, SponsorSerializer, UserSerializer,
    UserDetailSerializer, VoteAuditSerializer,
)
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

    @action(detail=True, methods=['get'])
    def audit(self, request, pk=None):
        vote_audit = VoteAudit.objects.get(pk=pk)
        return Response(VoteAuditSerializer(vote_audit).data)




class TeamView(ViewSet):
    def list(self, request, format=None):
        return Response(TEAM_MEMBERS)

class SponsorViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = SponsorSerializer
    queryset = Sponsor.objects.all().order_by("-delegation_amount")


class UserViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all().exclude(is_superuser=True).order_by("-id")
    lookup_field = "username"

    def retrieve(self, request, *args, **kwargs):

        try:
            user = User.objects.get(username=kwargs.get("username"))
        except User.DoesNotExist:
            raise Http404

        return Response(UserDetailSerializer(user).data)

class AuditView(APIView):

    queryset = VoteAudit.objects.all()

    def get(self, request, **kwargs):

        try:
            question = Question.objects.get(
                username=request.query_params.get("username"),
                permlink=request.query_params.get("permlink")
            )
            vote_logs = VoteAudit.objects.filter(question=question)
        except (Question.DoesNotExist, VoteAudit.DoesNotExist):
            raise Http404

        audit = {
            "question": question.text,
            "author": question.username,
            "permlink": question.permlink,
            "voters": []
        }
        for vote_log in vote_logs:
            audit["voters"].append({
                "block_id": vote_log.block_id,
                "trx_id": vote_log.trx_id,
                "voter": vote_log.voter.username,
                "choices": [c.text for c in vote_log.choices.all()]
            })

        return Response(audit)
