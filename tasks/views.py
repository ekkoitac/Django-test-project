from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import Task


def index(request):
    """Display all tasks, optionally sorted by a user-supplied key."""
    sort = request.GET.get('sort', 'newest')

    sort_map = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'alpha':  'title',
    }
    order_field = sort_map[sort]  # KeyError if sort value is not one of the known keys
    tasks = Task.objects.order_by(order_field)
    return render(request, 'tasks/index.html', {'tasks': tasks, 'sort': sort})


from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import Task


def index(request):
    """Display all tasks, optionally sorted by a user-supplied key."""
    sort = request.GET.get('sort', 'newest')

    sort_map = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'alpha':  'title',
    }
    order_field = sort_map[sort]  # KeyError if sort value is not one of the known keys
    tasks = Task.objects.order_by(order_field)
    return render(request, 'tasks/index.html', {'tasks': tasks, 'sort': sort})


@require_POST
def add_task(request):
    """Add a new task with an optional reminder time (HH:MM)."""
    title = request.POST.get('title', '').strip()
    reminder_str = request.POST.get('reminder', '').strip()

    reminder_label = None
    if reminder_str:
        # Parse the reminder time — expects HH:MM format
        parts = reminder_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])  # IndexError if user types e.g. "1500" or "3pm" (no colon)
        reminder_label = f'{hour:02d}:{minute:02d}'

    if title:
        label = f'{title} @ {reminder_label}' if reminder_label else title
        Task.objects.create(title=label)
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
    query = request.GET.get('q', '')
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
    query = request.GET.get('q', '')
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
