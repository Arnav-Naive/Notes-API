# Notes API — Django REST Framework

First REST API ever built. Goal wasn't the Notes app itself — goal was finally
understanding the full request → response flow that tutorials never made click.

---

## Tech Stack

- Python + Django
- Django REST Framework (DRF)
- SQLite (default dev DB)
- Postman (manual testing)

---

## Project Structure

```
notesAPI/                  ← Django project root (has manage.py)
├── notesAPI/              ← project config folder
│   ├── settings.py
│   ├── urls.py            ← MAIN url router
├── notes/                 ← the actual app
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py            ← APP-level url router
├── venv/                  ← ignored by git
├── db.sqlite3             ← ignored by git
└── .gitignore
```

---

## The Model — `notes/models.py`

```python
class Note(models.Model):
    title = models.CharField(max_length=50)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
```

- `CharField` → short, bounded text (has a hard `max_length`, DB-enforced).
- `TextField` → long-form, unbounded text. No natural cap, so no `max_length` needed.
- `auto_now_add=True` → sets the timestamp **once**, only at creation. Never touched again on updates.
- `id` field — never wrote it myself. Django auto-adds it as the **auto-incrementing primary key** for every model.

**Rule of thumb learned:** CharField vs TextField isn't about "does it have a limit" —
it's about whether the content is naturally short/bounded (CharField) vs
long-form/open-ended (TextField, optionally with a soft `max_length` validation only,
not DB-enforced).

---

## The Serializer — `notes/serializers.py`

```python
class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'created_at']
```

**What a serializer actually does — translator + gatekeeper:**

1. **Model → JSON**: converts a Python `Note` object into JSON so the outside
   world (API clients) can read it.
2. **JSON → Model**: takes incoming JSON from a client, **validates** it
   (e.g. did they forget `title`?), then converts it into a Python object
   Django can save to the database.

`ModelSerializer` is the shortcut class — it already knows the model's fields
and auto-generates most of this logic, instead of writing every field by hand
like the plain `Serializer` class would require.

---

## The Views — `notes/views.py`

```python
class NoteListCreate(generics.ListCreateAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer

class NoteRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
```

**Core realization:** these two classes have *identical* bodies
(`queryset` + `serializer_class`), but behave completely differently.
The difference is 100% in the **parent class**, not in what I wrote:

- `ListCreateAPIView` → parent already has built-in logic for GET (list all) + POST (create new)
- `RetrieveUpdateDestroyAPIView` → parent already has built-in logic for GET (single item), PUT/PATCH (update), DELETE (remove)

Analogy that made it click: the parent class is a **recipe template** that
already knows the cooking steps. `queryset` and `serializer_class` are just
me filling in the blanks — "here's the ingredient (data source), here's the
conversion method (serializer)." I'm not writing the GET/POST/DELETE logic
myself; DRF already wrote it inside the parent class I inherited from.

`NoteListCreate` **inherits from** `ListCreateAPIView` — not the other way
around. Rule to never forget: `class Child(Parent):` — parent always goes
in the parentheses.

**Where does `.save()` happen if I never typed it?**
`ListCreateAPIView`'s built-in POST logic calls `serializer.save()`
internally on my behalf. In plain Django (no DRF), I'd have to call
`.save()` manually in my view. DRF's generic views hide that call inside
the parent class — it still happens, just not in code I wrote.

---

## The URLs

**`notes/urls.py`** (app-level):
```python
from django.urls import path
from .views import NoteListCreate, NoteRetrieveUpdateDestroy

urlpatterns = [
    path('', NoteListCreate.as_view(), name='note-list-create'),
    path('<int:pk>/', NoteRetrieveUpdateDestroy.as_view(), name='note-retrieve-update-destroy'),
]
```

**`notesAPI/urls.py`** (project-level):
```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("notes/", include("notes.urls")),
]
```

- `include()` hands off anything starting with `notes/` to the app's own
  urls.py — this is why apps can manage their own URL namespace instead of
  dumping everything into one giant project-level file.
- `<int:pk>/` → captures a number from the URL and passes it in as `pk`
  (the primary key / `id`). This is how `/notes/1/` knows which specific
  note to fetch/update/delete.
- `.as_view()` → converts my class-based view into something Django's URL
  system can actually call (it expects a callable function, not a raw class).

---

## Full Request Flow (GET /notes/)

```
Client (Postman/browser) sends GET /notes/
        │
        ▼
Project urls.py sees "notes/" prefix → hands off to notes/urls.py
        │
        ▼
notes/urls.py matches '' → routes to NoteListCreate view
        │
        ▼
NoteListCreate (is-a ListCreateAPIView) handles GET automatically
        │
        ▼
Looks at its own queryset → Note.objects.all() → fetches all rows from DB
        │
        ▼
Looks at its own serializer_class → NoteSerializer → converts rows to JSON
        │
        ▼
JSON response sent back to client
```

## Full Request Flow (POST /notes/)

```
Client sends POST /notes/ with JSON body {title, content}
        │
        ▼
Routed to NoteListCreate same as above
        │
        ▼
NoteListCreate's built-in POST logic:
  - passes incoming JSON to NoteSerializer
  - serializer validates it (is title present? right types?)
  - if valid → serializer.save() is called INTERNALLY by the parent class
  - new Note row created in db.sqlite3
        │
        ▼
Response: 201 Created + the new object (with auto-generated id + created_at)
```

---

## Things I broke and had to fix (real bugs, not hypothetical)

- Wrote `content - models.TextField(200)` — typo, `-` instead of `=`.
- Used `CharField(10)` / `TextField(200)` incorrectly — confused which field
  type needs `max_length` and why.
- Used `auto_created=True` instead of the correct `auto_now_add=True`.
- Wrote `from rest_framework import ListCreateAPIView` — wrong import path;
  it actually lives in `rest_framework.generics`.
- Forgot to import `NoteRetrieveUpdateDestroy` in `notes/urls.py` after
  adding the class — used it before importing it. Same mistake pattern
  happened twice, should watch for this going forward.
- Broken venv pointing to an unrelated project path (`ch1/venv`) — had to
  fully delete and recreate the venv from scratch.
- Ran `makemigrations`/`migrate` from the wrong directory (project root
  instead of the folder containing `manage.py`).
- Forgot to add `'notes'` and `'rest_framework'` to `INSTALLED_APPS` —
  caused `ModuleNotFoundError: No module named 'rest_framework'`.

---

## Tested & confirmed working

- [x] GET /notes/ → returns list (browsable API + Postman)
- [x] POST /notes/ → creates note, returns 201 + full object
- [x] GET /notes/<id>/ → returns single note, not full list
- [x] DELETE /notes/<id>/ → removes note, confirmed gone via follow-up GET
- [x] Auto-increment `id` behavior confirmed (deleted note's id not reused
      by next created note)

---

## Core lesson (the actual point of this project)

Before this: could follow a DRF tutorial, get it "working," but couldn't
explain *why* it worked — classic copy-paste-without-understanding trap.

After this: can trace the full path from HTTP request → URL routing →
view → serializer validation → model save → DB → JSON response, and
explain *why* two identically-written view classes behave differently
(parent class logic, not child class code).

**Next planned step:** Rebuild this entire thing from scratch, closed-book,
as a different app (Tasks API) with zero help, to confirm this actually
stuck rather than just being fresh in short-term memory.