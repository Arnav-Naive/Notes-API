from django.urls import path
from .views import NoteListCreate, NoteRetrieveUpdateDestroy

urlpatterns = [
    path('', NoteListCreate.as_view(), name='note-list-create'),
    path('<int:pk>/', NoteRetrieveUpdateDestroy.as_view(), name='note-retrieve-update-destroy')
]