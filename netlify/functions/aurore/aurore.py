import os
import json
import requests
import hashlib
from datetime import datetime

# --- Dépendances à installer ---
from github import Github
import google.generativeai as genai
from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify
import tweepy

# ==============================================================================
# MODULE : DEDUPLICATOR (Nouvelle version avec kvdb.io)
# ==============================================================================
def get_processed_urls(bucket_url):
    """Lit les URLs depuis le bucket kvdb.io."""
    try:
        res = requests.get(bucket_url)
        res.raise_for_status()
        # kvdb renvoie une liste de clés, on les veut dans un set
        return set(res.json())
    except requests.exceptions.JSONDecodeError: # Le bucket est peut-être vide
        return set()
    except Exception as e:
        print(f"Erreur en lisant le bucket kvdb : {e}")
        return None

def check_and_filter_articles(articles, processed_urls):
    """Filtre les articles qui n'ont pas encore été traités."""
    if processed_urls is None: return []
    
    new_articles = []
    for article in articles:
        # On utilise un hash de l'URL comme clé pour kvdb
        key = hashlib.sha256(article.get('url').encode()).hexdigest()
        if key not in processed_urls:
            new_articles.append(article)
    return new_articles

def mark_articles_as_processed(articles, bucket_url):
    """Met à jour le bucket kvdb.io avec les nouvelles clés."""
    for article in articles:
        key = hashlib.sha256(article.get('url').encode()).hexdigest()
        try:
            # On envoie une requête POST pour chaque nouvelle clé
            requests.post(bucket_url + "/" + key)
        except Exception as e:
            print(f"Erreur en écrivant dans le bucket kvdb : {e}")

# ==============================================================================
# MODULES : NEWS, AI, GITHUB, SOCIAL (inchangés)
# ==============================================================================
def get_top_articles(topic, api_key, article_count=3):
    url = "https://newsapi.org/v2/everything"
    sources = "reuters,bbc-news"
    params = {'q': topic, 'sources': sources, 'language': 'en', 'sortBy': 'publishedAt', 'apiKey': api_key}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('status') != 'ok': return []
        articles = data.get('articles', [])
        return [{'title': a.get('title'), 'description': a.get('description'), 'content': a.get('content'), 'url': a.get('url'), 'source_name': a.get('source', {}).get('name')} for a in articles[:article_count]]
    except Exception as e: print(f"Erreur NewsAPI : {e}"); return None

def create_synthesis(articles, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')
    prompt_header = """# RÔLE\nTu es 'Aurore', un assistant journaliste pour 'L'Horizon Libre'. Ta mission est de créer une synthèse neutre et factuelle en te basant **uniquement** sur les sources fournies.\n\n# FORMAT DE SORTIE\nRéponds **uniquement** en JSON valide.\n\n{\n  "titre": "...",\n  "chapo": "...",\n  "corps_article": ["...", "..."],\n  "conclusion": "...",\n  "suggestion_image": "...",\n  "mots_cles_seo": ["...", "..."],\n  "sources_citees": ["...", "..."],\n  "suggestion_tweet": "..."\n}\n\n# ARTICLES SOURCES\n---\n"""
    article_content_str = ""
    for i, article in enumerate(articles):
        content = article['content'] if article['content'] else article['description']
        article_content_str += f"### SOURCE {i+1}: {article['source_name']}\n- Titre: {article['title']}\n- Contenu: {content}\n---\n"
    full_prompt = prompt_header + article_content_str
    try:
        response = model.generate_content(full_prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except Exception as e: print(f"Erreur Gemini : {e}"); return None

def generate_html(article_data):
    env = Environment(loader=FileSystemLoader('./netlify/functions/aurore/templates'), autoescape=select_autoescape(['html']))
    template = env.get_template('article.html')
    return template.render(article=article_data)

def create_pull_request(token, repo_name, article_title, html_content):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        slug_title = slugify(article_title)
        branch_name = f"aurore/article-{slug_title[:40]}-{datetime.now().strftime('%Y%m%d%H%M')}"
        source_branch = repo.get_branch(repo.default_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_branch.commit.sha)
        file_path = f"articles/{slug_title}.html"
        commit_message = f"feat: Ajout de l'article '{article_title}'"
        repo.create_file(path=file_path, message=commit_message, content=html_content, branch=branch_name)
        pr = repo.create_pull(title=f"Proposition d'article : {article_title}", body="Article généré par Aurore.", head=branch_name, base=repo.default_branch)
        return pr.html_url
    except Exception as e: print(f"Erreur GitHub : {e}"); return None

def post_to_twitter(tweet_text, article_url):
    full_tweet = f"{tweet_text} \n\nLire l'article complet : {article_url}"
    try:
        client = tweepy.Client(bearer_token=os.environ.get('TWITTER_BEARER_TOKEN'), consumer_key=os.environ.get('TWITTER_API_KEY'), consumer_secret=os.environ.get('TWITTER_API_SECRET'), access_token=os.environ.get('TWITTER_ACCESS_TOKEN'), access_token_secret=os.environ.get('TWITTER_ACCESS_TOKEN_SECRET'))
        response = client.create_tweet(text=full_tweet)
        return f"https://twitter.com/user/status/{response.data['id']}"
    except Exception as e: print(f"Erreur Twitter : {e}"); return None

# ==============================================================================
# FONCTION PRINCIPALE (HANDLER) - MISE À JOUR
# ==============================================================================
def handler(event, context):
    print("--- Aurore démarre sa mission (version kvdb.io) ---")
    
    # Récupération des secrets
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GITHUB_TOKEN = os.environ.get('AURORE_GITHUB_TOKEN')
    GITHUB_REPO = os.environ.get('GITHUB_REPO_NAME')
    KVDB_BUCKET_URL = os.environ.get('KVDB_BUCKET_URL')
    topic = "france"

    try:
        processed_urls = get_processed_urls(KVDB_BUCKET_URL)
        
        all_articles = get_top_articles(topic, NEWS_API_KEY)
        if not all_articles: return {'statusCode': 200, 'body': 'Aucun article source trouvé.'}

        new_articles = check_and_filter_articles(all_articles, processed_urls)
        if not new_articles: return {'statusCode': 200, 'body': 'Aucun nouvel article à traiter.'}

        article_data = create_synthesis(new_articles, GEMINI_API_KEY)
        if not article_data: raise ValueError("Impossible de générer la synthèse.")

        html_content = generate_html(article_data)
        if not html_content: raise ValueError("Impossible de générer le HTML.")

        pr_url = create_pull_request(GITHUB_TOKEN, GITHUB_REPO, article_data['titre'], html_content)
        if not pr_url: raise ValueError("Impossible de créer la Pull Request.")

        tweet_url = post_to_twitter(article_data.get("suggestion_tweet"), pr_url)
        
        mark_articles_as_processed(new_articles, KVDB_BUCKET_URL)
        
        print("--- Mission d'Aurore terminée avec succès ! ---")
        return { 'statusCode': 200, 'body': json.dumps({ 'message': 'Workflow complet terminé.', 'pull_request_url': pr_url }) }

    except Exception as e:
        print(f"--- ERREUR FATALE DANS LE WORKFLOW D'AURORE --- \n{e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

# Point d'entrée pour l'exécution directe du script
if __name__ == "__main__":
    handler(event=None, context=None)
