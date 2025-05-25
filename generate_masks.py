#!/usr/bin/env python3
"""
Generate all mask images for WordCloud shapes
Creates black shapes on white backgrounds for use as masks
"""

import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import math

MASK_DIR = '/var/temp188.com/static/masks'
os.makedirs(MASK_DIR, exist_ok=True)

def create_basic_shapes():
    """Create basic geometric shapes"""
    
    # Circle
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse([100, 100, 700, 700], fill=0)
    img.save(os.path.join(MASK_DIR, 'circle_mask.png'))
    
    # Square
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 700, 700], fill=0)
    img.save(os.path.join(MASK_DIR, 'square_mask.png'))
    
    # Triangle
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    points = [(400, 100), (100, 700), (700, 700)]
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'triangle_mask.png'))
    
    # Diamond
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    points = [(400, 100), (700, 400), (400, 700), (100, 400)]
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'diamond_mask.png'))
    
    # Hexagon
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    center_x, center_y = 400, 400
    size = 300
    points = []
    for i in range(6):
        angle = i * math.pi / 3
        x = center_x + size * math.cos(angle)
        y = center_y + size * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'hexagon_mask.png'))
    
    # Pentagon
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    center_x, center_y = 400, 400
    size = 300
    points = []
    for i in range(5):
        angle = i * 2 * math.pi / 5 - math.pi / 2
        x = center_x + size * math.cos(angle)
        y = center_y + size * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'pentagon_mask.png'))
    
    # Octagon
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    center_x, center_y = 400, 400
    size = 300
    points = []
    for i in range(8):
        angle = i * math.pi / 4
        x = center_x + size * math.cos(angle)
        y = center_y + size * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'octagon_mask.png'))
    
    # Oval
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 100, 750, 500], fill=0)
    img.save(os.path.join(MASK_DIR, 'oval_mask.png'))

def create_nature_shapes():
    """Create nature-themed shapes"""
    
    # Heart
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Heart shape using bezier curves approximation
    heart_points = []
    for t in np.linspace(0, 2*np.pi, 100):
        x = 16 * (np.sin(t)**3)
        y = -(13 * np.cos(t) - 5 * np.cos(2*t) - 2 * np.cos(3*t) - np.cos(4*t))
        heart_points.append((400 + x * 20, 400 + y * 20))
    draw.polygon(heart_points, fill=0)
    img.save(os.path.join(MASK_DIR, 'heart_mask.png'))
    
    # Star
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    center_x, center_y = 400, 400
    outer_radius = 300
    inner_radius = 120
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        if i % 2 == 0:
            x = center_x + outer_radius * math.cos(angle)
            y = center_y + outer_radius * math.sin(angle)
        else:
            x = center_x + inner_radius * math.cos(angle)
            y = center_y + inner_radius * math.sin(angle)
        points.append((x, y))
    draw.polygon(points, fill=0)
    img.save(os.path.join(MASK_DIR, 'star_mask.png'))
    
    # Cloud
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Create cloud using overlapping circles
    circles = [
        (200, 350, 150), (350, 300, 180), (500, 320, 160),
        (650, 350, 140), (300, 400, 120), (500, 400, 130)
    ]
    for x, y, r in circles:
        draw.ellipse([x-r, y-r, x+r, y+r], fill=0)
    img.save(os.path.join(MASK_DIR, 'cloud_mask.png'))
    
    # Simple tree
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Tree trunk
    draw.rectangle([350, 500, 450, 700], fill=0)
    # Tree crown (triangle)
    draw.polygon([(400, 150), (200, 500), (600, 500)], fill=0)
    img.save(os.path.join(MASK_DIR, 'tree_mask.png'))
    
    # Flower
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Center
    draw.ellipse([350, 350, 450, 450], fill=0)
    # Petals
    for i in range(8):
        angle = i * math.pi / 4
        x = 400 + 150 * math.cos(angle)
        y = 400 + 150 * math.sin(angle)
        draw.ellipse([x-80, y-80, x+80, y+80], fill=0)
    img.save(os.path.join(MASK_DIR, 'flower_mask.png'))
    
    # Moon (crescent)
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Full circle
    draw.ellipse([150, 150, 650, 650], fill=0)
    # Cut out part to make crescent
    draw.ellipse([300, 100, 700, 600], fill=255)
    img.save(os.path.join(MASK_DIR, 'moon_mask.png'))
    
    # Sun
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Center circle
    draw.ellipse([250, 250, 550, 550], fill=0)
    # Rays
    for i in range(12):
        angle = i * math.pi / 6
        x1 = 400 + 150 * math.cos(angle)
        y1 = 400 + 150 * math.sin(angle)
        x2 = 400 + 350 * math.cos(angle)
        y2 = 400 + 350 * math.sin(angle)
        draw.line([(x1, y1), (x2, y2)], fill=0, width=40)
    img.save(os.path.join(MASK_DIR, 'sun_mask.png'))
    
    # Butterfly (simplified)
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Body
    draw.ellipse([380, 200, 420, 400], fill=0)
    # Wings
    draw.ellipse([200, 150, 380, 350], fill=0)
    draw.ellipse([420, 150, 600, 350], fill=0)
    draw.ellipse([250, 280, 380, 450], fill=0)
    draw.ellipse([420, 280, 550, 450], fill=0)
    img.save(os.path.join(MASK_DIR, 'butterfly_mask.png'))

def create_communication_shapes():
    """Create communication-themed shapes"""
    
    # Speech bubble
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Main bubble
    draw.rounded_rectangle([100, 100, 700, 400], radius=50, fill=0)
    # Tail
    draw.polygon([(200, 400), (150, 500), (300, 400)], fill=0)
    img.save(os.path.join(MASK_DIR, 'speech_bubble_mask.png'))
    
    # Thought bubble
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Main bubble
    draw.ellipse([150, 100, 650, 400], fill=0)
    # Small bubbles for tail
    draw.ellipse([200, 380, 280, 460], fill=0)
    draw.ellipse([150, 450, 210, 510], fill=0)
    draw.ellipse([100, 500, 140, 540], fill=0)
    img.save(os.path.join(MASK_DIR, 'thought_bubble_mask.png'))
    
    # Chat box
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([100, 100, 700, 500], radius=30, fill=0)
    img.save(os.path.join(MASK_DIR, 'chat_box_mask.png'))
    
    # Comment icon
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([100, 200, 700, 600], radius=40, fill=0)
    draw.polygon([(550, 600), (650, 700), (600, 600)], fill=0)
    img.save(os.path.join(MASK_DIR, 'comment_mask.png'))

def create_symbol_shapes():
    """Create symbol shapes"""
    
    # Thumbs up
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Thumb
    draw.rounded_rectangle([300, 200, 400, 450], radius=50, fill=0)
    # Fist
    draw.rounded_rectangle([200, 400, 600, 600], radius=30, fill=0)
    img.save(os.path.join(MASK_DIR, 'thumbs_up_mask.png'))
    
    # Peace sign
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Circle
    draw.ellipse([100, 100, 700, 700], fill=0)
    # Peace symbol lines (white to cut out)
    draw.line([(400, 100), (400, 700)], fill=255, width=60)
    draw.line([(400, 400), (200, 600)], fill=255, width=60)
    draw.line([(400, 400), (600, 600)], fill=255, width=60)
    img.save(os.path.join(MASK_DIR, 'peace_mask.png'))
    
    # Infinity
    img = Image.new('L', (800, 400), 255)
    draw = ImageDraw.Draw(img)
    # Two circles forming infinity
    draw.ellipse([100, 50, 400, 350], fill=0, width=80)
    draw.ellipse([400, 50, 700, 350], fill=0, width=80)
    # Fill the loops
    draw.ellipse([150, 100, 350, 300], fill=0)
    draw.ellipse([450, 100, 650, 300], fill=0)
    img.save(os.path.join(MASK_DIR, 'infinity_mask.png'))
    
    # Yin Yang
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Main circle
    draw.ellipse([100, 100, 700, 700], fill=0)
    # S-curve (white half)
    draw.pieslice([100, 100, 700, 700], 90, 270, fill=255)
    draw.ellipse([250, 100, 550, 400], fill=255)
    draw.ellipse([250, 400, 550, 700], fill=0)
    # Small circles
    draw.ellipse([350, 200, 450, 300], fill=0)
    draw.ellipse([350, 500, 450, 600], fill=255)
    img.save(os.path.join(MASK_DIR, 'yin_yang_mask.png'))

def create_animal_shapes():
    """Create simple animal silhouettes"""
    
    # Cat face
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Head
    draw.ellipse([200, 300, 600, 700], fill=0)
    # Ears
    draw.polygon([(200, 400), (150, 200), (300, 350)], fill=0)
    draw.polygon([(500, 350), (650, 200), (600, 400)], fill=0)
    img.save(os.path.join(MASK_DIR, 'cat_mask.png'))
    
    # Dog face
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Head
    draw.ellipse([200, 250, 600, 650], fill=0)
    # Ears (floppy)
    draw.ellipse([100, 300, 250, 500], fill=0)
    draw.ellipse([550, 300, 700, 500], fill=0)
    # Snout
    draw.ellipse([300, 450, 500, 600], fill=0)
    img.save(os.path.join(MASK_DIR, 'dog_mask.png'))
    
    # Bird
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Body
    draw.ellipse([300, 250, 550, 450], fill=0)
    # Head
    draw.ellipse([450, 200, 600, 350], fill=0)
    # Wing
    draw.ellipse([200, 200, 400, 400], fill=0)
    # Tail
    draw.polygon([(300, 350), (100, 400), (200, 300)], fill=0)
    img.save(os.path.join(MASK_DIR, 'bird_mask.png'))
    
    # Fish
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Body
    draw.ellipse([200, 200, 600, 400], fill=0)
    # Tail
    draw.polygon([(200, 300), (50, 200), (50, 400)], fill=0)
    img.save(os.path.join(MASK_DIR, 'fish_mask.png'))

def create_tech_shapes():
    """Create technology-themed shapes"""
    
    # Monitor
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Screen
    draw.rounded_rectangle([100, 150, 700, 550], radius=20, fill=0)
    # Stand
    draw.rectangle([350, 550, 450, 650], fill=0)
    # Base
    draw.ellipse([250, 620, 550, 700], fill=0)
    img.save(os.path.join(MASK_DIR, 'monitor_mask.png'))
    
    # Phone
    img = Image.new('L', (600, 800), 255)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([100, 50, 500, 750], radius=40, fill=0)
    img.save(os.path.join(MASK_DIR, 'phone_mask.png'))
    
    # Gamepad
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Main body
    draw.rounded_rectangle([150, 200, 650, 450], radius=100, fill=0)
    # Grips
    draw.ellipse([50, 250, 200, 400], fill=0)
    draw.ellipse([600, 250, 750, 400], fill=0)
    img.save(os.path.join(MASK_DIR, 'gamepad_mask.png'))
    
    # Keyboard
    img = Image.new('L', (800, 400), 255)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([50, 100, 750, 300], radius=20, fill=0)
    img.save(os.path.join(MASK_DIR, 'keyboard_mask.png'))

def create_social_media_shapes():
    """Create social media themed shapes (simplified logos)"""
    
    # Twitter bird (simplified)
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Body
    draw.ellipse([200, 300, 600, 600], fill=0)
    # Head
    draw.ellipse([350, 200, 650, 450], fill=0)
    # Beak
    draw.polygon([(650, 325), (750, 350), (650, 375)], fill=0)
    img.save(os.path.join(MASK_DIR, 'twitter_mask.png'))
    
    # Facebook F
    img = Image.new('L', (600, 800), 255)
    draw = ImageDraw.Draw(img)
    # Vertical bar
    draw.rectangle([200, 100, 300, 700], fill=0)
    # Top horizontal
    draw.rectangle([200, 200, 500, 300], fill=0)
    # Middle horizontal
    draw.rectangle([200, 400, 450, 500], fill=0)
    img.save(os.path.join(MASK_DIR, 'facebook_mask.png'))
    
    # Instagram camera
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # Outer square with rounded corners
    draw.rounded_rectangle([100, 100, 700, 700], radius=150, fill=0)
    # Cut out center
    draw.rounded_rectangle([150, 150, 650, 650], radius=100, fill=255)
    # Re-fill with border
    draw.rounded_rectangle([200, 200, 600, 600], radius=50, fill=0)
    # Camera lens
    draw.ellipse([300, 300, 500, 500], fill=255)
    draw.ellipse([320, 320, 480, 480], fill=0)
    # Flash
    draw.ellipse([550, 200, 600, 250], fill=0)
    img.save(os.path.join(MASK_DIR, 'instagram_mask.png'))
    
    # YouTube play button
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Rectangle background
    draw.rounded_rectangle([100, 150, 700, 450], radius=50, fill=0)
    # Triangle play button (cut out)
    draw.polygon([(350, 250), (350, 350), (450, 300)], fill=255)
    img.save(os.path.join(MASK_DIR, 'youtube_mask.png'))
    
    # TikTok note
    img = Image.new('L', (600, 800), 255)
    draw = ImageDraw.Draw(img)
    # Musical note shape
    draw.ellipse([200, 500, 400, 700], fill=0)
    draw.rectangle([380, 200, 420, 520], fill=0)
    draw.ellipse([400, 180, 500, 280], fill=0)
    img.save(os.path.join(MASK_DIR, 'tiktok_mask.png'))
    
    # LinkedIn
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    # "in" text as shape
    draw.rectangle([150, 300, 250, 600], fill=0)  # i
    draw.ellipse([150, 200, 250, 300], fill=0)  # i dot
    draw.rectangle([350, 350, 450, 600], fill=0)  # n stem
    draw.ellipse([350, 350, 550, 550], fill=0)  # n curve
    draw.rectangle([550, 450, 650, 600], fill=0)  # n right
    img.save(os.path.join(MASK_DIR, 'linkedin_mask.png'))

def create_geography_shapes():
    """Create simplified geography shapes"""
    
    # USA (simplified outline)
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Very simplified USA shape
    usa_points = [
        (100, 300), (200, 250), (400, 200), (600, 250), (700, 300),
        (650, 400), (550, 450), (400, 400), (300, 450), (150, 400)
    ]
    draw.polygon(usa_points, fill=0)
    img.save(os.path.join(MASK_DIR, 'usa_mask.png'))
    
    # World (simplified oval)
    img = Image.new('L', (800, 600), 255)
    draw = ImageDraw.Draw(img)
    # Main continents as blobs
    draw.ellipse([50, 200, 350, 400], fill=0)  # Americas
    draw.ellipse([400, 150, 600, 350], fill=0)  # Europe/Africa
    draw.ellipse([550, 300, 750, 450], fill=0)  # Asia
    img.save(os.path.join(MASK_DIR, 'world_mask.png'))
    
    # Europe (simplified)
    img = Image.new('L', (800, 800), 255)
    draw = ImageDraw.Draw(img)
    europe_points = [
        (400, 100), (500, 150), (600, 200), (650, 300),
        (600, 400), (500, 500), (400, 550), (300, 500),
        (200, 400), (150, 300), (200, 200), (300, 150)
    ]
    draw.polygon(europe_points, fill=0)
    img.save(os.path.join(MASK_DIR, 'europe_mask.png'))
    
    # Africa (simplified)
    img = Image.new('L', (600, 800), 255)
    draw = ImageDraw.Draw(img)
    africa_points = [
        (300, 100), (450, 150), (500, 250), (450, 400),
        (400, 550), (300, 700), (200, 550), (150, 400),
        (100, 250), (150, 150)
    ]
    draw.polygon(africa_points, fill=0)
    img.save(os.path.join(MASK_DIR, 'africa_mask.png'))

def main():
    """Generate all masks"""
    print("Generating basic shapes...")
    create_basic_shapes()
    
    print("Generating nature shapes...")
    create_nature_shapes()
    
    print("Generating communication shapes...")
    create_communication_shapes()
    
    print("Generating symbol shapes...")
    create_symbol_shapes()
    
    print("Generating animal shapes...")
    create_animal_shapes()
    
    print("Generating tech shapes...")
    create_tech_shapes()
    
    print("Generating social media shapes...")
    create_social_media_shapes()
    
    print("Generating geography shapes...")
    create_geography_shapes()
    
    print(f"All masks generated in {MASK_DIR}")

if __name__ == '__main__':
    main()