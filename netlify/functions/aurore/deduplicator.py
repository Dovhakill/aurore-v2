from netlify_blob import get_store
import hashlib

def check_and_filter_articles(articles):
    """
    Filtre une liste d'articles pour ne garder que ceux qui n'ont pas encore été traités.

    Args:
        articles (list): La liste des articles récupérés de NewsAPI.

    Returns:
        list: La liste des articles qui sont nouveaux.
    """
    if not articles:
        return []

    store = get_store("processed_articles_v1")
    new_articles = []

    for article in articles:
        # L'URL est la clé la plus fiable pour l'unicité
        article_url = article.get('url')
        if not article_url:
            continue

        # Netlify Blob Store n'aime pas les / dans les clés. On utilise un hash.
        key = hashlib.sha256(article_url.encode()).hexdigest()
        
        try:
            existing_entry = store.get(key)
            if existing_entry is None:
                # L'article est nouveau
                new_articles.append(article)
            else:
                print(f"Article déjà traité (doublon) : {article_url}")
        except Exception as e:
            print(f"Erreur d'accès au Blob Store pour la clé {key}: {e}")
            # Par sécurité, on considère qu'on ne peut pas traiter l'article
            continue
            
    return new_articles

def mark_articles_as_processed(articles):
    """
    Enregistre les URLs des articles traités dans le Netlify Blob Store.
    """
    if not articles:
        return

    store = get_store("processed_articles_v1")
    for article in articles:
        article_url = article.get('url')
        if article_url:
            key = hashlib.sha256(article_url.encode()).hexdigest()
            try:
                # On stocke l'URL pour référence future, même si la clé est un hash
                store.set(key, article_url)
                print(f"Article marqué comme traité : {article_url}")
            except Exception as e:
                print(f"Erreur d'écriture dans le Blob Store pour la clé {key}: {e}")