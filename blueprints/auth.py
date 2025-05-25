"""Authentication blueprint for temp188.com"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import datetime
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with local and OAuth options"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        # Validation
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters')
        
        if not email or '@' not in email:
            errors.append('Valid email required')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters')
        
        if password != password2:
            errors.append('Passwords do not match')
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if errors:
            for error in errors:
                flash(error, 'error')
        else:
            # Create new user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.commit()
            
            # Log them in
            login_user(user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard.index'))
    
    return render_template('auth/signup.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    if request.method == 'POST':
        # Update username if changed
        new_username = request.form.get('username')
        if new_username and new_username != current_user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Username already taken', 'error')
            else:
                current_user.username = new_username
        
        # Update email if changed
        new_email = request.form.get('email')
        if new_email and new_email != current_user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Email already in use', 'error')
            else:
                current_user.email = new_email
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            current_password = request.form.get('current_password')
            if not check_password_hash(current_user.password_hash, current_password):
                flash('Current password incorrect', 'error')
            else:
                current_user.password_hash = generate_password_hash(new_password)
                flash('Password updated', 'success')
        
        db.session.commit()
        flash('Profile updated', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html', user=current_user)

# OAuth routes would go here (GitHub, Google, etc.)
@auth_bp.route('/oauth/github')
def oauth_github():
    """Initiate GitHub OAuth"""
    # TODO: Implement GitHub OAuth
    flash('GitHub OAuth coming soon!', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/oauth/google')
def oauth_google():
    """Initiate Google OAuth"""
    # TODO: Implement Google OAuth
    flash('Google OAuth coming soon!', 'info')
    return redirect(url_for('auth.login'))