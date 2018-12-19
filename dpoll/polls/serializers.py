from rest_framework import serializers

from .models import Question, Choice, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class ChoiceSerializer(serializers.ModelSerializer):
    voted_users = UserSerializer(many=True)
    class Meta:
        model = Choice
        fields = '__all__'



class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    class Meta:
        model = Question
        fields = '__all__'
