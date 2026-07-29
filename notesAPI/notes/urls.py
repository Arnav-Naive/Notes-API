from django.urls import path
from .views import NoteListCreate

urlpatterns = [
    path('', NoteListCreate.as_view(), name='note-list-create'),
]