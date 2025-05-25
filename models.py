"""Database models for temp188.com"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model with support for OAuth and local auth"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50))  # 'github', 'google', etc.
    oauth_id = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    
    # User metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default='user')  # 'user', 'admin'
    
    # Relationships
    wordclouds = db.relationship('WordCloud', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_url': self.avatar_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'role': self.role
        }

class WordCloud(db.Model):
    """Word cloud storage model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Word cloud metadata
    title = db.Column(db.String(200))
    text_content = db.Column(db.Text)
    config = db.Column(db.Text)  # JSON string of configuration
    
    # File paths
    file_path = db.Column(db.String(500))
    thumbnail_path = db.Column(db.String(500))
    
    # Timestamps and stats
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    
    # Word cloud type
    cloud_type = db.Column(db.String(50))  # 'quick', 'shaped', 'advanced'
    
    def __repr__(self):
        return f'<WordCloud {self.id}: {self.title}>'
    
    def get_config(self):
        """Return config as dictionary"""
        if self.config:
            return json.loads(self.config)
        return {}
    
    def set_config(self, config_dict):
        """Set config from dictionary"""
        self.config = json.dumps(config_dict)

class Project(db.Model):
    """Project/tool definitions"""
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))
    color = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.slug}>'

class UserSession(db.Model):
    """Track user sessions for security"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    session_token = db.Column(db.String(255), unique=True)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

def init_db():
    """Initialize database with tables and default data"""
    db.create_all()
    
    # Create default projects if they don't exist
    if not Project.query.filter_by(slug='wordcloud').first():
        wordcloud_project = Project(
            slug='wordcloud',
            name='WordCloud Studio',
            description='Create beautiful word clouds with multiple styles',
            icon='fa-cloud',
            color='indigo',
            is_active=True,
            order_index=1
        )
        db.session.add(wordcloud_project)
        db.session.commit()
        print("Created default WordCloud project")
    
    print("Database initialized successfully!")