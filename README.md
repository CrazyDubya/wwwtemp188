# temp188.com - Multi-Project Platform with WordCloud Studio

A unified web platform featuring multiple creative tools, starting with a comprehensive WordCloud Studio.

## Features

### 🎨 WordCloud Studio

A full-featured word cloud generator leveraging the complete power of Andreas Mueller's [word_cloud library](https://github.com/amueller/word_cloud).

#### Three Generation Modes:

1. **Quick Generator**
   - Instant word cloud creation with word/weight pairs
   - 10 pre-defined color schemes
   - Generates 3 variations automatically
   - No login required

2. **Custom Shapes**
   - 40+ pre-designed shape masks (hearts, stars, animals, social media icons, etc.)
   - Upload custom black & white masks
   - Full color control with 60+ color schemes
   - Image color extraction support

3. **Advanced Studio**
   - Complete parameter control (24 parameters)
   - Text file upload support
   - Custom font upload
   - Word frequency analytics
   - High-resolution export (up to 3200x2400px)

#### Available Color Schemes (60+):
- Sequential: Viridis, Plasma, Blues, Greens, etc.
- Diverging: RdYlBu, Spectral, Coolwarm, etc.
- Qualitative: Set3, Pastel, Tab10, etc.
- Seasonal: Spring, Summer, Autumn, Winter
- Special: Ocean, Galaxy, Neon, Rainbow, etc.

#### Available Shapes (40+):
- Basic: Circle, Square, Triangle, Diamond, etc.
- Nature: Heart, Star, Cloud, Tree, Butterfly, etc.
- Communication: Speech/Thought bubbles
- Social Media: Twitter, Facebook, Instagram, etc.
- Animals: Cat, Dog, Bird, Fish
- Tech: Monitor, Phone, Gamepad
- Geography: USA, World, Europe, Africa

### 🔐 Unified Authentication
- Single sign-on across all tools
- User dashboard
- Save and manage creations
- OAuth ready (GitHub, Google)

### 🚀 Technical Stack
- **Backend**: Flask with Blueprints architecture
- **Database**: SQLAlchemy with SQLite
- **Authentication**: Flask-Login
- **UI**: Tailwind CSS with glass-morphism design
- **Word Cloud Engine**: word_cloud library (MIT License)
- **Deployment**: Nginx + Supervisor

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/temp188.com.git
cd temp188.com
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python migrate_to_unified.py
```

4. Run the application:
```bash
python app_unified.py
```

## API Endpoints

### WordCloud API
- `POST /wordcloud/api/generate` - Generate word cloud programmatically
- `GET /wordcloud/api/stats` - Get usage statistics
- `GET /wordcloud/api/color-schemes` - List all color schemes
- `GET /wordcloud/api/shapes` - List all shape templates

### Example API Usage:
```python
import requests

response = requests.post('https://temp188.com/wordcloud/api/generate', 
    json={
        'text': 'Your text here',
        'width': 800,
        'height': 400,
        'colormap': 'viridis',
        'max_words': 100
    }
)
```

## Project Structure
```
temp188.com/
├── app_unified.py          # Main application
├── models.py              # Database models
├── blueprints/            # Feature modules
│   ├── auth.py           # Authentication
│   ├── wordcloud.py      # WordCloud features
│   └── dashboard.py      # User dashboard
├── templates/             # HTML templates
├── static/               # CSS, JS, images
├── generate_masks.py     # Shape mask generator
└── requirements.txt      # Python dependencies
```

## Credits

- **WordCloud Library**: [Andreas Mueller](https://github.com/amueller/word_cloud) (MIT License)
- **UI Framework**: Tailwind CSS
- **Icons**: Font Awesome

## License

MIT License - See LICENSE file for details

## Future Roadmap

- [ ] Text Analytics Tools
- [ ] Data Visualization Suite
- [ ] Creative Writing Tools
- [ ] API Rate Limiting
- [ ] Premium Features
- [ ] Mobile App

---

Built with ❤️ by temp188.com