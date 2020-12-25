from rest_framework.pagination import PageNumberPagination


class SmallPageNumberPagination(PageNumberPagination):
    page_size = 10
