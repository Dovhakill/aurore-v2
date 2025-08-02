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
# MODULE : DEDUPLICATOR (version kvdb.io)
# ==============================================================================
def get_processed_urls(bucket_url):
    """Lit les URLs depuis le bucket kvdb.io."""
    try:
        res = requests.get(bucket_url)
        res.raise_for_status()
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
        key = hashlib.sha256(article.get('url').encode()).hexdigest()
        if key not in processed_urls:
            new_articles.append(article)
    return new_articles

def mark_articles_as_processed(articles, bucket_url):
    """Met à jour le bucket kvdb.io avec les nouvelles clés."""
    for article in articles:
        key = hashlib.sha256(article.get('url').encode()).hexdigest()
        try:
            requests.post(bucket_url + "/" + key)
        except Exception as e:
            print(f"Erreur en écrivant dans le bucket kvdb : {e}")

# (Le début du fichier avec les imports et les autres fonctions ne change pas)

# ==============================================================================
# MODULE : NEWS (mis à jour pour accepter une source)
# ==============================================================================
def get_top_articles(source, api_key, article_count=3):
    url = "https://newsapi.org/v2/everything"
    # Le sujet 'a' est un placeholder pour chercher "tout" ce qui est récent.
    # On filtre principalement par la source.
    params = {'q': 'a', 'sources': source, 'language': 'en', 'sortBy': 'publishedAt', 'apiKey': api_key}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('status') != 'ok': return []
        articles = data.get('articles', [])
        # On ne prend que le tout premier article le plus récent
        return [{'title': a.get('title'), 'description': a.get('description'), 'content': a.get('content'), 'url': a.get('url'), 'source_name': a.get('source', {}).get('name')} for a in articles[:1]]
    except Exception as e: print(f"Erreur NewsAPI : {e}"); return None

# ... (les autres fonctions comme create_synthesis, generate_html, etc. ne changent pas) ...

# ==============================================================================
# FONCTION PRINCIPALE (HANDLER) - VERSION MULTI-SOURCE
# ==============================================================================
def handler(event, context):
    
    # --- Le script reçoit la source à traiter depuis l'extérieur ---
    source_a_traiter = os.environ.get('NEWS_SOURCE')
    print(f"--- Aurore démarre sa mission pour la source : {source_a_traiter} ---")
    
    # Récupération des secrets
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GITHUB_TOKEN = os.environ.get('AURORE_GITHUB_TOKEN')
    GITHUB_REPO = os.environ.get('REPO_CIBLE')
    KVDB_BUCKET_URL = os.environ.get('KVDB_BUCKET_URL')
    
    try:
        print(f"Étape 1: Lecture de la base de données kvdb.io pour {source_a_traiter}...")
        processed_urls = get_processed_urls(KVDB_BUCKET_URL)
        
        print(f"\nÉtape 2: Récupération du dernier article de {source_a_traiter} depuis NewsAPI...")
        all_articles = get_top_articles(source_a_traiter, NEWS_API_KEY)
        if not all_articles:
            print("-> NewsAPI n'a retourné aucun article. Mission terminée.")
            return

        print(f"-> Trouvé {len(all_articles)} article.")

        print("\nÉtape 3: Filtrage des doublons...")
        new_articles = check_and_filter_articles(all_articles, processed_urls)
        if not new_articles:
            print("-> L'article trouvé a déjà été traité. Mission terminée.")
            return

        print(f"-> 1 nouvel article va être traité.")

        # ... (le reste de la fonction est identique) ...
        # ... (Étape 4: Synthèse, Étape 5: HTML, etc...)

    except Exception as e:
        print(f"--- ERREUR FATALE DANS LE WORKFLOW D'AURORE POUR {source_a_traiter} --- \n{e}")
        raise e

# Point d'entrée pour l'exécution directe du script
if __name__ == "__main__":
    handler(event=None, context=None)

