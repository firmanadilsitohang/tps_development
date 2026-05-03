"""
Service layer for News/Announcement operations.
"""
from app import db
from app.models.development import News


class NewsService:
    """Business logic for News operations."""

    @staticmethod
    def get_all_news():
        """Get all news ordered by creation date (newest first)."""
        return News.query.order_by(News.created_at.desc()).all()

    @staticmethod
    def get_news_by_id(news_id):
        """Get news by ID."""
        return News.query.get(news_id)

    @staticmethod
    def get_news_by_category(category):
        """Get all news by category."""
        return News.query.filter_by(category=category).order_by(News.created_at.desc()).all()

    @staticmethod
    def _sanitize(data):
        """Sanitize input data to prevent XSS."""
        from app.services.security import sanitize_html, sanitize_text
        return {
            'title': sanitize_text(data.get('title', ''), 200),
            'category': sanitize_text(data.get('category', 'News'), 20),
            'content': sanitize_html(data.get('content', '')),
            'target_type': sanitize_text(data.get('target_type', 'all'), 20),
            'target_users': data.get('target_users', [])
        }

    @staticmethod
    def create_news(data):
        """
        Create new news from data dictionary.
        Returns (success: bool, news: News or None, message: str)
        """
        try:
            data = NewsService._sanitize(data)
            target_users_list = data.get('target_users', [])
            target_users_str = ""
            if data.get('target_type') == 'specific' and target_users_list:
                if isinstance(target_users_list, str):
                    target_users_str = target_users_list
                else:
                    target_users_str = ",".join(target_users_list)

            news = News(
                title=data.get('title'),
                category=data.get('category', 'News'),
                content=data.get('content'),
                target_type=data.get('target_type', 'all'),
                target_users=target_users_str
            )
            db.session.add(news)
            db.session.commit()
            return True, news, "News created successfully"
        except Exception as e:
            db.session.rollback()
            return False, None, str(e)

    @staticmethod
    def update_news(news, data):
        """
        Update existing news with data dictionary.
        Returns (success: bool, message: str)
        """
        try:
            data = NewsService._sanitize(data)
            if 'title' in data:
                news.title = data['title']
            if 'category' in data:
                news.category = data['category']
            if 'content' in data:
                news.content = data['content']
            if 'target_type' in data:
                news.target_type = data['target_type']

            target_users_list = data.get('target_users', [])
            if news.target_type == 'specific' and target_users_list:
                if isinstance(target_users_list, str):
                    news.target_users = target_users_list
                else:
                    news.target_users = ",".join(target_users_list)
            else:
                news.target_users = ""

            db.session.commit()
            return True, "News updated successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def delete_news(news):
        """
        Delete news.
        Returns (success: bool, message: str)
        """
        try:
            db.session.delete(news)
            db.session.commit()
            return True, "News deleted successfully"
        except Exception as e:
            db.session.rollback()
            return False, str(e)
