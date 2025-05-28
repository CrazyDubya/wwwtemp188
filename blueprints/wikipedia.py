"""
Wikipedia AI Analyzer Blueprint
Analyzes Wikipedia articles for bias, sourcing quality, and factual accuracy
"""

from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, session
from flask_login import login_required, current_user
from functools import wraps
import requests
import json
import os
import hashlib
from datetime import datetime, timedelta
from models import db, AnalysisRequest, AnalysisHistory, AnalysisCache, UserContribution, UserBadge, PageView, SearchQuery, UserInteraction, AnalyticsSession

wikipedia_bp = Blueprint('wikipedia', __name__)

def check_rate_limit(ip_address, analysis_type='quick'):
    """
    Check if request is within rate limits
    Returns: (allowed: bool, remaining: int, reset_time: datetime)
    """
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    
    # Get user info if logged in
    user_id = None
    try:
        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
            user_id = current_user.id
    except:
        user_id = None
    
    if user_id:
        # Logged in users get tier-based limits
        try:
            limit = current_user.get_rate_limit()
        except:
            limit = 5  # Fallback limit
        count = AnalysisRequest.query.filter(
            AnalysisRequest.user_id == user_id,
            AnalysisRequest.analysis_type == analysis_type,
            AnalysisRequest.timestamp >= hour_ago
        ).count()
    else:
        # Anonymous users get IP-based limits
        limit = 5  # Anonymous limit
        count = AnalysisRequest.query.filter(
            AnalysisRequest.ip_address == ip_address,
            AnalysisRequest.user_id.is_(None),
            AnalysisRequest.analysis_type == analysis_type,
            AnalysisRequest.timestamp >= hour_ago
        ).count()
    
    allowed = count < limit
    remaining = max(0, limit - count)
    reset_time = now + timedelta(hours=1)
    
    return allowed, remaining, reset_time

def log_analysis_request(ip_address, article_title, analysis_type='quick'):
    """Log analysis request for rate limiting"""
    user_agent = request.headers.get('User-Agent', '')
    user_id = current_user.id if current_user.is_authenticated else None
    
    analysis_request = AnalysisRequest(
        user_id=user_id,
        ip_address=ip_address,
        article_title=article_title,
        analysis_type=analysis_type,
        user_agent=user_agent
    )
    db.session.add(analysis_request)
    db.session.commit()

def log_contribution(contribution_type, points=1, extra_data=None):
    """Log user contribution for gamification"""
    if current_user.is_authenticated:
        contribution = UserContribution(
            user_id=current_user.id,
            contribution_type=contribution_type,
            points=points,
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        db.session.add(contribution)
        db.session.commit()
        
        # Check for new badges after contribution
        check_and_award_badges(current_user.id)

def check_and_award_badges(user_id):
    """Check if user earned new badges and award them"""
    from models import User
    user = User.query.get(user_id)
    if not user:
        return
    
    # Define badges and requirements
    badges = {
        'first_analysis': {
            'requirement': lambda u: u.analysis_count >= 1,
            'points': 5
        },
        'analyzer_novice': {
            'requirement': lambda u: u.analysis_count >= 5,
            'points': 10
        },
        'analyzer_expert': {
            'requirement': lambda u: u.analysis_count >= 25,
            'points': 25
        },
        'wikipedia_scholar': {
            'requirement': lambda u: u.analysis_count >= 100,
            'points': 50
        }
    }
    
    # Check each badge
    for badge_id, badge_config in badges.items():
        if not user.has_badge(badge_id) and badge_config['requirement'](user):
            # Award badge
            badge = UserBadge(user_id=user_id, badge_id=badge_id)
            db.session.add(badge)
            
            # Award points
            contribution = UserContribution(
                user_id=user_id,
                contribution_type='badge_earned',
                points=badge_config['points'],
                extra_data=json.dumps({'badge_id': badge_id})
            )
            db.session.add(contribution)
    
    db.session.commit()

@wikipedia_bp.route('/')
def index():
    """Wikipedia AI Analyzer main page"""
    # Track page view
    track_page_view(request.url, 'Wikipedia AI Analyzer - Home')
    return render_template('wikipedia/index.html')

@wikipedia_bp.route('/search')
def search():
    """Search Wikipedia articles"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    
    # Track search query
    track_search_query(query, 'wikipedia_search')
    
    try:
        # Use Wikipedia API to search for articles
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&generator=prefixsearch&gpssearch={query}&gpslimit=10&prop=pageimages|pageterms|info&piprop=thumbnail&pilimit=10&wbptterms=description&inprop=url&redirects=&origin=*"
        
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        pages = data.get('query', {}).get('pages', {})
        
        for page_id, page in pages.items():
            if page_id != '-1':  # Skip missing pages
                result = {
                    'title': page.get('title', ''),
                    'description': page.get('terms', {}).get('description', [''])[0],
                    'url': page.get('fullurl', ''),
                    'thumbnail': page.get('thumbnail', {}).get('source', '') if page.get('thumbnail') else ''
                }
                results.append(result)
        
        return jsonify({
            'results': results,
            'total': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Wikipedia search error: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@wikipedia_bp.route('/page')
def get_page():
    """Get Wikipedia page content with citations"""
    title = request.args.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Missing title parameter'}), 400
    
    try:
        # Get full page content with parse data
        parse_url = f"https://en.wikipedia.org/w/api.php?action=parse&format=json&page={title}&prop=wikitext|categories|externallinks|sections&redirects=&origin=*"
        
        # Get page info and revision history  
        info_url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&titles={title}&prop=info|revisions&inprop=url&rvprop=timestamp|user|size|comment&rvlimit=10&redirects=&origin=*"
        
        # Make both API calls
        parse_response = requests.get(parse_url, timeout=15)
        info_response = requests.get(info_url, timeout=15)
        
        parse_response.raise_for_status()
        info_response.raise_for_status()
        
        parse_data = parse_response.json()
        info_data = info_response.json()
        
        if 'error' in parse_data:
            return jsonify({'error': f"Page not found: {title}"}), 404
        
        # Extract page info
        pages = info_data.get('query', {}).get('pages', {})
        page_info = next(iter(pages.values())) if pages else {}
        
        # Extract citations from wikitext
        wikitext = parse_data.get('parse', {}).get('wikitext', {}).get('*', '')
        citations = extract_citations(wikitext)
        
        # Clean and structure the content
        cleaned_content = clean_wikitext(wikitext, citations)
        
        result = {
            'title': parse_data.get('parse', {}).get('title', title),
            'content': cleaned_content,
            'citations': citations,
            'categories': parse_data.get('parse', {}).get('categories', []),
            'external_links': parse_data.get('parse', {}).get('externallinks', []),
            'sections': parse_data.get('parse', {}).get('sections', []),
            'page_info': {
                'created': page_info.get('touched', ''),
                'last_modified': page_info.get('touched', ''),
                'length': page_info.get('length', 0),
                'watchers': page_info.get('watchers', 0)
            },
            'content_urls': {
                'desktop': {
                    'page': page_info.get('fullurl', f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Wikipedia page error: {str(e)}")
        return jsonify({'error': 'Failed to fetch page'}), 500

@wikipedia_bp.route('/quick-analyze', methods=['POST'])
def quick_analyze():
    """Quick analysis with rate-limited built-in AI"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text content'}), 400
    
    text = data.get('text', '')
    title = data.get('title', 'Article')
    
    # Track analysis request - temporarily disabled for debugging
    # track_search_query(title, 'quick_analysis')
    # track_user_interaction('analysis_request', extra_data={'title': title, 'text_length': len(text)})
    
    if len(text) > 50000:  # Limit text size for free analysis
        text = text[:50000]
    
    # Get client IP for rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    # Check rate limit
    allowed, remaining, reset_time = check_rate_limit(client_ip, 'quick')
    if not allowed:
        return jsonify({
            'error': f'Rate limit exceeded. You can make {remaining} more requests. Rate limit resets at {reset_time.strftime("%H:%M:%S")} UTC.',
            'rate_limit': {
                'allowed': False,
                'remaining': remaining,
                'reset_time': reset_time.isoformat(),
                'suggestion': 'Sign up for a free account to get higher rate limits!'
            }
        }), 429
    
    # Log the request
    log_analysis_request(client_ip, title, 'quick')
    
    # Update session analytics for analysis - temporarily disabled for debugging
    # try:
    #     client_ip, user_agent, session_id = get_client_info()
    #     user_id = None
    #     try:
    #         if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
    #             user_id = current_user.id
    #     except:
    #         user_id = None
    #     update_session_analytics(session_id, user_id, client_ip, user_agent, 'analysis')
    # except:
    #     pass  # Don't let analytics break the analysis
    
    try:
        # First check database cache for high-quality admin-approved analyses
        db_cached_analysis = check_database_cache(text, title)
        if db_cached_analysis:
            return jsonify(db_cached_analysis)
        
        # Then check temporary cache for recent analyses
        cache_key = f"quick_analysis:{hashlib.md5((title + text[:1000]).encode()).hexdigest()}"
        cached_analysis = get_cached_analysis(cache_key)
        if cached_analysis:
            return jsonify({
                'analysis': cached_analysis['analysis'],
                'model': cached_analysis['model'],
                'provider': cached_analysis['provider'] + ' (Cached)',
                'timestamp': cached_analysis['timestamp'],
                'cached': True
            })
        
        # If not cached, get fresh analysis
        analysis_result = quick_analyze_with_openrouter_data(text, title)
        
        # Cache the result for future use and return as JSON
        if analysis_result and 'analysis' in analysis_result:
            cache_analysis(cache_key, analysis_result)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        current_app.logger.error(f"Quick analysis error: {str(e)}")
        return jsonify({'error': 'Analysis service temporarily unavailable'}), 500

@wikipedia_bp.route('/analyze', methods=['POST'])
def analyze():
    """Analyze Wikipedia content with user's AI configuration"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text content'}), 400
    
    text = data.get('text', '')
    title = data.get('title', 'Article')
    ai_endpoint = data.get('endpoint', '')
    model = data.get('model', 'gpt-3.5-turbo')
    provider = data.get('provider', 'openai')
    api_key = data.get('api_key', '')
    
    if not ai_endpoint or not api_key:
        return jsonify({'error': 'Missing AI endpoint or API key'}), 400
    
    try:
        # First check database cache for high-quality admin-approved analyses
        db_cached_analysis = check_database_cache(text, title)
        if db_cached_analysis:
            return jsonify(db_cached_analysis)
        
        # If not cached, analyze with user's AI configuration
        analysis_result = analyze_with_ai(text, ai_endpoint, api_key, model, provider)
        
        # Log the analysis to history for potential admin review
        if isinstance(analysis_result, tuple):
            result_data = analysis_result[0].get_json()
        else:
            result_data = analysis_result.get_json()
            
        if result_data and 'analysis' in result_data:
            log_analysis_history(title, {
                'analysis': result_data['analysis'],
                'model': model,
                'provider': provider,
                'cached': False
            })
        
        return analysis_result
        
    except Exception as e:
        current_app.logger.error(f"AI analysis error: {str(e)}")
        return jsonify({'error': 'Analysis failed'}), 500

def extract_citations(wikitext):
    """Extract citations from Wikipedia wikitext"""
    import re
    
    citations = []
    citation_counter = 0
    
    # Find all <ref> tags with content
    ref_pattern = r'<ref[^>]*>(.*?)</ref>'
    matches = re.finditer(ref_pattern, wikitext, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        citation_counter += 1
        content = match.group(1).strip()
        
        # Clean citation content
        cleaned_content = clean_citation_template(content)
        
        citations.append({
            'id': f'ref-{citation_counter}',
            'number': citation_counter,
            'content': cleaned_content,
            'position': match.start()
        })
    
    return citations

def clean_citation_template(template):
    """Extract useful information from citation templates"""
    import re
    
    title_match = re.search(r'title\s*=\s*([^|]+)', template, re.IGNORECASE)
    author_match = re.search(r'author\s*=\s*([^|]+)', template, re.IGNORECASE)
    url_match = re.search(r'url\s*=\s*([^|]+)', template, re.IGNORECASE)
    date_match = re.search(r'date\s*=\s*([^|]+)', template, re.IGNORECASE)
    
    citation = ''
    if author_match:
        citation += author_match.group(1).strip() + '. '
    if title_match:
        citation += '"' + title_match.group(1).strip() + '". '
    if date_match:
        citation += date_match.group(1).strip() + '. '
    if url_match:
        citation += f'<a href="{url_match.group(1).strip()}" target="_blank" rel="noopener">Source</a>'
    
    return citation or template[:100] + '...'

def clean_wikitext(wikitext, citations=None):
    """Clean and format Wikipedia wikitext for display with comprehensive parsing"""
    import re
    
    if citations is None:
        citations = []
    
    cleaned = wikitext
    citation_map = {c['position']: c for c in citations}
    
    # Step 1: Remove Wikipedia metadata and navigation templates
    cleaned = re.sub(r'\{\{Short description\|[^}]+\}\}', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\{\{Redirect\|[^}]+\}\}', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\{\{Use dmy dates\|[^}]+\}\}', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\{\{Pp\|[^}]+\}\}', '', cleaned, flags=re.IGNORECASE)
    
    # Step 2: Handle navigation and infobox templates more gracefully
    cleaned = re.sub(r'\{\{[Aa]rtificial intelligence\}\}', 
                    '<div class="wikipedia-navbox">📚 See also: <a href="https://en.wikipedia.org/wiki/Template:Artificial_intelligence" target="_blank">Artificial Intelligence Topics</a></div>', 
                    cleaned, flags=re.IGNORECASE)
    
    # Step 3: Process images before other replacements
    def replace_images(match):
        content = match.group(0)
        # Extract filename
        file_match = re.search(r'File:([^|\]]+)', content)
        if file_match:
            filename = file_match.group(1)
            # Extract description (last part after |)
            parts = content.split('|')
            description = parts[-1].replace(']]', '') if len(parts) > 1 else filename
            return f'''
            <div class="wikipedia-image">
                <img src="https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width=400" 
                     alt="{description}" 
                     style="max-width: 100%; height: auto; border-radius: 5px; margin: 1rem 0;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display: none; padding: 1rem; background: #f8f9fa; border-radius: 5px; text-align: center;">
                    📷 Image: {filename}
                </div>
                <div class="image-caption" style="font-size: 0.9em; color: #666; margin-top: 0.5rem; font-style: italic;">
                    {description}
                </div>
            </div>
            '''
        return ''
    
    cleaned = re.sub(r'\[\[File:[^\]]+\]\]', replace_images, cleaned, flags=re.IGNORECASE)
    
    # Step 4: Replace ref tags with numbered superscript citations
    ref_pattern = r'<ref[^>]*>.*?</ref>'
    matches = list(re.finditer(ref_pattern, cleaned, re.DOTALL | re.IGNORECASE))
    
    # Replace in reverse order to maintain positions
    for match in reversed(matches):
        citation = citation_map.get(match.start())
        if citation:
            replacement = f'<sup class="citation" data-citation-id="{citation["id"]}" data-citation-number="{citation["number"]}" title="{citation["content"][:200]}...">[{citation["number"]}]</sup>'
            cleaned = cleaned[:match.start()] + replacement + cleaned[match.end():]
    
    # Step 5: Handle named references
    cleaned = re.sub(r'<ref\s+name\s*=\s*["\']([^"\']+)["\']\s*/>', 
                    lambda m: f'<sup class="citation">[ref: {m.group(1)}]</sup>', 
                    cleaned, flags=re.IGNORECASE)
    
    # Step 6: Clean citation templates (Sfnp, Harvtxt, etc.)
    def clean_citation_template(match):
        content = match.group(0)
        # Extract author and year if possible
        if 'Sfnp' in content or 'Harvtxt' in content:
            # Try to extract meaningful info
            parts = content.split('|')
            if len(parts) >= 3:
                author = parts[1] if parts[1] else 'Author'
                year = parts[2] if parts[2] else 'Year'
                return f'<span class="inline-citation">({author}, {year})</span>'
        return '<span class="inline-citation">(Citation)</span>'
    
    cleaned = re.sub(r'\{\{(?:Sfnp|Harvtxt)[^}]+\}\}', clean_citation_template, cleaned, flags=re.IGNORECASE)
    
    # Step 7: Remove remaining templates but preserve some useful ones
    cleaned = re.sub(r'\{\{[Cc]ite[^}]+\}\}', '<span class="inline-citation">(Source)</span>', cleaned)
    cleaned = re.sub(r'\{\{[^}]*\}\}', '', cleaned)  # Remove remaining templates
    
    # Step 8: Process Wikipedia links
    # Handle links with custom display text: [[target|display]]
    cleaned = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'<a href="https://en.wikipedia.org/wiki/\1" target="_blank" class="wikipedia-link">\2</a>', cleaned)
    # Handle simple links: [[target]]
    cleaned = re.sub(r'\[\[([^\]]+)\]\]', r'<a href="https://en.wikipedia.org/wiki/\1" target="_blank" class="wikipedia-link">\1</a>', cleaned)
    
    # Step 9: Handle external links
    cleaned = re.sub(r'\[([http][^\s]+)\s+([^\]]+)\]', r'<a href="\1" target="_blank" rel="noopener">\2</a>', cleaned)
    cleaned = re.sub(r'\[([http][^\]]+)\]', r'<a href="\1" target="_blank" rel="noopener">External Link</a>', cleaned)
    
    # Step 10: Text formatting
    cleaned = re.sub(r"'''([^']+)'''", r'<strong>\1</strong>', cleaned)  # Bold
    cleaned = re.sub(r"''([^']+)''", r'<em>\1</em>', cleaned)  # Italic
    
    # Step 11: Process sections for collapsible display
    lines = cleaned.split('\n')
    processed_lines = []
    section_counter = 0
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for headers (2, 3, and 4 level)
        h2_match = re.match(r'^==\s*([^=]+)\s*==$', line)
        h3_match = re.match(r'^===\s*([^=]+)\s*===$', line)
        h4_match = re.match(r'^====\s*([^=]+)\s*====$', line)
        
        if h2_match or h3_match or h4_match:
            # Close previous section
            if current_section:
                processed_lines.append('</div></div>')
            
            section_counter += 1
            title = (h2_match or h3_match or h4_match).group(1).strip()
            section_id = f'section-{section_counter}'
            
            # Determine header styling based on level
            if h2_match:
                header_level = 'h3'
                header_class = 'text-xl font-bold bg-teal-50 border-l-4 border-teal-500'
            elif h3_match:
                header_level = 'h4'
                header_class = 'text-lg font-semibold bg-blue-50 border-l-4 border-blue-400'
            else:  # h4_match
                header_level = 'h5'
                header_class = 'text-base font-medium bg-gray-50 border-l-4 border-gray-400'
            
            processed_lines.append('<div class="collapsible-section">')
            processed_lines.append(f'<{header_level} class="section-header cursor-pointer py-3 px-4 {header_class} rounded mb-2 hover:bg-opacity-75 transition-colors" onclick="toggleSection(\'{section_id}\')">')
            processed_lines.append(f'<span class="section-toggle" id="toggle-{section_id}">▼</span> {title}')
            processed_lines.append(f'</{header_level}>')
            processed_lines.append(f'<div class="section-content" id="{section_id}">')
            current_section = section_id
        else:
            # Add content to current section
            if line:
                processed_lines.append(f'<p class="mb-4 leading-relaxed">{line}</p>')
    
    # Close final section
    if current_section:
        processed_lines.append('</div></div>')
    
    cleaned = '\n'.join(processed_lines)
    
    # Step 12: Clean up remaining markup
    cleaned = re.sub(r'\[\[Category:[^\]]+\]\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    cleaned = re.sub(r'<!--[^>]*-->', '', cleaned)  # Remove comments
    
    return cleaned.strip()

def analyze_with_ai(text, endpoint, api_key, model='gpt-3.5-turbo', provider='openai'):
    """Analyze text with AI service"""
    
    prompt = f"""Please analyze this Wikipedia text for bias and neutrality. Note that [citation] markers indicate where sources are referenced in the original article.

Key areas to evaluate:
1. **Bias Detection**: Look for loaded language, POV statements, or unbalanced coverage
2. **Source Quality**: Assess if claims are properly cited and if sources appear reliable  
3. **Neutrality**: Check if multiple perspectives are presented fairly
4. **Factual Accuracy**: Note any suspicious claims or potential inaccuracies

Text to analyze:
{text[:8000]}  

Respond in readable text format."""

    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        if provider.lower() == 'openai':
            headers['Authorization'] = f'Bearer {api_key}'
            payload = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 1000,
                'temperature': 0.3
            }
        else:
            # Generic format for other providers
            headers['Authorization'] = f'Bearer {api_key}'
            payload = {
                'model': model,
                'prompt': prompt,
                'max_tokens': 1000,
                'temperature': 0.3
            }
        
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if provider.lower() == 'openai' and 'choices' in result:
            analysis = result['choices'][0]['message']['content']
        elif 'choices' in result:
            analysis = result['choices'][0].get('text', result['choices'][0].get('message', {}).get('content', ''))
        else:
            analysis = str(result)
        
        analysis_data = {
            'analysis': analysis,
            'model': model,
            'provider': provider,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log the analysis for user history (if logged in)  
        log_analysis_history('User Analysis', analysis_data)
        
        return jsonify(analysis_data)
        
    except Exception as e:
        raise Exception(f"AI analysis failed: {str(e)}")

def quick_analyze_with_openrouter_data(text, title):
    """Quick analysis using rate-limited OpenRouter service - returns data only"""
    import os
    import time
    from datetime import datetime
    
    # Rate limiting - simple in-memory store (use Redis in production)
    rate_limit_key = f"quick_analyze_rate_limit"
    # For now, allow 10 requests per hour per instance
    # In production, implement proper rate limiting with Redis/database
    
    prompt = f"""Please analyze this Wikipedia article "{title}" for bias and neutrality. Focus on:

1. **Bias Detection**: Any loaded language, POV statements, or unbalanced coverage?
2. **Source Quality**: Are claims properly cited with reliable sources?
3. **Neutrality**: Are multiple perspectives presented fairly?
4. **Notable Issues**: Any suspicious claims or potential inaccuracies?

Article content (truncated if needed):
{text[:8000]}

Provide a concise analysis in 3-4 paragraphs."""

    try:
        # Use demo OpenRouter key from environment variable
        demo_api_key = os.getenv('OPENROUTER_API_KEY')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {demo_api_key}',
            'HTTP-Referer': 'https://temp188.com',
            'X-Title': 'Wikipedia AI Analyzer'
        }
        
        # Use best free model available on OpenRouter
        # Meta Llama 3.1 8B is reliable and free for most tasks
        payload = {
            'model': 'meta-llama/llama-3.1-8b-instruct:free',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1000,
            'temperature': 0.3,
            'extra': {
                'used_for': 'wikipedia_analysis',
                'source': 'temp188.com'
            }
        }
        
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers, 
            json=payload, 
            timeout=30
        )
        
        if response.status_code == 429:
            return jsonify({
                'error': 'Rate limit reached. Please try again in a few minutes or use the Advanced Analysis with your own API key.',
                'retry_after': 300
            })
        
        response.raise_for_status()
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            analysis = result['choices'][0]['message']['content']
            analysis_data = {
                'analysis': analysis,
                'model': 'Llama 3.1 8B',
                'provider': 'OpenRouter (Rate Limited)',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Log the analysis for user history (if logged in)
            log_analysis_history(title, analysis_data)
            
            return analysis_data
        else:
            return {'error': 'No analysis returned from AI service'}
        
    except requests.exceptions.RequestException as e:
        # Fallback to mock analysis for demo purposes
        return {
            'analysis': f"""**Demo Analysis for "{title}"**

**Bias Assessment**: This appears to be a well-structured Wikipedia article following standard encyclopedic conventions. The language used is generally neutral and factual, though some sections may benefit from additional perspectives.

**Source Quality**: The article contains numerous citations (as indicated by the reference markers), which is positive for verifiability. However, without examining the actual sources, it's difficult to assess their quality and reliability fully.

**Neutrality Check**: The content presents information in an encyclopedia format typical of Wikipedia. Multiple viewpoints appear to be acknowledged where relevant, though some topics might benefit from expanded coverage of alternative perspectives.

**Overall Assessment**: This article demonstrates the collaborative nature of Wikipedia with extensive referencing. For the most current and comprehensive analysis, users should verify sources directly and consider multiple authoritative references.

*Note: This is a demo analysis. For detailed analysis with your preferred AI model, please use the Advanced Analysis option.*""",
            'model': 'Demo Service (Rate Limited)',
            'provider': 'temp188.com Fallback',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {'error': 'Analysis service error. Please try again later.'}

def quick_analyze_with_openrouter(text, title):
    """Quick analysis using rate-limited OpenRouter service - Flask endpoint version"""
    try:
        result = quick_analyze_with_openrouter_data(text, title)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"OpenRouter analysis error: {str(e)}")
        return jsonify({'error': 'Analysis service error. Please try again later.'})

def get_cached_analysis(cache_key):
    """Get cached analysis result"""
    try:
        # For now using simple file-based cache
        # In production, use Redis or database
        import os
        import json
        from datetime import datetime, timedelta
        
        cache_dir = '/tmp/wikipedia_analysis_cache'
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_file):
            # Check if cache is still valid (24 hours)
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_time < timedelta(hours=24):
                with open(cache_file, 'r') as f:
                    return json.load(f)
            else:
                # Remove expired cache
                os.remove(cache_file)
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Cache read error: {str(e)}")
        return None

def cache_analysis(cache_key, result_data):
    """Cache analysis result"""
    try:
        import os
        import json
        
        cache_dir = '/tmp/wikipedia_analysis_cache'
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")
        
        with open(cache_file, 'w') as f:
            json.dump(result_data, f)
            
        current_app.logger.info(f"Cached analysis for key: {cache_key}")
        
    except Exception as e:
        current_app.logger.error(f"Cache write error: {str(e)}")

def log_analysis_history(title, analysis_data):
    """Log analysis history for users (if authenticated)"""
    try:
        # Save to database - safely check for authentication
        user_id = None
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                user_id = current_user.id
        except:
            user_id = None
        
        # Create content hash for cache invalidation
        text_content = analysis_data.get('analysis', '')
        content_hash = hashlib.md5(text_content.encode()).hexdigest()
        
        analysis_history = AnalysisHistory(
            user_id=user_id,
            article_title=title,
            article_hash=content_hash,
            model_used=analysis_data.get('model'),
            provider=analysis_data.get('provider'),
            analysis_text=text_content,
            is_cached=analysis_data.get('cached', False),
            timestamp=datetime.utcnow()
        )
        db.session.add(analysis_history)
        
        # Log contribution points for authenticated users
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                log_contribution('quick_analysis', 1, {'article': title, 'model': analysis_data.get('model')})
                current_app.logger.info(f"Analysis by user {current_user.username}: {title} - Model: {analysis_data.get('model', 'Unknown')}")
            else:
                current_app.logger.info(f"Anonymous analysis: {title} - Model: {analysis_data.get('model', 'Unknown')}")
        except:
            current_app.logger.info(f"Analysis logged: {title} - Model: {analysis_data.get('model', 'Unknown')}")
        
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Analysis logging error: {str(e)}")
        # Don't let logging errors break the analysis
        try:
            db.session.rollback()
        except:
            pass

def check_database_cache(text, title):
    """Check if high-quality analysis exists in database cache"""
    try:
        # Create content hash
        content_hash = hashlib.md5((title + text[:1000]).encode()).hexdigest()
        
        # Look for approved analysis in cache
        cached_analysis = AnalysisCache.query.filter_by(
            article_hash=content_hash,
        ).filter(
            AnalysisCache.quality_score >= 3,  # Only high-quality cached analyses
            AnalysisCache.approved_by.isnot(None),  # Only admin-approved
            AnalysisCache.analysis_text != ''  # Not rejected analyses
        ).first()
        
        if cached_analysis:
            return {
                'analysis': cached_analysis.analysis_text,
                'model': cached_analysis.model_used,
                'provider': cached_analysis.provider + ' (High-Quality Cache)',
                'timestamp': cached_analysis.created_at.isoformat(),
                'cached': True,
                'quality_score': cached_analysis.quality_score,
                'admin_approved': True
            }
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"Database cache lookup error: {str(e)}")
        return None

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('wikipedia.index'))
        return f(*args, **kwargs)
    return decorated_function

@wikipedia_bp.route('/admin/review')
@login_required
@admin_required
def admin_review():
    """Admin dashboard for reviewing analyses"""
    # Track admin page view
    track_page_view(request.url, 'Admin Review Dashboard')
    # Get pending analyses (from analysis_history that aren't in cache yet)
    pending_analyses = db.session.query(AnalysisHistory).outerjoin(
        AnalysisCache, 
        AnalysisHistory.article_hash == AnalysisCache.article_hash
    ).filter(
        AnalysisCache.id.is_(None),  # Not in cache yet
        AnalysisHistory.analysis_text.isnot(None)  # Has analysis content
    ).order_by(AnalysisHistory.timestamp.desc()).limit(20).all()
    
    # Get recent approved analyses
    approved_analyses = AnalysisCache.query.filter(
        AnalysisCache.approved_by.isnot(None)
    ).order_by(AnalysisCache.approved_at.desc()).limit(10).all()
    
    return render_template('wikipedia/admin_review.html', 
                         pending_analyses=pending_analyses,
                         approved_analyses=approved_analyses)

@wikipedia_bp.route('/admin/review/<int:analysis_id>')
@login_required
@admin_required
def review_analysis(analysis_id):
    """Review a specific analysis"""
    analysis = AnalysisHistory.query.get_or_404(analysis_id)
    
    # Check if already cached
    existing_cache = AnalysisCache.query.filter_by(
        article_hash=analysis.article_hash
    ).first()
    
    return render_template('wikipedia/review_detail.html', 
                         analysis=analysis,
                         existing_cache=existing_cache)

@wikipedia_bp.route('/admin/approve/<int:analysis_id>', methods=['POST'])
@login_required
@admin_required
def approve_analysis(analysis_id):
    """Approve an analysis for caching"""
    analysis = AnalysisHistory.query.get_or_404(analysis_id)
    
    try:
        quality_score = int(request.form.get('quality_score', 3))
        admin_notes = request.form.get('admin_notes', '')
        
        # Check if already cached
        existing_cache = AnalysisCache.query.filter_by(
            article_hash=analysis.article_hash
        ).first()
        
        if existing_cache:
            # Update existing cache entry
            existing_cache.quality_score = quality_score
            existing_cache.admin_notes = admin_notes
            existing_cache.approved_by = current_user.id
            existing_cache.approved_at = datetime.utcnow()
            flash('Analysis cache updated successfully!', 'success')
        else:
            # Create new cache entry
            cache_entry = AnalysisCache(
                article_title=analysis.article_title,
                article_hash=analysis.article_hash,
                model_used=analysis.model_used,
                provider=analysis.provider,
                analysis_text=analysis.analysis_text,
                quality_score=quality_score,
                admin_notes=admin_notes,
                approved_by=current_user.id,
                approved_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            db.session.add(cache_entry)
            flash('Analysis approved and cached successfully!', 'success')
        
        db.session.commit()
        
        # Award badge to original user if they exist
        if analysis.user_id:
            from models import User
            original_user = User.query.get(analysis.user_id)
            if original_user:
                award_badge(original_user.id, 'quality_contributor', 
                          f'Analysis of "{analysis.article_title}" approved by admin')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving analysis: {str(e)}")
        flash('Error approving analysis. Please try again.', 'error')
    
    return redirect(url_for('wikipedia.admin_review'))

@wikipedia_bp.route('/admin/reject/<int:analysis_id>', methods=['POST'])
@login_required
@admin_required
def reject_analysis(analysis_id):
    """Reject an analysis (mark as reviewed but don't cache)"""
    analysis = AnalysisHistory.query.get_or_404(analysis_id)
    
    try:
        admin_notes = request.form.get('admin_notes', 'Rejected by admin')
        
        # Mark as reviewed by adding a "rejected" cache entry
        cache_entry = AnalysisCache(
            article_title=analysis.article_title,
            article_hash=analysis.article_hash,
            model_used=analysis.model_used,
            provider=analysis.provider,
            analysis_text='',  # Empty analysis text indicates rejection
            quality_score=0,   # 0 indicates rejection
            admin_notes=admin_notes,
            approved_by=current_user.id,
            approved_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        db.session.add(cache_entry)
        db.session.commit()
        
        flash('Analysis rejected and marked as reviewed.', 'info')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting analysis: {str(e)}")
        flash('Error rejecting analysis. Please try again.', 'error')
    
    return redirect(url_for('wikipedia.admin_review'))

@wikipedia_bp.route('/admin/analytics')
@login_required
@admin_required
def admin_analytics():
    """Admin analytics dashboard"""
    # Track admin page view
    track_page_view(request.url, 'Admin Analytics Dashboard')
    
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta
    
    # Get date range (last 30 days by default)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Page view analytics
    total_page_views = PageView.query.filter(PageView.timestamp >= start_date).count()
    unique_visitors = db.session.query(PageView.ip_address).filter(
        PageView.timestamp >= start_date
    ).distinct().count()
    
    # Top pages
    top_pages = db.session.query(
        PageView.page_url,
        func.count(PageView.id).label('views')
    ).filter(
        PageView.timestamp >= start_date
    ).group_by(PageView.page_url).order_by(desc('views')).limit(10).all()
    
    # Search analytics
    total_searches = SearchQuery.query.filter(SearchQuery.timestamp >= start_date).count()
    top_searches = db.session.query(
        SearchQuery.query_text,
        func.count(SearchQuery.id).label('count')
    ).filter(
        SearchQuery.timestamp >= start_date
    ).group_by(SearchQuery.query_text).order_by(desc('count')).limit(10).all()
    
    # User interaction analytics
    total_interactions = UserInteraction.query.filter(UserInteraction.timestamp >= start_date).count()
    interaction_types = db.session.query(
        UserInteraction.interaction_type,
        func.count(UserInteraction.id).label('count')
    ).filter(
        UserInteraction.timestamp >= start_date
    ).group_by(UserInteraction.interaction_type).order_by(desc('count')).all()
    
    # Session analytics
    total_sessions = AnalyticsSession.query.filter(AnalyticsSession.start_time >= start_date).count()
    avg_session_duration = db.session.query(
        func.avg(AnalyticsSession.duration_seconds)
    ).filter(
        AnalyticsSession.start_time >= start_date,
        AnalyticsSession.duration_seconds.isnot(None)
    ).scalar() or 0
    
    bounce_rate = db.session.query(
        func.avg(AnalyticsSession.bounce_rate.cast(db.Integer))
    ).filter(
        AnalyticsSession.start_time >= start_date
    ).scalar() or 0
    
    # Analysis performance
    total_analyses = AnalysisHistory.query.filter(AnalysisHistory.timestamp >= start_date).count()
    analyses_by_user = db.session.query(
        func.count(AnalysisHistory.id).label('anonymous_count')
    ).filter(
        AnalysisHistory.timestamp >= start_date,
        AnalysisHistory.user_id.is_(None)
    ).scalar() or 0
    
    # Cache performance
    cache_hits = AnalysisCache.query.filter(
        AnalysisCache.created_at >= start_date,
        AnalysisCache.hit_count > 0
    ).count()
    
    return render_template('wikipedia/admin_analytics.html',
                         total_page_views=total_page_views,
                         unique_visitors=unique_visitors,
                         top_pages=top_pages,
                         total_searches=total_searches,
                         top_searches=top_searches,
                         total_interactions=total_interactions,
                         interaction_types=interaction_types,
                         total_sessions=total_sessions,
                         avg_session_duration=int(avg_session_duration),
                         bounce_rate=bounce_rate * 100,
                         total_analyses=total_analyses,
                         anonymous_analyses=analyses_by_user,
                         cache_hits=cache_hits,
                         start_date=start_date,
                         end_date=end_date)

# ============================================================================
# COMPREHENSIVE TRACKING SYSTEM
# ============================================================================

def get_client_info():
    """Get client IP, user agent, and session info"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    user_agent = request.headers.get('User-Agent', '')
    session_id = request.headers.get('X-Session-ID') or session.get('session_id')
    
    # Generate session ID if not exists
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    return client_ip, user_agent, session_id

def track_page_view(page_url, page_title=None, load_time=None):
    """Track page views with detailed analytics"""
    try:
        client_ip, user_agent, session_id = get_client_info()
        referrer = request.headers.get('Referer')
        user_id = current_user.id if current_user.is_authenticated else None
        
        page_view = PageView(
            user_id=user_id,
            ip_address=client_ip,
            user_agent=user_agent,
            page_url=page_url,
            page_title=page_title,
            referrer=referrer,
            session_id=session_id,
            timestamp=datetime.utcnow(),
            load_time=load_time
        )
        
        db.session.add(page_view)
        
        # Update session analytics
        update_session_analytics(session_id, user_id, client_ip, user_agent, 'page_view')
        
        db.session.commit()
        current_app.logger.info(f"Page view tracked: {page_url} by {client_ip}")
        
    except Exception as e:
        current_app.logger.error(f"Page view tracking error: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass

def track_search_query(query_text, query_type='wikipedia_search', results_count=None, filters=None):
    """Track user searches and queries"""
    try:
        client_ip, user_agent, session_id = get_client_info()
        user_id = current_user.id if current_user.is_authenticated else None
        
        search_query = SearchQuery(
            user_id=user_id,
            ip_address=client_ip,
            session_id=session_id,
            query_text=query_text,
            query_type=query_type,
            results_count=results_count,
            timestamp=datetime.utcnow(),
            filters_applied=json.dumps(filters) if filters else None
        )
        
        db.session.add(search_query)
        
        # Update session analytics
        update_session_analytics(session_id, user_id, client_ip, user_agent, 'search')
        
        db.session.commit()
        current_app.logger.info(f"Search tracked: '{query_text}' ({query_type}) by {client_ip}")
        
    except Exception as e:
        current_app.logger.error(f"Search tracking error: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass

def track_user_interaction(interaction_type, element_id=None, element_text=None, extra_data=None):
    """Track user clicks, interactions, and engagement"""
    try:
        client_ip, user_agent, session_id = get_client_info()
        user_id = current_user.id if current_user.is_authenticated else None
        page_url = request.url
        
        interaction = UserInteraction(
            user_id=user_id,
            ip_address=client_ip,
            session_id=session_id,
            interaction_type=interaction_type,
            element_id=element_id,
            element_text=element_text,
            page_url=page_url,
            timestamp=datetime.utcnow(),
            extra_data=json.dumps(extra_data) if extra_data else None
        )
        
        db.session.add(interaction)
        
        # Update session analytics
        update_session_analytics(session_id, user_id, client_ip, user_agent, 'interaction')
        
        db.session.commit()
        current_app.logger.info(f"Interaction tracked: {interaction_type} ({element_id}) by {client_ip}")
        
    except Exception as e:
        current_app.logger.error(f"Interaction tracking error: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass

def update_session_analytics(session_id, user_id, client_ip, user_agent, activity_type):
    """Update or create session analytics"""
    try:
        session_analytics = AnalyticsSession.query.filter_by(session_id=session_id).first()
        
        if not session_analytics:
            session_analytics = AnalyticsSession(
                session_id=session_id,
                user_id=user_id,
                ip_address=client_ip,
                user_agent=user_agent,
                start_time=datetime.utcnow(),
                page_views=0,
                interactions=0,
                searches=0,
                analyses_performed=0
            )
            db.session.add(session_analytics)
        
        # Update counters based on activity type
        if activity_type == 'page_view':
            session_analytics.page_views += 1
        elif activity_type == 'interaction':
            session_analytics.interactions += 1
        elif activity_type == 'search':
            session_analytics.searches += 1
        elif activity_type == 'analysis':
            session_analytics.analyses_performed += 1
        
        # Update bounce rate (single page view = bounce)
        session_analytics.bounce_rate = (session_analytics.page_views == 1)
        
        # Update duration
        if session_analytics.start_time:
            duration = datetime.utcnow() - session_analytics.start_time
            session_analytics.duration_seconds = int(duration.total_seconds())
        
    except Exception as e:
        current_app.logger.error(f"Session analytics update error: {str(e)}")

@wikipedia_bp.route('/track/click', methods=['POST'])
def track_click():
    """API endpoint for tracking JavaScript clicks"""
    try:
        data = request.get_json()
        track_user_interaction(
            interaction_type='click',
            element_id=data.get('element_id'),
            element_text=data.get('element_text'),
            extra_data=data.get('extra_data')
        )
        return jsonify({'status': 'tracked'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@wikipedia_bp.route('/track/pageview', methods=['POST'])  
def track_pageview():
    """API endpoint for tracking JavaScript page views"""
    try:
        data = request.get_json()
        track_page_view(
            page_url=data.get('page_url'),
            page_title=data.get('page_title'),
            load_time=data.get('load_time')
        )
        return jsonify({'status': 'tracked'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500