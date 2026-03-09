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
    order_field = sort_map.get(sort, '-created_at')
    tasks = Task.objects.order_by(order_field)

    # Show a "last added" hint in the header
    latest_task = tasks.order_by('-created_at').first()
    latest_title = latest_task.title if latest_task else None

    return render(request, 'tasks/index.html', {'tasks': tasks, 'sort': sort, 'latest_title': latest_title})


@require_POST
def add_task(request):
    """Add a new task with an optional reminder time (HH:MM)."""
    title = request.POST.get('title', '').strip()
    reminder_str = request.POST.get('reminder', '').strip()
    estimated_hours_str = request.POST.get('estimated_hours', '').strip()

    estimated_hours = None
    if estimated_hours_str:
        try:
            estimated_hours = int(estimated_hours_str)
        except ValueError:
            pass

    reminder_label = None
    if reminder_str:
        parts = reminder_str.split(':')
        if len(parts) == 2:
            try:
                hour = int(parts[0])
                minute = int(parts[1])
                reminder_label = f'{hour:02d}:{minute:02d}'
            except ValueError:
                pass

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
    task = get_object_or_404(Task, id=task_id)
    task.delete()
    return redirect('index')


def search_tasks(request):
    """Search tasks by title or task ID."""
    query = request.GET.get('q', '')
    results = []

    if query:
        try:
            task_id = int(query)
            results = Task.objects.filter(id=task_id) | Task.objects.filter(title__icontains=query)
        except ValueError:
            results = Task.objects.filter(title__icontains=query)

    return render(request, 'tasks/search.html', {'results': results, 'query': query})


def task_detail(request, task_id):
    """Show detail page for a single task."""
    task = get_object_or_404(Task, id=task_id)
    return render(request, 'tasks/task_detail.html', {'task': task})


def export_tasks_csv(request):
    """Export all tasks as a CSV file."""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Completed', 'Created At'])
    for task in Task.objects.all().order_by('id'):
        writer.writerow([task.id, task.title, task.completed, task.created_at])
    return response
