import pytest
from research_agent.tools.wiki_tool import search_wikipedia

@pytest.mark.asyncio
async def test_wiki_found():
    text, urls, success, error = await search_wikipedia("квантовый компьютер")
    assert success is True
    assert len(text) >= 50
    assert len(urls) == 1
    assert "wikipedia.org" in urls[0]

@pytest.mark.asyncio
async def test_wiki_not_found():
    text, urls, success, error = await search_wikipedia("ываываывафывфыв")
    assert success is False
    assert text == ""