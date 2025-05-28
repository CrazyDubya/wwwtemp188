"""Database models for temp188.com"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
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
    analysis_requests = db.relationship('AnalysisRequest', backref='user', lazy='dynamic')
    analysis_history = db.relationship('AnalysisHistory', backref='user', lazy='dynamic')
    contributions = db.relationship('UserContribution', backref='user', lazy='dynamic')
    badges = db.relationship('UserBadge', backref='user', lazy='dynamic')
    
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
    
    @property
    def analysis_count(self):
        """Total number of analyses performed by user"""
        return self.analysis_history.count()
    
    @property
    def contribution_points(self):
        """Total contribution points earned"""
        return db.session.query(db.func.sum(UserContribution.points)).filter_by(user_id=self.id).scalar() or 0
    
    @property
    def tier(self):
        """User tier based on activity"""
        if self.role == 'admin':
            return 'admin'
        elif self.analysis_count >= 100:
            return 'premium'
        elif self.analysis_count >= 10:
            return 'advanced'
        elif self.analysis_count >= 1:
            return 'basic'
        else:
            return 'new'
    
    def has_badge(self, badge_id):
        """Check if user has a specific badge"""
        return self.badges.filter_by(badge_id=badge_id).first() is not None
    
    def get_rate_limit(self):
        """Get rate limit based on user tier"""
        rate_limits = {
            'admin': 1000,      # Unlimited for admins
            'premium': 200,     # High limit for premium users
            'advanced': 100,    # Medium limit for advanced users
            'basic': 50,        # Standard limit for basic users
            'new': 25           # Starting limit for new users
        }
        return rate_limits.get(self.tier, 5)  # Default to 5 for anonymous
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

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

class AnalysisRequest(db.Model):
    """Track analysis requests for rate limiting"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for anonymous
    ip_address = db.Column(db.String(45), nullable=False)
    article_title = db.Column(db.String(500))
    analysis_type = db.Column(db.String(20))  # 'quick' or 'advanced'
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisRequest {self.id}: {self.analysis_type} by {self.user_id or "anonymous"}>'

class AnalysisHistory(db.Model):
    """Store analysis results and history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    article_title = db.Column(db.String(500), nullable=False)
    article_hash = db.Column(db.String(32))  # MD5 of content for cache invalidation
    model_used = db.Column(db.String(100))
    provider = db.Column(db.String(50))
    analysis_text = db.Column(db.Text)
    is_cached = db.Column(db.Boolean, default=False)
    admin_reviewed = db.Column(db.Boolean, default=False)
    quality_score = db.Column(db.Integer)  # 1-10 admin rating
    admin_notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AnalysisHistory {self.id}: {self.article_title}>'

class UserContribution(db.Model):
    """Track user contributions for gamification"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contribution_type = db.Column(db.String(50))  # 'analysis', 'review', 'feedback'
    points = db.Column(db.Integer, default=1)
    extra_data = db.Column(db.Text)  # JSON for additional data
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserContribution {self.id}: {self.contribution_type} by {self.user_id}>'

class UserBadge(db.Model):
    """User badges and achievements"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.String(50), nullable=False)  # Badge identifier
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserBadge {self.badge_id} for user {self.user_id}>'

class AnalysisCache(db.Model):
    """Cache high-quality analyses for reuse"""
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(64), unique=True)
    article_title = db.Column(db.String(500), nullable=False)
    article_hash = db.Column(db.String(32))  # MD5 of content
    analysis_text = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(100))
    provider = db.Column(db.String(50))
    quality_score = db.Column(db.Integer)  # Admin-assigned quality 1-5
    admin_notes = db.Column(db.Text)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Admin who approved
    approved_at = db.Column(db.DateTime)  # When approved
    hit_count = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    def __repr__(self):
        return f'<AnalysisCache {self.id}: {self.article_title}>'

class PageView(db.Model):
    """Track page views and user navigation"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    page_url = db.Column(db.String(500), nullable=False)
    page_title = db.Column(db.String(200))
    referrer = db.Column(db.String(500))
    session_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Performance metrics
    load_time = db.Column(db.Float)  # Page load time in seconds
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<PageView {self.page_url} at {self.timestamp}>'

class SearchQuery(db.Model):
    """Track user searches and queries"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(45))
    session_id = db.Column(db.String(100))
    query_text = db.Column(db.Text, nullable=False)
    query_type = db.Column(db.String(50))  # 'wikipedia_search', 'analysis_request', etc.
    results_count = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Search metadata
    filters_applied = db.Column(db.Text)  # JSON string of filters
    sort_order = db.Column(db.String(50))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<SearchQuery "{self.query_text[:50]}" at {self.timestamp}>'

class UserInteraction(db.Model):
    """Track user clicks, interactions, and engagement"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(45))
    session_id = db.Column(db.String(100))
    interaction_type = db.Column(db.String(50), nullable=False)  # 'click', 'download', 'share', etc.
    element_id = db.Column(db.String(100))  # DOM element ID
    element_text = db.Column(db.Text)  # Button text, link text, etc.
    page_url = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Interaction metadata
    extra_data = db.Column(db.Text)  # JSON string for additional data
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<UserInteraction {self.interaction_type} at {self.timestamp}>'

class AnalyticsSession(db.Model):
    """Track user sessions for analytics"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    page_views = db.Column(db.Integer, default=0)
    interactions = db.Column(db.Integer, default=0)
    searches = db.Column(db.Integer, default=0)
    analyses_performed = db.Column(db.Integer, default=0)
    
    # Session quality metrics
    bounce_rate = db.Column(db.Boolean, default=False)  # Single page visit
    duration_seconds = db.Column(db.Integer)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<AnalyticsSession {self.session_id} for user {self.user_id}>'

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