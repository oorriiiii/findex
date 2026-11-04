import asyncio
import httpx
from findex.crawler import canonicalize_url, RobotsCache

def test_canonicalize_url():
    assert canonicalize_url("/subpage", "https://example.com/path/") == "https://example.com/subpage"
    assert canonicalize_url("https://EXAMPLE.com/Path?b=2&a=1") == "https://example.com/Path?a=1&b=2"
    assert canonicalize_url("ftp://example.com") is None

def test_crawler_mock():
    async def run_test():
        def handle_request(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/robots.txt":
                return httpx.Response(200, text="User-agent: *\nAllow: /")
            return httpx.Response(404)

        transport = httpx.MockTransport(handle_request)
        async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
            cache = RobotsCache("FindexBot")
            allowed = await cache.can_fetch(client, "https://example.com/")
            assert allowed is True

    asyncio.run(run_test())