from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search, name='search'),
    path('ask/', views.ask, name='ask'),
    path('chat-sessions/', views.ChatSessionListCreateView.as_view(), name='chat-sessions'),
    path('chat-history/<str:session_id>/', views.ChatHistoryView.as_view(), name='chat-history'),

]
