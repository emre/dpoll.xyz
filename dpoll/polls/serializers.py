from rest_framework import serializers

from .models import Question, Choice, User
from sponsors.models import Sponsor


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class ChoiceSerializer(serializers.ModelSerializer):
    voted_users = UserSerializer(many=True)

    class Meta:
        model = Choice
        exclude = ['question']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    is_editable = serializers.BooleanField()
    is_votable = serializers.BooleanField()

    class Meta:
        model = Question
        fields = '__all__'


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class LightQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class ChoiceSerializerWithQuestion(serializers.ModelSerializer):
    voted_users = UserSerializer(many=True)
    question = LightQuestionSerializer()

    class Meta:
        model = Choice
        fields = '__all__'


class UserDetailSerializer(UserSerializer):
    recent_questions = LightQuestionSerializer(many=True, read_only=True)
    recent_choices = ChoiceSerializerWithQuestion(many=True, read_only=True)
    question_count = serializers.IntegerField(source="total_polls_created")
    choice_count = serializers.IntegerField(source="total_votes_casted")

    class Meta:
        model = User
        fields = [
            'username',
            'recent_questions',
            'recent_choices',
            'question_count',
            'choice_count',
        ]
