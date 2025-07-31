import requests

def get_top_articles(topic, api_key, article_count=3):
    """
    Récupère les derniers articles pour un sujet donné depuis des sources spécifiques (Reuters, BBC).

    Args:
        topic (str): Le sujet de recherche.
        api_key (str): La clé API pour NewsAPI.
        article_count (int): Le nombre d'articles à retourner.

    Returns:
        list: Une liste de dictionnaires, chaque dictionnaire représentant un article.
              Retourne None en cas d'erreur.
    """
    if not api_key:
        print("Erreur : La clé API de NewsAPI n'est pas fournie.")
        return None

    url = "https://newsapi.org/v2/everything"
    
    # On cible spécifiquement Reuters et la BBC pour la neutralité
    sources = "reuters,bbc-news"
    
    params = {
        'q': topic,
        'sources': sources,
        'language': 'en', # Les dépêches de ces agences sont principalement en anglais
        'sortBy': 'publishedAt', # On trie par date de publication pour avoir les plus récents
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get('status') != 'ok':
            print(f"Erreur de l'API NewsAPI : {data.get('message')}")
            return None

        articles = data.get('articles', [])
        if not articles:
            print("Aucun article trouvé pour ce sujet dans les sources ciblées.")
            return []
        
        top_articles = []
        for article in articles[:article_count]:
            top_articles.append({
                'title': article.get('title'),
                'description': article.get('description'),
                'content': article.get('content'),
                'url': article.get('url'),
                'source_name': article.get('source', {}).get('name')
            })
        
        print(f"{len(top_articles)} articles trouvés et traités avec succès depuis Reuters/BBC.")
        return top_articles

    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion à NewsAPI : {e}")
        return None