from django.test import TestCase
from django.urls import reverse
from tasks.models import Task


class SearchTasksViewTests(TestCase):
    """Tests for the search_tasks view function."""

    @classmethod
    def setUpTestData(cls):
        """Create test tasks with varied completion states and titles."""
        cls.task1 = Task.objects.create(title='Buy milk', completed=False)
        cls.task2 = Task.objects.create(title='Buy eggs', completed=True)
        cls.task3 = Task.objects.create(title='Write tests', completed=False)
        cls.task4 = Task.objects.create(title='Deploy app', completed=True)

    def test_search_without_completed_param_returns_200(self):
        """Regression: accessing /search/ without 'completed' parameter must not raise KeyError."""
        response = self.client.get(reverse('search_tasks'))
        self.assertEqual(response.status_code, 200)

    def test_search_with_query_but_no_completed_param_returns_200(self):
        """Regression: search with ?q= but no 'completed' parameter must not crash."""
        response = self.client.get(reverse('search_tasks'), {'q': 'Buy'})
        self.assertEqual(response.status_code, 200)
        results = response.context['results']
        self.assertEqual(len(results), 2)

    def test_search_with_query_only_filters_by_title(self):
        """Search with only 'q' parameter filters tasks by title."""
        response = self.client.get(reverse('search_tasks'), {'q': 'Buy'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.task1, results)
        self.assertIn(self.task2, results)
        self.assertNotIn(self.task3, results)

    def test_search_with_completed_true_filters_completed_tasks(self):
        """Search with completed=true returns only completed tasks."""
        response = self.client.get(reverse('search_tasks'), {'completed': 'true'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.task2, results)
        self.assertIn(self.task4, results)
        self.assertNotIn(self.task1, results)
        self.assertNotIn(self.task3, results)

    def test_search_with_completed_false_filters_incomplete_tasks(self):
        """Search with completed=false returns only incomplete tasks."""
        response = self.client.get(reverse('search_tasks'), {'completed': 'false'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.task1, results)
        self.assertIn(self.task3, results)
        self.assertNotIn(self.task2, results)
        self.assertNotIn(self.task4, results)

    def test_search_with_both_query_and_completed_filter(self):
        """Search with both 'q' and 'completed' parameters combines filters."""
        response = self.client.get(reverse('search_tasks'), {'q': 'Buy', 'completed': 'true'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertEqual(len(results), 1)
        self.assertIn(self.task2, results)

    def test_search_with_invalid_completed_value_returns_all_results(self):
        """Search with completed=invalid does not crash and returns unfiltered results."""
        response = self.client.get(reverse('search_tasks'), {'q': 'Buy', 'completed': 'invalid'})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertEqual(len(results), 2)

    def test_search_empty_returns_all_tasks(self):
        """Search with no parameters returns all tasks."""
        response = self.client.get(reverse('search_tasks'))
        self.assertEqual(response.status_code, 200)
        results = response.context['results']
        self.assertEqual(len(results), 4)

    def test_search_by_task_id(self):
        """Search with numeric query searches by task ID as well as title."""
        response = self.client.get(reverse('search_tasks'), {'q': str(self.task1.id)})
        self.assertEqual(response.status_code, 200)
        results = list(response.context['results'])
        self.assertIn(self.task1, results)

    def test_search_no_results_found(self):
        """Search with query that matches nothing returns empty results."""
        response = self.client.get(reverse('search_tasks'), {'q': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        results = response.context['results']
        self.assertEqual(len(results), 0)
