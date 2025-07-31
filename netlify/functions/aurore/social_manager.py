import os
import tweepy

def post_to_twitter(tweet_text, article_url):
    """
    Publie un tweet avec le texte fourni et un lien vers l'article.
    Nécessite les clés d'API Twitter/X dans les variables d'environnement.
    """
    if not tweet_text:
        print("Aucun texte de tweet fourni. Publication annulée.")
        return None

    full_tweet = f"{tweet_text} \n\nLire l'article complet : {article_url}"

    try:
        # --- Authentification sécurisée via les variables d'environnement ---
        consumer_key = os.environ.get('TWITTER_API_KEY')
        consumer_secret = os.environ.get('TWITTER_API_SECRET')
        access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
        bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')

        if not all([consumer_key, consumer_secret, access_token, access_token_secret, bearer_token]):
            print("Erreur : Les clés d'API Twitter ne sont pas toutes configurées.")
            return None

        # Utilisation de l'API v2 avec tweepy.Client
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

        # Publication du tweet
        response = client.create_tweet(text=full_tweet)
        tweet_id = response.data['id']
        print(f"Tweet publié avec succès ! ID : {tweet_id}")
        return f"https://twitter.com/user/status/{tweet_id}"

    except Exception as e:
        print(f"Erreur lors de la publication sur Twitter : {e}")
        return None