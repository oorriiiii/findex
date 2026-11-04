import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
import typer
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from findex.index import build_partial, merge
from findex.crawler import crawl

app = typer.Typer()


@app.command()
def index(
        data_dir: Path = typer.Argument(..., help="Шлях до корпусу документів"),
        out: Path = typer.Option("index.bin", "--out", help="Файл для збереження індексу"),
        workers: int = typer.Option(os.cpu_count(), "--workers", help="Кількість воркерів"),
        executor: str = typer.Option("processes", "--executor", help="Тип екзекутора: serial, threads, processes"),
):
    """Побудова індексу з підтримкою паралелізму."""
    files = sorted(list(data_dir.glob("**/*.txt")))
    if not files:
        typer.echo(f"Файлів не знайдено в {data_dir}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Знайдено файлів: {len(files)}. Запуск з екзекутором: {executor} (воркерів: {workers})")

    chunk_size = max(1, len(files) // workers)
    chunks = []
    current_id = 1

    for i in range(0, len(files), chunk_size):
        chunk_files = files[i:i + chunk_size]
        if chunk_files:
            chunks.append((chunk_files, current_id))
            current_id += len(chunk_files)

    start_time = time.time()
    partial_indices = []

    if executor == "serial":
        for chunk_files, start_id in chunks:
            partial_indices.append(build_partial(chunk_files, start_id))

    elif executor == "threads":
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(build_partial, cf, sid) for cf, sid in chunks]
            for future in as_completed(futures):
                partial_indices.append(future.result())

    elif executor == "processes":
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(build_partial, cf, sid) for cf, sid in chunks]
            for future in as_completed(futures):
                partial_indices.append(future.result())
    else:
        typer.echo(f"Невідомий екзекутор: {executor}", err=True)
        raise typer.Exit(code=1)

    merge_start = time.time()
    final_index = merge(partial_indices)
    merge_time = time.time() - merge_start

    # Збереження індексу через storage (за потреби розкоментуй)
    # from findex.storage import save_index
    # save_index(final_index, out)

    total_time = time.time() - start_time
    typer.echo(f"Індекс побудовано за {total_time:.4f} с (Час злиття: {merge_time:.4f} с)")


@app.command()
def crawl_cmd(
        start_url: str = typer.Argument(..., help="Початковий URL для краулінгу"),
        max_pages: int = typer.Option(200, "--max-pages", help="Максимальна кількість сторінок"),
        concurrency: int = typer.Option(10, "--concurrency", help="Кількість одночасних воркерів"),
        output: Path = typer.Option("corpus.jsonl", "--output", help="Файл для JSONL стріму"),
        log_file: Path = typer.Option("crawl.log", "--log", help="Файл логів краулера"),
        user_agent: str = typer.Option("FindexBot/1.0 (+https://github.com/oorriiiii/findex)", "--user-agent"),
):
    """Асинхронний краулер вебсторінок з інтерфейсом rich."""

    async def run():
        start_time = time.time()
        collected = 0
        errors = 0

        def generate_table():
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Метрика", style="cyan")
            table.add_column("Значення", style="green")

            elapsed = time.time() - start_time
            speed = collected / elapsed if elapsed > 0 else 0.0

            table.add_row("Зібрано сторінок", str(collected))
            table.add_row("Швидкість", f"{speed:.2f} стор/сек")
            table.add_row("Помилки", str(errors))
            table.add_row("Час роботи", f"{elapsed:.1f} сек")
            return Panel(table, title="[bold blue]Findex Async Crawler[/bold blue]", border_style="cyan")

        # Викликаємо crawl() коректно, щоб отримати асинхронний генератор
        crawler_gen = crawl(
            start_url=start_url,
            max_pages=max_pages,
            concurrency=concurrency,
            user_agent=user_agent,
            output_jsonl=output,
            log_file=log_file
        )

        with Live(generate_table(), refresh_per_second=4) as live:
            async for page in crawler_gen:
                collected += 1
                if page["status"] != 200:
                    errors += 1
                live.update(generate_table())

    # Безпечний запуск циклу подій
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Якщо петля вже є (наприклад, у деяких середовищах)
        asyncio.run_coroutine_threadsafe(run(), loop)
    else:
        asyncio.run(run())

    typer.echo(f"Краулінг завершено! Дані збережено у {output}")

    if __name__ == "__main__":
        app()