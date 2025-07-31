import os
from github import Github
from datetime import datetime
from slugify import slugify

def create_pull_request(token, repo_name, article_title, html_content):
    """
    Crée une nouvelle branche, y ajoute un fichier article, et ouvre une Pull Request.

    Args:
        token (str): Token d'accès personnel GitHub.
        repo_name (str): Le nom du dépôt (ex: "votre-nom/votre-repo").
        article_title (str): Le titre de l'article pour le nom de fichier et le commit.
        html_content (str): Le contenu HTML de l'article à ajouter.

    Returns:
        str: L'URL de la Pull Request créée, ou None en cas d'erreur.
    """
    if not all([token, repo_name, article_title, html_content]):
        print("Erreur: Données manquantes pour la création de la PR GitHub.")
        return None

    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # 1. Créer un nom de branche unique
        slug_title = slugify(article_title)
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        branch_name = f"aurore/article-{slug_title[:40]}-{timestamp}"
        
        # 2. Créer la nouvelle branche à partir de la branche principale ('main' ou 'master')
        source_branch = repo.get_branch(repo.default_branch)
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_branch.commit.sha)
        print(f"Branche '{branch_name}' créée avec succès.")

        # 3. Créer le fichier sur la nouvelle branche
        file_path = f"articles/{slug_title}.html" # Assurez-vous que ce chemin correspond à votre site
        commit_message = f"feat: Ajout de l'article '{article_title}'"
        
        repo.create_file(
            path=file_path,
            message=commit_message,
            content=html_content,
            branch=branch_name
        )
        print(f"Fichier '{file_path}' ajouté à la branche.")

        # 4. Créer la Pull Request
        pr = repo.create_pull(
            title=f"Proposition d'article : {article_title}",
            body="Cet article a été généré automatiquement par Aurore. Veuillez le relire, l'approuver et le fusionner.",
            head=branch_name,
            base=repo.default_branch
        )
        print(f"Pull Request créée avec succès : {pr.html_url}")
        
        return pr.html_url

    except Exception as e:
        print(f"Erreur lors de l'interaction avec GitHub : {e}")
        return None