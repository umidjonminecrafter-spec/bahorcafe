from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class OptionalPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def paginate_queryset(self, queryset, request, view=None):
        # Support limit parameter or disabling pagination if requested
        limit = request.query_params.get('limit')
        if limit is not None:
            try:
                self.page_size = int(limit)
            except (ValueError, TypeError):
                pass
        
        no_page = request.query_params.get('no_page') or request.query_params.get('all')
        if no_page in ['true', '1', 'yes']:
            return None

        return super().paginate_queryset(queryset, request, view)
