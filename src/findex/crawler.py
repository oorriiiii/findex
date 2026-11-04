import asyncio
import json
import logging
import random
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional, Set, Tuple
import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

logger = logging.getLogger("findex.crawler")


def canonicalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    """Канонізує URL: схема і хост у нижньому регістрі, відкидання фрагментів тощо."""
    if base_url:
        url = urllib.parse.urljoin(base_url, url)

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"

    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query_params.sort()
    query = urllib.parse.urlencode(query_params)

    normalized = urllib.parse.ParseResult(
        scheme=scheme,
        netloc=netloc,
        path=path,
        params="",
        query=query,
        fragment=""
    )
    return urllib.parse.urlunparse(normalized)


class RobotsCache:
    """Кешує правила robots.txt для кожного хоста."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}

    async def can_fetch(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin not in self.parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{origin}/robots.txt"
            try:
                response = await client.get(robots_url, timeout=5.0, follow_redirects=True)
                if response.status_code == 200:
                    rp.parse(response.text.splitlines())
                elif response.status_code in (401, 403):
                    rp.allow_all = False
                else:
                    rp.allow_all = True
            except Exception:
                rp.allow_all = True
            self.parsers[origin] = rp

        return self.parsers[origin].can_fetch(self.user_agent, url)


async def fetch_page(
        client: httpx.AsyncClient,
        url: str,
        user_agent: str
) -> Tuple[str, int, float, Optional[bytes]]:
    """Асинхронно завантажує сторінку з підтримкою повторів (429, 5xx, timeouts) і Retry-After."""
    headers = {"User-Agent": user_agent}
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries + 1):
        start_time = asyncio.get_running_loop().time()
        try:
            async with asyncio.timeout(10.0):
                response = await client.get(url, headers=headers, follow_redirects=True)
                elapsed = asyncio.get_running_loop().time() - start_time

                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < max_retries:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            delay = float(retry_after)
                        else:
                            delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)

                        logger.warning(f"Статус {response.status_code} для {url}. Повтор через {delay:.2f}с")
                        await asyncio.sleep(delay)
                        continue

                return url, response.status_code, elapsed, response.content

        except (httpx.TimeoutException, asyncio.TimeoutError) as e:
            elapsed = asyncio.get_running_loop().time() - start_time
            if attempt < max_retries:
                delay = (base_delay * (2 ** attempt)) + random.uniform(0, 1)
                logger.warning(f"Таймаут для {url}. Повтор через {delay:.2f}с: {e}")
                await asyncio.sleep(delay)
                continue
            return url, 408, elapsed, None

        except Exception as e:
            elapsed = asyncio.get_running_loop().time() - start_time
            logger.error(f"Помилка запиту до {url}: {e}")
            return url, 0, elapsed, None

    return url, 0, 0.0, None


async def crawl(
        start_url: str,
        max_pages: int,
        concurrency: int,
        user_agent: str,
        output_jsonl: Path,
        log_file: Path
) -> AsyncGenerator[dict, None]:
    """Асинхронний краулер із чергою, семафорами, обходом robots.txt та стрімінгом у JSONL."""

    logger.handlers.clear()
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)
    logger.setLevel(logging.INFO)

    visited: Set[str] = {start_url}
    url_queue: asyncio.Queue[str] = asyncio.Queue()
    results_queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

    await url_queue.put(start_url)

    global_semaphore = asyncio.Semaphore(concurrency)
    host_semaphores: Dict[str, asyncio.Semaphore] = {}
    host_last_access: Dict[str, float] = {}

    robots_cache = RobotsCache(user_agent)

    collected_count = 0
    active_requests = 0

    async with httpx.AsyncClient() as client:

        async def worker():
            nonlocal collected_count, active_requests
            while True:
                try:
                    url = await asyncio.wait_for(url_queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    if active_requests == 0 and url_queue.empty():
                        break
                    continue

                if collected_count >= max_pages:
                    url_queue.task_done()
                    break

                parsed_url = urllib.parse.urlparse(url)
                netloc = parsed_url.netloc

                if netloc not in host_semaphores:
                    host_semaphores[netloc] = asyncio.Semaphore(1)

                allowed = await robots_cache.can_fetch(client, url)
                if not allowed:
                    logger.info(f"Заборонено robots.txt: {url}")
                    url_queue.task_done()
                    continue

                async with host_semaphores[netloc]:
                    now = asyncio.get_running_loop().time()
                    last_time = host_last_access.get(netloc, 0.0)
                    elapsed_since_last = now - last_time
                    if elapsed_since_last < 0.5:
                        await asyncio.sleep(0.5 - elapsed_since_last)
                    host_last_access[netloc] = asyncio.get_running_loop().time()

                    active_requests += 1
                    async with global_semaphore:
                        fetched_url, status, elapsed, content = await fetch_page(client, url, user_agent)
                    active_requests -= 1

                page_data = {
                    "url": fetched_url,
                    "status": status,
                    "elapsed": elapsed,
                    "text": ""
                }

                if status == 200 and content:
                    try:
                        html = HTMLParser(content.decode("utf-8", errors="ignore"))
                        text_content = html.body.text(separator=" ") if html.body else ""
                        page_data["text"] = " ".join(text_content.split())

                        if collected_count + url_queue.qsize() < max_pages:
                            for node in html.css("a[href]"):
                                href = node.attributes.get("href")
                                canon = canonicalize_url(href, base_url=fetched_url)
                                if canon and canon not in visited:
                                    visited.add(canon)
                                    await url_queue.put(canon)
                    except Exception as e:
                        logger.error(f"Помилка парсингу HTML для {fetched_url}: {e}")

                collected_count += 1
                logger.info(f"[{collected_count}/{max_pages}] Оброблено: {fetched_url} [Статус: {status}]")

                # Записуємо у файл JSONL
                with open(output_jsonl, "a", encoding="utf-8") as f:
                    f.write(json.dumps(page_data, ensure_ascii=False) + "\n")

                await results_queue.put(page_data)
                url_queue.task_done()

        # Запускаємо воркерів та менеджер збору результатів
        try:
            async with asyncio.TaskGroup() as tg:
                workers = [tg.create_task(worker()) for _ in range(concurrency)]

                # Завдання для закриття черги результатів, коли всі воркери завершаться
                async def monitor():
                    await asyncio.gather(*workers)
                    await results_queue.put(None)  # сигнал завершення

                monitor_task = tg.create_task(monitor())

                # По черзі віддаємо результати назовні (yield)
                while True:
                    res = await results_queue.get()
                    if res is None:
                        break
                    yield res
                    results_queue.task_done()

        except Exception as e:
            logger.error(f"Помилка в TaskGroup: {e}")