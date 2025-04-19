from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association tables for many-to-many relationships
book_tags = db.Table('book_tags',
    db.Column('book_id', db.Integer, db.ForeignKey('books.id'), primary_key=True),
    db.Column('tag', db.String(50), primary_key=True)
)

child_interests = db.Table('child_interests',
    db.Column('child_profile_id', db.Integer, db.ForeignKey('child_profiles.id'), primary_key=True),
    db.Column('interest', db.String(50), primary_key=True)
)

challenge_participants = db.Table('challenge_participants',
    db.Column('challenge_id', db.Integer, db.ForeignKey('challenges.id'), primary_key=True),
    db.Column('child_profile_id', db.Integer, db.ForeignKey('child_profiles.id'), primary_key=True),
    db.Column('progress', db.Integer, default=0),
    db.Column('completed', db.Boolean, default=False),
    db.Column('joined_at', db.DateTime, default=datetime.utcnow)
)

# User model
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='parent')  # 'parent', 'educator', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    theme_preference = db.Column(db.String(10), default='light')  # 'light' or 'dark'
    
    # Relationships
    child_profiles = db.relationship('ChildProfile', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'theme_preference': self.theme_preference
        }

# Child Profile model
class ChildProfile(db.Model):
    __tablename__ = 'child_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    reading_level = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_url = db.Column(db.String(255))
    
    # Many-to-many relationship for interests
    interests = db.relationship('child_interests', secondary=child_interests, lazy='subquery',
                                backref=db.backref('child_profiles', lazy=True))
    
    # Relationships
    reading_lists = db.relationship('ReadingList', backref='child_profile', lazy=True)
    learning_paths = db.relationship('LearningPath', backref='child_profile', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'age': self.age,
            'reading_level': self.reading_level,
            'interests': [interest for interest in self.interests],
            'created_at': self.created_at.isoformat(),
            'avatar_url': self.avatar_url
        }

# Book model
class Book(db.Model):
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    age_range = db.Column(db.String(20), nullable=False)
    genre = db.Column(db.String(50), nullable=False)
    cover_image_url = db.Column(db.String(255))
    content_url = db.Column(db.String(255))
    is_interactive = db.Column(db.Boolean, default=False)
    reading_time_minutes = db.Column(db.Integer)
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship for tags
    tags = db.relationship('book_tags', secondary=book_tags, lazy='subquery',
                           backref=db.backref('books', lazy=True))
    
    # Relationships
    reading_lists = db.relationship('ReadingList', backref='book', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'age_range': self.age_range,
            'genre': self.genre,
            'tags': [tag for tag in self.tags],
            'cover_image_url': self.cover_image_url,
            'content_url': self.content_url,
            'is_interactive': self.is_interactive,
            'reading_time_minutes': self.reading_time_minutes,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'created_at': self.created_at.isoformat()
        }

# Reading List model
class ReadingList(db.Model):
    __tablename__ = 'reading_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    child_profile_id = db.Column(db.Integer, db.ForeignKey('child_profiles.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    status = db.Column(db.String(20), default='to-read')  # 'to-read', 'in-progress', 'completed'
    progress_percentage = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'child_profile_id': self.child_profile_id,
            'book_id': self.book_id,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

# Challenge model
class Challenge(db.Model):
    __tablename__ = 'challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    goal = db.Column(db.Integer, nullable=False)  # Number of books or minutes to read
    unit = db.Column(db.String(20), nullable=False)  # 'books' or 'minutes'
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    image_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Participants through association table
    participants = db.relationship('ChildProfile', secondary=challenge_participants, lazy='subquery',
                                  backref=db.backref('challenges', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'goal': self.goal,
            'unit': self.unit,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'participants_count': len(self.participants)
        }

# Resource model
class Resource(db.Model):
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'article', 'video', 'printable', etc.
    category = db.Column(db.String(50), nullable=False)  # 'parent_tips', 'classroom_activities', etc.
    age_range = db.Column(db.String(20))
    file_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.type,
            'category': self.category,
            'age_range': self.age_range,
            'file_url': self.file_url,
            'thumbnail_url': self.thumbnail_url,
            'created_at': self.created_at.isoformat()
        }

# Learning Path model for AI-generated personalized learning journeys
class LearningPath(db.Model):
    __tablename__ = 'learning_paths'
    
    id = db.Column(db.Integer, primary_key=True)
    child_profile_id = db.Column(db.Integer, db.ForeignKey('child_profiles.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    current_stage = db.Column(db.Integer, default=1)
    total_stages = db.Column(db.Integer, nullable=False)
    progress_percentage = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    path_activities = db.relationship('PathActivity', backref='learning_path', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'child_profile_id': self.child_profile_id,
            'title': self.title,
            'description': self.description,
            'current_stage': self.current_stage,
            'total_stages': self.total_stages,
            'progress_percentage': self.progress_percentage,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }

# Path Activity model for activities in a learning path
class PathActivity(db.Model):
    __tablename__ = 'path_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    learning_path_id = db.Column(db.Integer, db.ForeignKey('learning_paths.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # 'reading', 'quiz', 'game', 'exercise'
    content_url = db.Column(db.String(255))
    stage_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'in-progress', 'completed'
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'learning_path_id': self.learning_path_id,
            'title': self.title,
            'description': self.description,
            'activity_type': self.activity_type,
            'content_url': self.content_url,
            'stage_number': self.stage_number,
            'status': self.status,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat()
        }

# Progress Assessment model for tracking learning progress
class ProgressAssessment(db.Model):
    __tablename__ = 'progress_assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    child_profile_id = db.Column(db.Integer, db.ForeignKey('child_profiles.id'), nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    reading_level = db.Column(db.String(20), nullable=False)
    reading_fluency_score = db.Column(db.Integer)
    comprehension_score = db.Column(db.Integer)
    vocabulary_score = db.Column(db.Integer)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'child_profile_id': self.child_profile_id,
            'assessment_date': self.assessment_date.isoformat(),
            'reading_level': self.reading_level,
            'reading_fluency_score': self.reading_fluency_score,
            'comprehension_score': self.comprehension_score,
            'vocabulary_score': self.vocabulary_score,
            'notes': self.notes
        }