def flatten(categories):
    """Flatten incoming categories list
    >>> flatten({'name':'test'})
    [{'name': 'test', 'parent': None}]
    >>> flatten({'name': 'Category 8', 'children': [{'name': 'Category 22'}, {'name': 'Category 23'}]})
    [{'name': 'Category 8', 'parent': None}, {'name': 'Category 22', 'parent': 'Category 8'}, {'name': 'Category 23', 'parent': 'Category 8'}]
    >>> flatten({'name': 'c1', 'children': [{'name': 'c2', 'children': [{'name': 'c3'}]}]})
    [{'name': 'c1', 'parent': None}, {'name': 'c2', 'parent': 'c1'}, {'name': 'c3', 'parent': 'c2'}]
    >>> flatten({})
    Traceback (most recent call last):
        ...
    ValueError: name field is required.
    """
    result = []
    stack = [categories]

    while stack:
        category = stack.pop()
        name = category.get('name')
        if not name:
            raise ValueError("name field is required.")

        for child in reversed(category.get('children', [])):
            child['parent'] = name
            stack.append(child)

        result.append({'name': name, 'parent': category.get('parent', None)})

    return result


if __name__ == "__main__":
    import doctest

    doctest.testmod()