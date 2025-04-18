from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

class GenerateQuestionsViewTests(TestCase):
    def test_generate_questions_valid_post(self):
        """Test valid POST request to generate questions."""
        pdf_file = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(reverse('generate_questions'), {
            'pdf_url': pdf_file,
            'start_page': 1,
            'end_page': 2
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('questions', response.json())

    def test_generate_questions_invalid_method(self):
        """Test invalid request method."""
        response = self.client.get(reverse('generate_questions'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Invalid request method"})

    def test_generate_questions_missing_fields(self):
        """Test POST request with missing fields."""
        response = self.client.post(reverse('generate_questions'), {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Missing required fields"})

    def test_generate_questions_invalid_page_range(self):
        """Test POST request with invalid page range."""
        pdf_file = SimpleUploadedFile("test.pdf", b"PDF content", content_type="application/pdf")
        response = self.client.post(reverse('generate_questions'), {
            'pdf_url': pdf_file,
            'start_page': 5,
            'end_page': 10
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Page range exceeds the number of pages in the PDF."})
