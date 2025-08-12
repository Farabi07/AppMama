from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

class Pagination:

    def __init__(self):
        self._page = 1
        self._size = 10
        self._max_size = 100
        self._total_pages = 1

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value):
        # Validate page to ensure it's an integer and positive
        try:
            self._page = max(int(value), 1)  # Ensure page is at least 1
        except (ValueError, TypeError):
            self._page = 1  # Default to the first page if invalid value

    @property
    def total_pages(self):
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value):
        if isinstance(value, int):
            self._total_pages = value

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        # Validate size to ensure it's an integer within max size limit
        try:
            size = int(value)
            if size > self._max_size:
                self._size = self._max_size
            elif size < 1:
                self._size = 1  # Ensure size is at least 1
            else:
                self._size = size
        except (ValueError, TypeError):
            self._size = 10  # Default to 10 if invalid value

    def paginate_data(self, data):
        paginator = Paginator(data, self.size)
        self.total_pages = paginator.num_pages

        try:
            data = paginator.page(self.page)
        except PageNotAnInteger:
            # If the page is not an integer, return the first page
            data = paginator.page(1)
        except EmptyPage:
            # If the page is empty, return the last page
            data = paginator.page(self.total_pages)

        return data
