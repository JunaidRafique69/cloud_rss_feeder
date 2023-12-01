
from datetime import timedelta, datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api
from flask import request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from bs4 import BeautifulSoup
import requests
from helpers import extract_title_and_desc

app = Flask(__name__)
app.config['SECRET_KEY'] = '65374430fade73cd539b16952414d58495fa4869f290b6654348aac124c6241d'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)  # Set token expiration time

api = Api(app)
db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password_hash = generate_password_hash(password)


class ParsedFeed(db.Model):
    __tablename__ = 'parsed_feeds'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255))
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    last_parsed = db.Column(db.DateTime, default=datetime.utcnow)


class RegistrationResource(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Check if the username is already taken
        if User.query.filter_by(username=username).first():
            return {'message': 'Username already taken'}, 400

        # Create a new user
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return {'message': 'User registered successfully'}


class LoginResource(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            # Generate access token
            access_token = create_access_token(identity=user.id)
            return {'access_token': access_token}

        return {'message': 'Invalid credentials'}, 401


# Resource to handle RSS parsing
class RSSParserResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json()
        url = data.get('url')

        # Check if URL was parsed within the last 10 minutes
        last_parsed_entry = ParsedFeed.query.filter_by(url=url).first()

        if last_parsed_entry and (datetime.utcnow() - last_parsed_entry.last_parsed).total_seconds() < 600:
            return {'message': 'Last parsed results',
                    'data': {'title': last_parsed_entry.title, 'description': last_parsed_entry.description}}

        # Parse the RSS feed
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for 4xx and 5xx status codes
            feed = BeautifulSoup(response.content, 'html.parser')
            main_title, main_description = extract_title_and_desc(feed)
        except requests.RequestException as e:
            return {'message': f'Error fetching the RSS feed: {str(e)}'}, 500

        articles = []
        article_tags = feed.find_all('article')

        links = []
        for article_tag in article_tags:
            # Find all <a> tags within the current article
            anchor_tags = article_tag.find_all('a')
            for anchor_tag in anchor_tags:
                # Extract the href attribute from each <a> tag
                href = anchor_tag.get('href')
                # Check if the href attribute exists before appending to the list
                if href and href not in links:
                    links.append(href)

        for entry in links:
            response = requests.get(entry)
            feed = BeautifulSoup(response.content, 'html.parser')
            title, description = extract_title_and_desc(feed)
            articles.append({'title': title, 'description': description})

        # Save parsed data to the database

        new_parsed_entry = ParsedFeed(url=url, title=main_title, description=main_description)
        db.session.add(new_parsed_entry)
        db.session.commit()

        return {'message': 'Parsed successfully', 'data': articles}


# Add resources to the API
api.add_resource(RegistrationResource, '/register')
api.add_resource(LoginResource, '/login')
api.add_resource(RSSParserResource, '/parse_url')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables before running the app
    app.run(debug=True)
