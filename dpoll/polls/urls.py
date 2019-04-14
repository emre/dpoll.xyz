from django.urls import path

from . import views


from rest_framework import routers

from .api_views import (
    QuestionViewSet,
    TeamView,
    AuditView,
    SponsorViewSet,
    UserViewSet
)


api_router = routers.DefaultRouter()
api_router.register(r'questions', QuestionViewSet,
                base_name='poll_view_set')
api_router.register(r'users', UserViewSet,
                base_name='user_view_set')
api_router.register(r'team', TeamView, base_name='team')
api_router.register(r'sponsors', SponsorViewSet, base_name='sponsors')

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.sc_login, name='login'),
    path('logout/', views.sc_logout, name='logout'),
    path('detail/@<str:user>/<str:permlink>/', views.detail, name='detail'),
    path('vote/@<str:user>/<str:permlink>/', views.vote, name='vote'),
    path('user/@<str:user>/', views.profile, name='profile'),
    path('create/', views.create_poll, name='create-poll'),
    path('team/', views.team, name='team'),
    path('edit/@<str:author>/<str:permlink>/', views.edit_poll, name='edit'),
    path('polls_by_vote/', views.polls_by_vote_count, name='polls-by-vote'),
    path('api/v1/audit/', AuditView.as_view(), name="api-audit"),
    path('web-api/vote_tx/', views.vote_transaction_details, name="vote-tx"),
]