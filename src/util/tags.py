def path_between_tags_exists(tag_from, tag_to):
    queue = tag_from.members
    visited = set()

    while len(queue) > 0:
        tag = queue.pop()
        if tag == tag_to:
            return True
        if not tag in visited:
            visited.add(tag)
            queue += tag.members
    return False
