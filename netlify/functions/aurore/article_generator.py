# Ajoutez cet import en haut du fichier
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ... (la fonction create_synthesis reste inchangée) ...

def generate_html(article_data):
    """
    Génère le contenu HTML d'un article à partir des données et d'un template Jinja2.

    Args:
        article_data (dict): Le dictionnaire contenant les données de l'article (titre, chapo, etc.).

    Returns:
        str: Le contenu HTML complet de l'article.
    """
    try:
        # Configure Jinja2 pour charger les templates depuis le dossier /templates
        env = Environment(
            loader=FileSystemLoader('netlify/functions/aurore/templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('article.html')
        
        # Rend le template avec les données de l'article
        html_content = template.render(article=article_data)
        print("Fichier HTML généré avec succès.")
        return html_content

    except Exception as e:
        print(f"Erreur lors de la génération du fichier HTML : {e}")
        return None