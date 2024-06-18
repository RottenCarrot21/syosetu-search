from __future__ import annotations
import re
import io
import json
import gzip
import httpx
import asyncio
from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Button, Select, Header

# Desired information attributes
attrs = ["title", "writer", "story", "genre", "ncode", "length"]

# Mapping from attributes to 'of' parameters
attr2of = {
    "title": "t",
    "ncode": "n",
    "userid": "u",
    "writer": "w",
    "story": "s",
    "biggenre": "bg",
    "genre": "g",
    "keyword": "k",
    "general_firstup": "gf",
    "general_lastup": "gl",
    "noveltype": "nt",
    "end": "e",
    "general_all_no": "ga",
    "length": "l",
    "time": "ti",
    "isstop": "i",
    "isr15": "ir",
    "isbl": "ibl",
    "isgl": "igl",
    "iszankoku": "izk",
    "istensei": "its",
    "istenni": "iti",
    "pc_or_k": "p",
    "global_point": "gp",
    "daily_point": "dp",
    "weekly_point": "wp",
    "monthly_point": "mp",
    "quarter_point": "qp",
    "yearly_point": "yp",
    "fav_novel_cnt": "f",
    "impression_cnt": "imp",
    "review_cnt": "r",
    "all_point": "a",
    "all_hyoka_cnt": "ah",
    "sasie_cnt": "sa",
    "kaiwaritu": "ka",
    "novelupdated_at": "nu",
    "updated_at": "ua",
}
ORDER_OPTIONS = [
    ("新着更新順", "new"),
    ("ブックマーク数の多い順", "favnovelcnt"),
    ("レビュー数の多い順", "reviewcnt"),
    ("総合ポイントの高い順", "hyoka"),
    ("総合ポイントの低い順", "hyokaasc"),
    ("日間ポイントの高い順", "dailypoint"),
    ("週間ポイントの高い順", "weeklypoint"),
    ("月間ポイントの高い順", "monthlypoint"),
    ("四半期ポイントの高い順", "quarterpoint"),
    ("年間ポイントの高い順", "yearlypoint"),
    ("感想の多い順", "impressioncnt"),
    ("評価者数の多い順", "hyokacnt"),
    ("評価者数の少ない順", "hyokacntasc"),
    ("週間ユニークユーザの多い順", "weekly"),
    ("作品本文の文字数が多い順", "lengthdesc"),
    ("作品本文の文字数が少ない順", "lengthasc"),
    ("新着投稿順", "ncodedesc"),
    ("更新が古い順", "old"),
]
VALUE_TO_LABEL = {value: label for label, value in ORDER_OPTIONS}


async def get_allcount_for_keyword(url, keyword, order):
    payload = {
        "gzip": 5,
        "out": "json",
        "lim": 1,
        "order": order,
        "keyword": 1,
        "word": keyword,
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=payload)
            res.raise_for_status()
        except httpx.HTTPStatusError:
            return None
    gzip_file = io.BytesIO(res.content)
    with gzip.open(gzip_file, "rt") as f:
        json_data = f.read()
    json_data = json.loads(json_data)
    return json_data[0]["allcount"]


async def get_info(url, keyword, allcount, lim_per_page, page_no, order):
    st = (page_no - 1) * lim_per_page + 1
    payload = {
        "gzip": 5,
        "out": "json",
        "of": "-".join([attr2of[attr] for attr in attrs]),
        "lim": lim_per_page,
        "st": st,
        "order": order,
        "keyword": 1,
        "word": keyword,
    }
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, params=payload)
            res.raise_for_status()
        except httpx.HTTPStatusError:
            return []
    gzip_file = io.BytesIO(res.content)
    with gzip.open(gzip_file, "rt") as f:
        json_data = f.read()
    json_data = json.loads(json_data)
    return json_data[1:]


class SyosetuApp(App):
    CSS_PATH = "search.tcss"
    App.title = "小説家になろう検索"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="キーワードで検索", id="search_input")
        yield Select(options=ORDER_OPTIONS, id="order_dropdown", prompt="並べ順")
        yield Button("Submit", id="submit", variant="success")
        with VerticalScroll(id="results-container"):
            yield Markdown(id="results")

    def on_mount(self) -> None:
        """Called when app starts."""
        self.query_one(Input).focus()
        self.debounce_task: asyncio.Task | None = None

    async def on_button_pressed(self, message: Button.Pressed) -> None:
        """A coroutine to handle button press."""
        if message.button.id == "submit":
            word = self.query_one("#search_input", Input).value
            order = VALUE_TO_LABEL.get(self.query_one("#order_dropdown", Select).value)
            if word:
                await self.query_one("#results", Markdown).update("Now loading...")
                self.lookup_word(word, order)
            else:
                await self.query_one("#results", Markdown).update("")

    @work(exclusive=True)
    async def lookup_word(self, word: str, order: str) -> None:
        md = await self.make_word_markdown(word, order)
        await self.query_one("#results", Markdown).update(md)

    async def make_word_markdown(self, word: str, order: str) -> str:
        """Convert the results into markdown."""
        lines = []
        url = "https://api.syosetu.com/novelapi/api/"
        keyword = word
        allcount = await get_allcount_for_keyword(url, keyword, order)
        if allcount is None:
            return "エラーが発生しました。やり直してください。"
        lim_per_page = 30
        page_no = 1
        lines.append("---")
        lines.append(f"{keyword}の検索結果")
        lines.append("---")
        lines.append("---")
        pattern = r"\[(.*?)\]\((.*?)\)"

        def replace_link(match):
            text = match.group(1)
            url = match.group(2)
            return f"{text} ({url})"

        for info in await get_info(
            url, keyword, allcount, lim_per_page, page_no, order
        ):
            lines.append(f"# {info['title']}\n")
            lines.append(f"###### {info['writer']}\n")
            lines.append(
                f"###### {info['ncode']}(https://ncode.syosetu.com/{info['ncode']}/)\n"
            )
            lines.append(f"##### {re.sub(pattern, replace_link, info['story'])}")
            lines.append(f"\n###### ジャンル：{info['genre']} 文章量：{info['length']}字")
            lines.append("---")
        return "\n".join(lines)


if __name__ == "__main__":
    app = SyosetuApp()
    app.run()
