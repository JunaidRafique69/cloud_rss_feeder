import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app import app, db, ParsedFeed, RSSParserResource
import requests


class TestRSSParserResource(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['REQUESTS_GET'] = None  # Add this line to initialize the key
        self.app = app.test_client()

        with app.app_context():
            db.create_all()

        # Enter the application context explicitly
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Exit the application context
        self.app_context.pop()

        with app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('requests.get', side_effect=requests.RequestException('Mocked Error'))
    def test_parse_url_request_exception(self, mock_requests_get):
        url = "https://rss.com/blog/top-comedy-podcasts/"

        # Make a POST request to the endpoint with a URL that triggers a RequestException
        response = self.app.post('/parse_url', json={'url': url}, headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcwMTQ0MTA4MCwianRpIjoiMDMzYTNlMTMtMDBlZC00M2RlLTkwNjUtMmNmYjJmZTAwNDAwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MSwibmJmIjoxNzAxNDQxMDgwLCJleHAiOjE3MDE0NDQ2ODB9.qHQ3xp4Apyl5N4DlFLmYr3eGtAcdJ2BffeD78I5zhsU'})

        # Check if the response indicates an error
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error fetching the RSS feed', response.json['message'])

    @patch('requests.get')
    @patch('app.extract_title_and_desc', return_value=('Main Title', 'Main Description'))
    def test_parse_url_success(self, mock_extract, mock_requests_get):
        url = "https://rss.com/blog/top-comedy-podcasts/"

        # Mock the response for the requests.get call
        mock_requests_get.return_value.content = '<rss><channel><title>Main Title</title></channel></rss>'

        # Make a POST request to the endpoint
        response = self.app.post('/parse_url', json={'url': url}, headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTcwMTQ0MTA4MCwianRpIjoiMDMzYTNlMTMtMDBlZC00M2RlLTkwNjUtMmNmYjJmZTAwNDAwIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MSwibmJmIjoxNzAxNDQxMDgwLCJleHAiOjE3MDE0NDQ2ODB9.qHQ3xp4Apyl5N4DlFLmYr3eGtAcdJ2BffeD78I5zhsU'})

        # Check if the response is as expected
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['message'], 'Parsed successfully')

        # Check if the new parsed entry is added to the database
        new_parsed_entry = ParsedFeed.query.filter_by(url=url).first()
        self.assertIsNotNone(new_parsed_entry)
        self.assertEqual(new_parsed_entry.title, 'Main Title')
        self.assertEqual(new_parsed_entry.description, 'Main Description')

if __name__ == '__main__':
    unittest.main()
