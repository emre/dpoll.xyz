from django.http import Http404
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Question
from .serializers import QuestionSerializer


class QuestionViewSet(ModelViewSet):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()

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