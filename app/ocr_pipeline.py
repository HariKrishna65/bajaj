async def prepare_pages(document_url: str):
    """
    We do NOT download or convert the document.

    We simply send the document URL directly to Gemini.
    This avoids all image/pdf processing libraries
    so it works perfectly on Python 3.13 (Render default).
    """

    # Return in same structure as before: (page_no, data)
    return [("1", document_url)]
