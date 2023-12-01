

def extract_title_and_desc(feed):
    # Extract title from the <title> tag
    title_tag = feed.find('title')
    title = title_tag.text.strip() if title_tag else None

    # Extract description from the meta tag with name="description"
    description_tag = feed.find('meta', attrs={'name': 'description'})
    description = description_tag.get('content').strip() if description_tag and description_tag.get(
        'content') else None
    return [title, description]
