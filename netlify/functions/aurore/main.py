import os
import json

# --- Nos modules fonctionnels ---
from .news_fetcher import get_top_articles
from .deduplicator import check_and_filter_articles, mark_articles_as_processed
from .article_generator import create_synthesis, generate_html
from .github_manager import create_pull_request
from .social_manager import post_to_twitter

def handler(event, context):
    print("--- Aurore démarre sa mission ---")

    # ... (récupération des clés API et config) ...
    NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_REPO = os.environ.get('GITHUB_REPO_NAME')
    topic = "tendances technologie 2025"

    try:
        # --- ÉTAPE 1: Récupérer les articles sources ---
        all_articles = get_top_articles(topic, NEWS_API_KEY)
        if not all_articles:
            print("Aucun article trouvé par NewsAPI. Mission terminée.")
            return {'statusCode': 200, 'body': 'Aucun article source trouvé.'}

        # --- ÉTAPE 2: Filtrer les doublons ---
        new_articles = check_and_filter_articles(all_articles)
        if not new_articles:
            print("Aucun NOUVEL article à traiter. Mission terminée.")
            return {'statusCode': 200, 'body': 'Aucun nouvel article à traiter.'}
        
        print(f"{len(new_articles)} nouvel(s) article(s) à traiter.")

        # --- ÉTAPE 3: Générer la synthèse avec Gemini ---
        article_data = create_synthesis(new_articles, GEMINI_API_KEY)
        if not article_data:
            raise ValueError("Impossible de générer la synthèse de l'article.")

        # --- ÉTAPE 4: Générer le contenu HTML ---
        html_content = generate_html(article_data)
        if not html_content:
            raise ValueError("Impossible de générer le fichier HTML.")

        # --- ÉTAPE 5: Créer la Pull Request sur GitHub ---
        pr_url = create_pull_request(GITHUB_TOKEN, GITHUB_REPO, article_data['titre'], html_content)
        if not pr_url:
            raise ValueError("Impossible de créer la Pull Request sur GitHub.")

        # --- ÉTAPE 6: Publier sur les réseaux sociaux ---
        tweet_text = article_data.get("suggestion_tweet")
        tweet_url = post_to_twitter(tweet_text, pr_url)

        # --- ÉTAPE 7: Marquer les articles comme traités ---
        mark_articles_as_processed(new_articles)
        
        print("--- Mission d'Aurore terminée avec succès ! ---")
        return { 'statusCode': 200, 'body': json.dumps({ 'message': 'Workflow complet terminé.', 'pull_request_url': pr_url }) }

    except Exception as e:
        print(f"--- ERREUR FATALE DANS LE WORKFLOW D'AURORE --- \n{e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}