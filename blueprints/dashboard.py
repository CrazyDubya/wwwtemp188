"""User dashboard blueprint"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, WordCloud, User
from datetime import datetime, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard view"""
    # Get user statistics
    total_clouds = WordCloud.query.filter_by(user_id=current_user.id).count()
    public_clouds = WordCloud.query.filter_by(user_id=current_user.id, is_public=True).count()
    
    # Recent word clouds
    recent_clouds = WordCloud.query.filter_by(user_id=current_user.id).order_by(
        WordCloud.created_at.desc()
    ).limit(6).all()
    
    # Total views across all clouds
    total_views = db.session.query(func.sum(WordCloud.views)).filter_by(
        user_id=current_user.id
    ).scalar() or 0
    
    # Activity in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_activity = WordCloud.query.filter(
        WordCloud.user_id == current_user.id,
        WordCloud.created_at >= thirty_days_ago
    ).count()
    
    stats = {
        'total_clouds': total_clouds,
        'public_clouds': public_clouds,
        'total_views': total_views,
        'recent_activity': recent_activity
    }
    
    return render_template('dashboard/index.html', 
                         stats=stats, 
                         recent_clouds=recent_clouds)

@dashboard_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('dashboard/settings.html')

@dashboard_bp.route('/activity')
@login_required
def activity():
    """User activity timeline"""
    # Get all user's word clouds with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    activities = WordCloud.query.filter_by(user_id=current_user.id).order_by(
        WordCloud.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('dashboard/activity.html', activities=activities)

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    """User analytics and insights"""
    # Calculate various analytics
    
    # Word clouds by type
    cloud_types = db.session.query(
        WordCloud.cloud_type, 
        func.count(WordCloud.id)
    ).filter_by(user_id=current_user.id).group_by(WordCloud.cloud_type).all()
    
    # Word clouds over time (last 12 months)
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)
    monthly_data = []
    
    for i in range(12):
        start_date = twelve_months_ago + timedelta(days=30*i)
        end_date = start_date + timedelta(days=30)
        
        count = WordCloud.query.filter(
            WordCloud.user_id == current_user.id,
            WordCloud.created_at >= start_date,
            WordCloud.created_at < end_date
        ).count()
        
        monthly_data.append({
            'month': start_date.strftime('%b %Y'),
            'count': count
        })
    
    # Most viewed clouds
    top_clouds = WordCloud.query.filter_by(user_id=current_user.id).order_by(
        WordCloud.views.desc()
    ).limit(5).all()
    
    analytics_data = {
        'cloud_types': dict(cloud_types),
        'monthly_data': monthly_data,
        'top_clouds': top_clouds
    }
    
    return render_template('dashboard/analytics.html', analytics=analytics_data)

@dashboard_bp.route('/admin')
@login_required
def admin():
    """Admin dashboard - only for admin users"""
    if current_user.role != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Get platform statistics
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'total_wordclouds': WordCloud.query.count(),
        'public_wordclouds': WordCloud.query.filter_by(is_public=True).count()
    }
    
    # Recent signups
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Recent word clouds
    recent_clouds = WordCloud.query.order_by(WordCloud.created_at.desc()).limit(10).all()
    
    return render_template('dashboard/admin.html', 
                         stats=stats,
                         recent_users=recent_users,
                         recent_clouds=recent_clouds)