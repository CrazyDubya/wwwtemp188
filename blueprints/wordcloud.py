"""
Word Cloud blueprint - consolidates all word cloud functionality
Powered by the word_cloud library by Andreas Mueller
https://github.com/amueller/word_cloud
Licensed under MIT License
"""

from flask import Blueprint, render_template, request, send_file, redirect, url_for, session, abort, flash, jsonify, make_response
from flask_login import login_required, current_user
from wordcloud import WordCloud as WC, STOPWORDS, ImageColorGenerator, get_single_color_func
from models import db, WordCloud as WordCloudModel
import os
import uuid
import time
from datetime import datetime, timedelta
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import io
import base64
from collections import Counter
import re
import colorsys
import random

wordcloud_bp = Blueprint('wordcloud', __name__)

# Configuration
WORDCLOUD_FOLDER = '/var/temp188.com/static/wordclouds'
TEMP_FOLDER = '/var/temp188.com/temp_wordclouds'
MASK_FOLDER = '/var/temp188.com/static/masks'
FONT_FOLDER = '/var/temp188.com/static/fonts'

# Ensure directories exist
for folder in [WORDCLOUD_FOLDER, TEMP_FOLDER, MASK_FOLDER, FONT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Enhanced color schemes with ALL matplotlib colormaps organized by category
COLOR_SCHEMES = {
    # Perceptually Uniform Sequential
    'viridis': {'colormap': 'viridis', 'background': 'white', 'category': 'Sequential'},
    'plasma': {'colormap': 'plasma', 'background': 'white', 'category': 'Sequential'},
    'inferno': {'colormap': 'inferno', 'background': 'white', 'category': 'Sequential'},
    'magma': {'colormap': 'magma', 'background': 'white', 'category': 'Sequential'},
    'cividis': {'colormap': 'cividis', 'background': 'white', 'category': 'Sequential'},
    
    # Sequential (Single Hue)
    'blues': {'colormap': 'Blues', 'background': 'white', 'category': 'Sequential'},
    'greens': {'colormap': 'Greens', 'background': 'white', 'category': 'Sequential'},
    'reds': {'colormap': 'Reds', 'background': 'white', 'category': 'Sequential'},
    'purples': {'colormap': 'Purples', 'background': 'white', 'category': 'Sequential'},
    'oranges': {'colormap': 'Oranges', 'background': 'white', 'category': 'Sequential'},
    'greys': {'colormap': 'Greys', 'background': 'white', 'category': 'Sequential'},
    
    # Sequential (Multi-hue)
    'turbo': {'colormap': 'turbo', 'background': 'white', 'category': 'Multi-hue'},
    'ylgnbu': {'colormap': 'YlGnBu', 'background': 'white', 'category': 'Multi-hue'},
    'ylorbr': {'colormap': 'YlOrBr', 'background': 'white', 'category': 'Multi-hue'},
    'gnbu': {'colormap': 'GnBu', 'background': 'white', 'category': 'Multi-hue'},
    'orrd': {'colormap': 'OrRd', 'background': 'white', 'category': 'Multi-hue'},
    'pubu': {'colormap': 'PuBu', 'background': 'white', 'category': 'Multi-hue'},
    'purd': {'colormap': 'PuRd', 'background': 'white', 'category': 'Multi-hue'},
    'rdpu': {'colormap': 'RdPu', 'background': 'white', 'category': 'Multi-hue'},
    
    # Diverging
    'rdylbu': {'colormap': 'RdYlBu', 'background': 'white', 'category': 'Diverging'},
    'spectral': {'colormap': 'Spectral', 'background': 'white', 'category': 'Diverging'},
    'coolwarm': {'colormap': 'coolwarm', 'background': 'white', 'category': 'Diverging'},
    'bwr': {'colormap': 'bwr', 'background': 'white', 'category': 'Diverging'},
    'seismic': {'colormap': 'seismic', 'background': 'white', 'category': 'Diverging'},
    'twilight': {'colormap': 'twilight', 'background': '#000033', 'category': 'Diverging'},
    'twilight_shifted': {'colormap': 'twilight_shifted', 'background': '#000033', 'category': 'Diverging'},
    
    # Qualitative
    'set3': {'colormap': 'Set3', 'background': 'white', 'category': 'Qualitative'},
    'set2': {'colormap': 'Set2', 'background': 'white', 'category': 'Qualitative'},
    'set1': {'colormap': 'Set1', 'background': 'white', 'category': 'Qualitative'},
    'pastel1': {'colormap': 'Pastel1', 'background': 'white', 'category': 'Qualitative'},
    'pastel2': {'colormap': 'Pastel2', 'background': 'white', 'category': 'Qualitative'},
    'dark2': {'colormap': 'Dark2', 'background': 'white', 'category': 'Qualitative'},
    'accent': {'colormap': 'Accent', 'background': 'white', 'category': 'Qualitative'},
    'tab10': {'colormap': 'tab10', 'background': 'white', 'category': 'Qualitative'},
    'tab20': {'colormap': 'tab20', 'background': 'white', 'category': 'Qualitative'},
    
    # Cyclic
    'hsv': {'colormap': 'hsv', 'background': 'white', 'category': 'Cyclic'},
    'twilight': {'colormap': 'twilight', 'background': 'white', 'category': 'Cyclic'},
    
    # Special/Themed
    'ocean': {'colormap': 'ocean', 'background': '#f0f8ff', 'category': 'Special'},
    'gist_earth': {'colormap': 'gist_earth', 'background': '#f5f5dc', 'category': 'Special'},
    'terrain': {'colormap': 'terrain', 'background': '#f0f8ff', 'category': 'Special'},
    'gist_stern': {'colormap': 'gist_stern', 'background': 'black', 'category': 'Special'},
    'gnuplot': {'colormap': 'gnuplot', 'background': 'white', 'category': 'Special'},
    'gnuplot2': {'colormap': 'gnuplot2', 'background': 'white', 'category': 'Special'},
    'cubehelix': {'colormap': 'cubehelix', 'background': 'white', 'category': 'Special'},
    'brg': {'colormap': 'brg', 'background': 'white', 'category': 'Special'},
    'gist_rainbow': {'colormap': 'gist_rainbow', 'background': 'white', 'category': 'Special'},
    'rainbow': {'colormap': 'rainbow', 'background': 'white', 'category': 'Special'},
    'jet': {'colormap': 'jet', 'background': 'white', 'category': 'Special'},
    'gist_ncar': {'colormap': 'gist_ncar', 'background': 'white', 'category': 'Special'},
    
    # Seasonal
    'spring': {'colormap': 'spring', 'background': '#fffaf0', 'category': 'Seasonal'},
    'summer': {'colormap': 'summer', 'background': '#fffacd', 'category': 'Seasonal'},
    'autumn': {'colormap': 'autumn', 'background': '#fffaf0', 'category': 'Seasonal'},
    'winter': {'colormap': 'winter', 'background': '#f0f8ff', 'category': 'Seasonal'},
    
    # Temperature
    'hot': {'colormap': 'hot', 'background': '#fff5ee', 'category': 'Temperature'},
    'cool': {'colormap': 'cool', 'background': '#f0ffff', 'category': 'Temperature'},
    'coolwarm': {'colormap': 'coolwarm', 'background': 'white', 'category': 'Temperature'},
    
    # Monochrome
    'gray': {'colormap': 'gray', 'background': 'white', 'category': 'Monochrome'},
    'bone': {'colormap': 'bone', 'background': 'white', 'category': 'Monochrome'},
    'pink': {'colormap': 'pink', 'background': 'white', 'category': 'Monochrome'},
    'copper': {'colormap': 'copper', 'background': 'white', 'category': 'Monochrome'},
    
    # Custom Named Themes
    'patriotic': {'colormap': 'bwr', 'background': 'white', 'category': 'Themed'},
    'sunset': {'colormap': 'hot', 'background': '#fff5ee', 'category': 'Themed'},
    'forest': {'colormap': 'YlGn', 'background': '#f5fffa', 'category': 'Themed'},
    'galaxy': {'colormap': 'twilight', 'background': '#000033', 'category': 'Themed'},
    'neon': {'colormap': 'plasma', 'background': '#000000', 'category': 'Themed'},
    'pastel': {'colormap': 'Pastel1', 'background': '#ffffff', 'category': 'Themed'},
    'monochrome': {'colormap': 'gray', 'background': 'white', 'category': 'Themed'},
}

# Custom color functions
def grey_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """Grey color function with random lightness"""
    return f"hsl(0, 0%, {random.randint(60, 100)}%)"

def single_color_func(hue):
    """Create a single color function with specified hue"""
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return f"hsl({hue}, 70%, {random.randint(40, 70)}%)"
    return color_func

def rainbow_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """Rainbow color function based on position"""
    hue = int(360 * position[0] / 800)  # Assuming 800 width
    return f"hsl({hue}, 80%, 50%)"

def size_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """Color based on word size - bigger words are darker"""
    # Normalize font size to 0-1 range
    lightness = 90 - int((font_size / 150) * 50)  # Assuming max font size 150
    return f"hsl(220, 70%, {lightness}%)"

# Predefined shape masks with categories
SHAPE_TEMPLATES = {
    # Basic Shapes
    'circle': {'file': 'circle_mask.png', 'category': 'Basic'},
    'square': {'file': 'square_mask.png', 'category': 'Basic'},
    'triangle': {'file': 'triangle_mask.png', 'category': 'Basic'},
    'diamond': {'file': 'diamond_mask.png', 'category': 'Basic'},
    'hexagon': {'file': 'hexagon_mask.png', 'category': 'Basic'},
    'octagon': {'file': 'octagon_mask.png', 'category': 'Basic'},
    'pentagon': {'file': 'pentagon_mask.png', 'category': 'Basic'},
    'oval': {'file': 'oval_mask.png', 'category': 'Basic'},
    
    # Nature & Objects
    'heart': {'file': 'heart_mask.png', 'category': 'Nature'},
    'star': {'file': 'star_mask.png', 'category': 'Nature'},
    'cloud': {'file': 'cloud_mask.png', 'category': 'Nature'},
    'tree': {'file': 'tree_mask.png', 'category': 'Nature'},
    'flower': {'file': 'flower_mask.png', 'category': 'Nature'},
    'butterfly': {'file': 'butterfly_mask.png', 'category': 'Nature'},
    'moon': {'file': 'moon_mask.png', 'category': 'Nature'},
    'sun': {'file': 'sun_mask.png', 'category': 'Nature'},
    
    # Communication
    'speech_bubble': {'file': 'speech_bubble_mask.png', 'category': 'Communication'},
    'thought_bubble': {'file': 'thought_bubble_mask.png', 'category': 'Communication'},
    'chat_box': {'file': 'chat_box_mask.png', 'category': 'Communication'},
    'comment': {'file': 'comment_mask.png', 'category': 'Communication'},
    
    # Social Media
    'twitter': {'file': 'twitter_mask.png', 'category': 'Social'},
    'facebook': {'file': 'facebook_mask.png', 'category': 'Social'},
    'instagram': {'file': 'instagram_mask.png', 'category': 'Social'},
    'youtube': {'file': 'youtube_mask.png', 'category': 'Social'},
    'tiktok': {'file': 'tiktok_mask.png', 'category': 'Social'},
    'linkedin': {'file': 'linkedin_mask.png', 'category': 'Social'},
    
    # Symbols
    'thumbs_up': {'file': 'thumbs_up_mask.png', 'category': 'Symbols'},
    'peace': {'file': 'peace_mask.png', 'category': 'Symbols'},
    'infinity': {'file': 'infinity_mask.png', 'category': 'Symbols'},
    'yin_yang': {'file': 'yin_yang_mask.png', 'category': 'Symbols'},
    
    # Animals
    'cat': {'file': 'cat_mask.png', 'category': 'Animals'},
    'dog': {'file': 'dog_mask.png', 'category': 'Animals'},
    'bird': {'file': 'bird_mask.png', 'category': 'Animals'},
    'fish': {'file': 'fish_mask.png', 'category': 'Animals'},
    
    # Tech & Gaming
    'monitor': {'file': 'monitor_mask.png', 'category': 'Tech'},
    'phone': {'file': 'phone_mask.png', 'category': 'Tech'},
    'gamepad': {'file': 'gamepad_mask.png', 'category': 'Tech'},
    'keyboard': {'file': 'keyboard_mask.png', 'category': 'Tech'},
    
    # Maps & Geography
    'usa': {'file': 'usa_mask.png', 'category': 'Geography'},
    'world': {'file': 'world_mask.png', 'category': 'Geography'},
    'europe': {'file': 'europe_mask.png', 'category': 'Geography'},
    'africa': {'file': 'africa_mask.png', 'category': 'Geography'},
}

# Feature sets organized by utility
FEATURE_SETS = {
    'text_processing': {
        'name': 'Text Processing',
        'features': [
            'stopwords', 'regexp', 'normalize_plurals', 'collocations',
            'collocation_threshold', 'include_numbers', 'min_word_length'
        ],
        'description': 'Control how text is analyzed and processed'
    },
    'layout_control': {
        'name': 'Layout Control',
        'features': [
            'prefer_horizontal', 'repeat', 'relative_scaling', 'ranks_only',
            'margin', 'scale'
        ],
        'description': 'Fine-tune word placement and arrangement'
    },
    'typography': {
        'name': 'Typography',
        'features': [
            'font_path', 'font_step', 'min_font_size', 'max_font_size'
        ],
        'description': 'Customize fonts and text sizing'
    },
    'visual_styling': {
        'name': 'Visual Styling',
        'features': [
            'colormap', 'color_func', 'background_color', 'mode',
            'contour_width', 'contour_color'
        ],
        'description': 'Control colors and visual effects'
    },
    'output_options': {
        'name': 'Output Options',
        'features': [
            'width', 'height', 'max_words', 'mask', 'random_state'
        ],
        'description': 'Set dimensions and output parameters'
    },
    'export_formats': {
        'name': 'Export Formats',
        'methods': [
            'to_image', 'to_array', 'to_file', 'to_svg'
        ],
        'description': 'Export in multiple formats including SVG'
    },
    'color_functions': {
        'name': 'Color Functions',
        'functions': [
            'ImageColorGenerator', 'get_single_color_func',
            'grey_color_func', 'rainbow_color_func', 'size_color_func'
        ],
        'description': 'Advanced color customization functions'
    }
}

@wordcloud_bp.route('/')
def index():
    """Word cloud studio homepage"""
    return render_template('wordcloud/index.html')

@wordcloud_bp.route('/quick')
def quick_generator():
    """Quick word cloud generator (red/white/blue)"""
    return render_template('wordcloud/quick.html')

@wordcloud_bp.route('/quick/generate', methods=['POST'])
def quick_generate():
    """Generate quick word cloud with enhanced features"""
    words = request.form.get('words', '').splitlines()
    weights = request.form.get('weights', '').splitlines()
    color_scheme = request.form.get('color_scheme', 'patriotic')
    
    if not words:
        flash('Please enter some words', 'error')
        return redirect(url_for('wordcloud.quick_generator'))
    
    # Clean and process words
    words = [word.strip() for word in words if word.strip()]
    
    # Process weights
    if len(weights) < len(words):
        weights += ['5'] * (len(words) - len(weights))
    
    # Create frequency dictionary
    word_freq = {}
    for word, weight in zip(words, weights):
        try:
            weight_int = int(weight)
        except:
            weight_int = 5
        word_freq[word] = weight_int
    
    # Generate three variations with different parameters
    session_id = str(uuid.uuid4())
    clouds = []
    
    # Get color scheme
    scheme = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['patriotic'])
    
    variations = [
        {'max_font_size': 100, 'relative_scaling': 0.5, 'prefer_horizontal': 0.7},
        {'max_font_size': 120, 'relative_scaling': 0.3, 'prefer_horizontal': 0.9},
        {'max_font_size': 80, 'relative_scaling': 0.7, 'prefer_horizontal': 0.5}
    ]
    
    for i, params in enumerate(variations):
        filename = f"quick_{session_id}_{i}.png"
        filepath = os.path.join(TEMP_FOLDER, filename)
        
        wc = WC(width=1200, height=600,
               background_color=scheme['background'],
               colormap=scheme['colormap'],
               max_words=150,
               relative_scaling=params['relative_scaling'],
               min_font_size=10,
               max_font_size=params['max_font_size'],
               prefer_horizontal=params['prefer_horizontal'],
               margin=10,
               contour_width=1,
               contour_color='steelblue' if scheme['background'] != '#000000' else 'white'
        ).generate_from_frequencies(word_freq)
        
        wc.to_file(filepath)
        clouds.append(filename)
    
    # Store in session for display
    session['quick_clouds'] = {
        'files': clouds,
        'created': time.time(),
        'session_id': session_id,
        'color_scheme': color_scheme
    }
    
    # If user is logged in, save to database
    if current_user.is_authenticated:
        for i, cloud_file in enumerate(clouds):
            wc_model = WordCloudModel(
                user_id=current_user.id,
                title=f"Quick Cloud {i+1} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                text_content=' '.join(words),
                file_path=f'/temp_wordclouds/{cloud_file}',
                cloud_type='quick'
            )
            wc_model.set_config({
                'colormap': scheme['colormap'],
                'color_scheme': color_scheme,
                'weights': dict(zip(words, weights)),
                'variation': i
            })
            db.session.add(wc_model)
        db.session.commit()
    
    return redirect(url_for('wordcloud.quick_display'))

@wordcloud_bp.route('/quick/display')
def quick_display():
    """Display generated quick word clouds"""
    cloud_data = session.get('quick_clouds')
    if not cloud_data:
        flash('No word clouds found. Please generate some first.', 'error')
        return redirect(url_for('wordcloud.quick_generator'))
    
    # Check if clouds are expired (1 hour)
    if time.time() - cloud_data['created'] > 3600:
        flash('Word clouds expired. Please generate new ones.', 'error')
        return redirect(url_for('wordcloud.quick_generator'))
    
    return render_template('wordcloud/quick_display.html', clouds=cloud_data['files'])

@wordcloud_bp.route('/shapes')
def custom_shapes():
    """Custom shape word cloud generator"""
    return render_template('wordcloud/shapes.html')

@wordcloud_bp.route('/shapes/generate', methods=['POST'])
def shapes_generate():
    """Generate shaped word cloud"""
    text = request.form.get('text', '')
    shape = request.form.get('shape', 'circle')
    color_scheme = request.form.get('color_scheme', 'ocean')
    custom_mask = request.files.get('custom_mask')
    
    if not text:
        flash('Please enter some text', 'error')
        return redirect(url_for('wordcloud.custom_shapes'))
    
    # Process text to get word frequencies
    words = re.findall(r'\b\w+\b', text.lower())
    word_freq = Counter(words)
    
    # Remove common stopwords
    custom_stopwords = set(STOPWORDS)
    custom_stopwords.update(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'])
    word_freq = {word: freq for word, freq in word_freq.items() if word not in custom_stopwords}
    
    # Load mask
    mask = None
    if custom_mask and custom_mask.filename:
        # Save custom mask temporarily
        mask_id = str(uuid.uuid4())
        mask_ext = os.path.splitext(custom_mask.filename)[1]
        temp_mask_path = os.path.join(TEMP_FOLDER, f'mask_{mask_id}{mask_ext}')
        custom_mask.save(temp_mask_path)
        
        # Load and process mask
        mask_image = Image.open(temp_mask_path).convert('RGBA')
        mask = np.array(mask_image)
        
        # Clean up temp mask
        os.remove(temp_mask_path)
    elif shape in SHAPE_TEMPLATES:
        # Use predefined shape
        mask_path = os.path.join(MASK_FOLDER, SHAPE_TEMPLATES[shape]['file'])
        if os.path.exists(mask_path):
            mask_image = Image.open(mask_path).convert('L')
            mask = np.array(mask_image)
    
    # Get color scheme
    scheme = COLOR_SCHEMES.get(color_scheme, COLOR_SCHEMES['ocean'])
    
    # Generate word cloud
    session_id = str(uuid.uuid4())
    filename = f"shaped_{session_id}.png"
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    wc_params = {
        'width': 800,
        'height': 800,
        'background_color': scheme['background'],
        'colormap': scheme['colormap'],
        'max_words': 200,
        'relative_scaling': 0.5,
        'min_font_size': 4,
        'contour_width': 2,
        'contour_color': 'steelblue',
        'prefer_horizontal': 0.6
    }
    
    if mask is not None:
        wc_params['mask'] = mask
        wc_params['contour_width'] = 3
    
    wc = WC(**wc_params).generate_from_frequencies(word_freq)
    
    # If using image colors from mask
    if request.form.get('use_image_colors') == 'true' and mask is not None:
        image_colors = ImageColorGenerator(mask)
        wc.recolor(color_func=image_colors)
    
    wc.to_file(filepath)
    
    # Store in session
    session['shaped_cloud'] = {
        'file': filename,
        'created': time.time(),
        'shape': shape,
        'color_scheme': color_scheme
    }
    
    # Save to database if logged in
    if current_user.is_authenticated:
        wc_model = WordCloudModel(
            user_id=current_user.id,
            title=f"Shaped Cloud ({shape}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            text_content=text[:1000],  # Store first 1000 chars
            file_path=f'/temp_wordclouds/{filename}',
            cloud_type='shaped'
        )
        wc_model.set_config({
            'shape': shape,
            'color_scheme': color_scheme,
            'word_count': len(word_freq)
        })
        db.session.add(wc_model)
        db.session.commit()
    
    return redirect(url_for('wordcloud.shapes_display'))

@wordcloud_bp.route('/shapes/display')
def shapes_display():
    """Display generated shaped word cloud"""
    cloud_data = session.get('shaped_cloud')
    if not cloud_data:
        flash('No shaped cloud found. Please generate one first.', 'error')
        return redirect(url_for('wordcloud.custom_shapes'))
    
    return render_template('wordcloud/shapes_display.html', cloud=cloud_data)

@wordcloud_bp.route('/studio')
def advanced_studio():
    """Advanced word cloud studio"""
    return render_template('wordcloud/studio.html')

@wordcloud_bp.route('/studio/generate', methods=['POST'])
def studio_generate():
    """Generate advanced word cloud with full parameter control"""
    # Get form data
    text = request.form.get('text', '')
    upload_file = request.files.get('text_file')
    
    # Advanced parameters
    width = int(request.form.get('width', 1600))
    height = int(request.form.get('height', 900))
    max_words = int(request.form.get('max_words', 200))
    min_font_size = int(request.form.get('min_font_size', 4))
    max_font_size = int(request.form.get('max_font_size', 150))
    font_step = int(request.form.get('font_step', 1) or 1)
    prefer_horizontal = float(request.form.get('prefer_horizontal', 0.9))
    relative_scaling = float(request.form.get('relative_scaling', 0.5))
    
    # Visual parameters
    background_color = request.form.get('background_color', 'white')
    colormap = request.form.get('colormap', 'viridis')
    contour_width = int(request.form.get('contour_width', 0))
    contour_color = request.form.get('contour_color', 'steelblue')
    margin = int(request.form.get('margin', 2))
    
    # Text processing parameters
    include_numbers = request.form.get('include_numbers') == 'true'
    collocations = request.form.get('collocations') == 'true'
    normalize_plurals = request.form.get('normalize_plurals') == 'true'
    repeat_words = request.form.get('repeat') == 'true'
    min_word_length = int(request.form.get('min_word_length', 3))
    
    # Get text from file if uploaded
    if upload_file and upload_file.filename:
        text = upload_file.read().decode('utf-8', errors='ignore')
    
    if not text:
        flash('Please enter text or upload a file', 'error')
        return redirect(url_for('wordcloud.advanced_studio'))
    
    # Process text
    if not include_numbers:
        text = re.sub(r'\b\d+\b', '', text)
    
    # Custom stopwords
    custom_stopwords = set(STOPWORDS)
    additional_stopwords = request.form.get('stopwords', '').split(',')
    custom_stopwords.update([sw.strip() for sw in additional_stopwords if sw.strip()])
    
    # Generate word cloud
    session_id = str(uuid.uuid4())
    filename = f"studio_{session_id}.png"
    filepath = os.path.join(TEMP_FOLDER, filename)
    
    # Font handling
    font_path = None
    custom_font = request.files.get('custom_font')
    if custom_font and custom_font.filename:
        font_id = str(uuid.uuid4())
        font_ext = os.path.splitext(custom_font.filename)[1]
        font_path = os.path.join(FONT_FOLDER, f'font_{font_id}{font_ext}')
        custom_font.save(font_path)
    
    # Mask handling
    mask = None
    mask_file = request.files.get('mask_file')
    if mask_file and mask_file.filename:
        mask_image = Image.open(mask_file).convert('RGBA')
        mask = np.array(mask_image)
    
    # Create word cloud with try/except for better error handling
    try:
        wc_params = {
            'width': width,
            'height': height,
            'max_words': max_words,
            'min_font_size': min_font_size,
            'max_font_size': max_font_size,
            'font_step': font_step,
            'prefer_horizontal': prefer_horizontal,
            'relative_scaling': relative_scaling,
            'background_color': background_color,
            'colormap': colormap,
            'stopwords': custom_stopwords,
            'contour_width': contour_width,
            'contour_color': contour_color,
            'margin': margin,
            'collocations': collocations,
            'normalize_plurals': normalize_plurals,
            'repeat': repeat_words
        }
        
        # Add optional parameters
        if font_path:
            wc_params['font_path'] = font_path
        if mask is not None:
            wc_params['mask'] = mask
            
        wc = WC(**wc_params).generate(text)
    except Exception as e:
        flash(f'Error generating word cloud: {str(e)}', 'error')
        return redirect(url_for('wordcloud.advanced_studio'))
    
    # Generate analytics
    word_freq = wc.words_
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    
    # Skip matplotlib plot for now to avoid issues
    plot_data = None
    
    # Save word cloud
    wc.to_file(filepath)
    
    # Clean up temporary font if used
    if font_path and os.path.exists(font_path):
        os.remove(font_path)
    
    # Store in session
    session['studio_cloud'] = {
        'file': filename,
        'created': time.time(),
        'analytics': {
            'total_words': len(word_freq),
            'unique_words': len(set(text.split())),
            'top_words': top_words,
            'plot': plot_data
        },
        'parameters': {
            'width': width,
            'height': height,
            'colormap': colormap,
            'max_words': max_words
        }
    }
    
    # Save to database if logged in
    if current_user.is_authenticated:
        wc_model = WordCloudModel(
            user_id=current_user.id,
            title=f"Studio Cloud - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            text_content=text[:1000],
            file_path=f'/temp_wordclouds/{filename}',
            cloud_type='studio'
        )
        wc_model.set_config({
            'parameters': session['studio_cloud']['parameters'],
            'word_count': len(word_freq),
            'unique_words': len(set(text.split()))
        })
        db.session.add(wc_model)
        db.session.commit()
    
    return redirect(url_for('wordcloud.studio_display'))

@wordcloud_bp.route('/studio/display')
def studio_display():
    """Display advanced studio word cloud with analytics"""
    cloud_data = session.get('studio_cloud')
    if not cloud_data:
        flash('No studio cloud found. Please generate one first.', 'error')
        return redirect(url_for('wordcloud.advanced_studio'))
    
    return render_template('wordcloud/studio_display.html', cloud=cloud_data)

@wordcloud_bp.route('/download/<filename>')
def download(filename):
    """Download word cloud image"""
    # Security check - ensure filename is safe
    if '..' in filename or '/' in filename:
        abort(403)
    
    # Check if file exists in temp folder
    temp_path = os.path.join(TEMP_FOLDER, filename)
    if os.path.exists(temp_path):
        return send_file(temp_path, as_attachment=True)
    
    # Check if file exists in permanent folder
    perm_path = os.path.join(WORDCLOUD_FOLDER, filename)
    if os.path.exists(perm_path):
        return send_file(perm_path, as_attachment=True)
    
    abort(404)

@wordcloud_bp.route('/gallery')
def gallery():
    """Public word cloud gallery"""
    public_clouds = WordCloudModel.query.filter_by(is_public=True).order_by(
        WordCloudModel.created_at.desc()
    ).limit(50).all()
    
    return render_template('wordcloud/gallery.html', clouds=public_clouds)

@wordcloud_bp.route('/my-clouds')
@login_required
def my_clouds():
    """User's word cloud collection"""
    user_clouds = WordCloudModel.query.filter_by(user_id=current_user.id).order_by(
        WordCloudModel.created_at.desc()
    ).all()
    
    return render_template('wordcloud/my_clouds.html', clouds=user_clouds)

@wordcloud_bp.route('/delete/<int:cloud_id>', methods=['POST'])
@login_required
def delete_cloud(cloud_id):
    """Delete a word cloud"""
    cloud = WordCloudModel.query.get_or_404(cloud_id)
    
    # Check ownership
    if cloud.user_id != current_user.id and current_user.role != 'admin':
        abort(403)
    
    # Delete file if exists
    if cloud.file_path:
        try:
            full_path = '/var/temp188.com' + cloud.file_path
            if os.path.exists(full_path):
                os.remove(full_path)
        except:
            pass
    
    db.session.delete(cloud)
    db.session.commit()
    
    flash('Word cloud deleted', 'success')
    return redirect(url_for('wordcloud.my_clouds'))

@wordcloud_bp.route('/api/stats')
def api_stats():
    """Get word cloud statistics"""
    stats = {
        'total_clouds': WordCloudModel.query.count(),
        'public_clouds': WordCloudModel.query.filter_by(is_public=True).count(),
        'total_users': db.session.query(WordCloudModel.user_id).distinct().count()
    }
    
    if current_user.is_authenticated:
        stats['my_clouds'] = WordCloudModel.query.filter_by(user_id=current_user.id).count()
    
    return jsonify(stats)

@wordcloud_bp.route('/api/generate', methods=['POST'])
def api_generate():
    """API endpoint for generating word clouds programmatically"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400
    
    # Extract parameters with defaults
    text = data['text']
    width = data.get('width', 800)
    height = data.get('height', 400)
    colormap = data.get('colormap', 'viridis')
    background_color = data.get('background_color', 'white')
    max_words = data.get('max_words', 100)
    
    try:
        # Generate word cloud
        wc = WC(
            width=width,
            height=height,
            background_color=background_color,
            colormap=colormap,
            max_words=max_words
        ).generate(text)
        
        # Save to buffer
        img_buffer = io.BytesIO()
        wc.to_image().save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Encode to base64
        img_data = base64.b64encode(img_buffer.read()).decode()
        
        # Get word frequencies
        word_freq = wc.words_
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_data}',
            'word_count': len(word_freq),
            'top_words': sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@wordcloud_bp.route('/api/color-schemes')
def api_color_schemes():
    """Get available color schemes"""
    return jsonify({
        'schemes': list(COLOR_SCHEMES.keys()),
        'details': COLOR_SCHEMES
    })

@wordcloud_bp.route('/api/shapes')
def api_shapes():
    """Get available shape templates"""
    return jsonify({
        'shapes': list(SHAPE_TEMPLATES.keys()),
        'shapes_by_category': {
            category: [name for name, info in SHAPE_TEMPLATES.items() if info['category'] == category]
            for category in set(info['category'] for info in SHAPE_TEMPLATES.values())
        },
        'custom_upload': True
    })

@wordcloud_bp.route('/color-showcase')
def color_showcase():
    """Display all available color schemes"""
    # Group color schemes by category
    schemes_by_category = {}
    for name, info in COLOR_SCHEMES.items():
        category = info.get('category', 'Other')
        if category not in schemes_by_category:
            schemes_by_category[category] = []
        schemes_by_category[category].append({
            'name': name,
            'colormap': info['colormap'],
            'background': info['background']
        })
    
    return render_template('wordcloud/color_showcase.html', 
                         schemes_by_category=schemes_by_category,
                         total_schemes=len(COLOR_SCHEMES))

@wordcloud_bp.route('/masks-showcase')
def masks_showcase():
    """Display all available mask shapes"""
    # Group shapes by category
    shapes_by_category = {}
    for name, info in SHAPE_TEMPLATES.items():
        category = info['category']
        if category not in shapes_by_category:
            shapes_by_category[category] = []
        shapes_by_category[category].append({
            'name': name,
            'file': info['file']
        })
    
    return render_template('wordcloud/masks_showcase.html',
                         shapes_by_category=shapes_by_category,
                         total_shapes=len(SHAPE_TEMPLATES))

@wordcloud_bp.route('/features')
def features():
    """Display all wordcloud features and capabilities"""
    return render_template('wordcloud/features.html',
                         feature_sets=FEATURE_SETS,
                         color_schemes=COLOR_SCHEMES,
                         shape_templates=SHAPE_TEMPLATES)

# Cleanup old temp files periodically
def cleanup_temp_files():
    """Remove temporary files older than 2 hours"""
    cutoff_time = time.time() - 7200  # 2 hours
    
    for filename in os.listdir(TEMP_FOLDER):
        filepath = os.path.join(TEMP_FOLDER, filename)
        if os.path.getmtime(filepath) < cutoff_time:
            try:
                os.remove(filepath)
            except:
                pass