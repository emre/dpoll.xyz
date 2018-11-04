from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.sc_login, name='login'),
    path('logout/', views.sc_logout, name='logout'),
    path('detail/@<str:user>/<str:permlink>/', views.detail, name='detail'),
    path('vote/@<str:user>/<str:permlink>/', views.vote, name='vote'),
    path('user/@<str:user>/', views.profile, name='profile'),
    path('create/', views.create_poll, name='create-poll'),
]