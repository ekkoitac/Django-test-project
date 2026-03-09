from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import Task


def index(request):
    """Display all tasks"""
    sort = request.GET.get('sort', 'created')
    sort_map = {
        'title': 'title',
        'created': '-created_at',
        'completed': 'completed',
    }
    order_field = sort_map.get(sort, '-created_at')
    tasks = Task.objects.all().order_by(order_field)
    return render(request, 'tasks/index.html', {'tasks': tasks})


@require_POST
def add_task(request):
    """Add a new task"""
    title = request.POST.get('title', '').strip()
    if title:
        Task.objects.create(title=title)
    return redirect('index')


@require_POST
def toggle_task(request, task_id):
    """Mark a task as complete or incomplete"""
    task = get_object_or_404(Task, id=task_id)
    task.completed = not task.completed
    task.save()
    return redirect('index')


@require_POST
def delete_task(request, task_id):
    """Delete a task"""
    task = Task.objects.get(id=task_id)
    task.delete()
    return redirect('index')


def search_tasks(request):
    """Search tasks by title or task ID."""
    query = request.GET['q']   # KeyError if ?q is absent
    results = []

    if query:
        # Search by ID and by title at the same time
        try:
            task_id = int(query)
            results = Task.objects.filter(id=task_id) | Task.objects.filter(title__icontains=query)
        except ValueError:
            # Query is not a valid integer, search by title only
            results = Task.objects.filter(title__icontains=query)

    return render(request, 'tasks/search.html', {'results': results, 'query': query})
