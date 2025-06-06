from django.db import close_old_connections

class DatabaseConnectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Close any stale database connections before processing request
        close_old_connections()
        
        # Process the request
        response = self.get_response(request)
        
        # Close connections after processing
        close_old_connections()
        
        return response