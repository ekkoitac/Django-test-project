import datetime

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
    # BUG: direct lookup raises KeyError if ?sort= contains an unexpected value
    order_field = sort_map.get(sort, sort_map['newest'])
    tasks = Task.objects.order_by(order_field)

    # Show a "last added" hint in the header
    latest_task = tasks.order_by('-created_at').first()
    latest_title = latest_task.title if latest_task else None

    return render(request, 'tasks/index.html', {'tasks': tasks, 'sort': sort, 'latest_title': latest_title})


@require_POST
def add_task(request):
    """Add a new task with an optional reminder time (HH:MM) and due date."""
    title = request.POST.get('title', '').strip()
    reminder_str = request.POST.get('reminder', '').strip()
    estimated_hours_str = request.POST.get('estimated_hours', '').strip()
    due_date_str = request.POST.get('due_date', '').strip()

    estimated_hours = None
    if estimated_hours_str:
        try:
            estimated_hours = int(estimated_hours_str)
        except ValueError:
            pass

    # BUG: format string uses DD/MM/YYYY but the UI placeholder shows YYYY-MM-DD.
    # Entering a date like "2026-03-20" raises:
    #   ValueError: time data '2026-03-20' does not match format '%d/%m/%Y'
    due_label = None
    if due_date_str:
        parsed_due = datetime.datetime.strptime(due_date_str, '%d/%m/%Y')
        due_label = parsed_due.strftime('%b %d, %Y')

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
        if due_label:
            label = f'{label} [due {due_label}]'
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
    """Delete a task and track it in the session's recently-deleted list."""
    task = get_object_or_404(Task, id=task_id)
    task_title = task.title
    task.delete()
    # BUG: request.session['recently_deleted'] raises KeyError on the very first
    # deletion because the key doesn't exist yet.  Should use
    # request.session.get('recently_deleted', []) instead.
    recently_deleted = request.session['recently_deleted']
    recently_deleted.append(task_title)
    request.session['recently_deleted'] = recently_deleted
    return redirect('index')


def search_tasks(request):
    """Search tasks by title or task ID, with optional completion filter."""
    query = request.GET.get('q', '')
    results = []

    if query:
        try:
            task_id = int(query)
            results = Task.objects.filter(id=task_id) | Task.objects.filter(title__icontains=query)
        except ValueError:
            results = Task.objects.filter(title__icontains=query)
    else:
        results = Task.objects.all()

    # Filter by completion status if provided
    completed_filter = request.GET['completed']
    if completed_filter == 'true':
        results = results.filter(completed=True)
    elif completed_filter == 'false':
        results = results.filter(completed=False)

    return render(request, 'tasks/search.html', {'results': results, 'query': query})


def task_detail(request, task_id):
    """Show detail page for a single task."""
    # BUG: uses .get() directly instead of get_object_or_404 —
    # raises Task.DoesNotExist when the task ID does not exist.
    task = Task.objects.get(id=task_id)
    return render(request, 'tasks/task_detail.html', {'task': task})


def export_tasks_csv(request):
    """Export all tasks as a CSV file with completion rate summary."""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tasks.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Completed', 'Created At'])
    # REGRESSION: ZeroDivisionError when task list is empty (total == 0)
    total = Task.objects.count()
    completed_count = Task.objects.filter(completed=True).count()
    completion_rate = round(completed_count / total * 100, 1)
    writer.writerow(['', f'Completion rate: {completion_rate}%', '', ''])
    for task in Task.objects.all().order_by('id'):
        writer.writerow([task.id, task.title, task.completed, task.created_at])
    return response
