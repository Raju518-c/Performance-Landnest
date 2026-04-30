from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Initialize total users count when Django apps are ready
        from cache_config import initialize_total_users_count
        try:
            initialize_total_users_count()
        except Exception as e:
            print(f"Failed to initialize total_users_count: {e}")
        
        # Start background tasks if needed
        # from . import tasks
        # tasks.start_thread()
