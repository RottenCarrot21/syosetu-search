from __future__ import annotations
import re
try:
    import httpx
    import io
    import json
    import gzip
    import requests
except ImportError:
    raise ImportError("Please install httpx with 'pip install httpx' and also requests")


from textual import work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Button
# 欲しい情報
attrs = ["title", "writer", "story", "genre"]

# 項目から of パラメータへの対応付け
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
def get_allcount_for_keyword(url, keyword):
    payload = {
        "gzip": 5,
        "out": "json",
        "lim": 1,
        "order": "new",
        "keyword": 1,
        "word": keyword,
    }
    res = requests.get(url, params=payload)
    if res.status_code != 200:
        return None
    gzip_file = io.BytesIO(res.content)
    with gzip.open(gzip_file, "rt") as f:
        json_data = f.read()
    json_data = json.loads(json_data)
    return json_data[0]["allcount"]


def get_info(url, keyword, allcount, lim_per_page, page_no):
    # 1 ページあたり `lim_per_page` 件表示として、`page_no` ページ目の情報を表示
    st = (page_no - 1) * lim_per_page + 1

    # `allcount` すれすれの場合 `lim_per_page` を上書きしたほうが良い？
    # 今回は実装をさぼる。

    payload = {
        "gzip": 5,
        "out": "json",
        "of": "-".join([attr2of[attr] for attr in attrs]),
        "lim": lim_per_page,
        "st": st,
        "order": "new",
        "keyword": 1,
        "word": keyword,
    }
    res = requests.get(url, params=payload)
    if res.status_code != 200:
        return []
    gzip_file = io.BytesIO(res.content)
    with gzip.open(gzip_file, "rt") as f:
        json_data = f.read()
    json_data = json.loads(json_data)
    return json_data[1:]
class SyosetuApp(App):


    CSS_PATH = "search.tcss"

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search for a word")
        yield Button("Submit", id="submit", variant="success")
        with VerticalScroll(id="results-container"):
            yield Markdown(id="results")

    def on_mount(self) -> None:
        """Called when app starts."""
        # Give the input focus, so we can start typing straight away
        self.query_one(Input).focus()

    async def on_input_changed(self, message: Input.Changed) -> None:
        """A coroutine to handle a text changed message."""
        if message.value:
            self.lookup_word(message.value)
        else:
            # Clear the results
            await self.query_one("#results", Markdown).update("")

    @work(exclusive=True)
    async def lookup_word(self, word: str) -> None:
        md = self.make_word_markdown(word)
        self.query_one("#results", Markdown).update(md)

    def make_word_markdown(self, word: str) -> str:
        """Convert the results in to markdown."""
        lines = []
        url = "https://api.syosetu.com/novelapi/api/"
        keyword = word
        allcount = get_allcount_for_keyword(url, keyword)
        lim_per_page = 30
        page_no = 1
        lines.append("---")
        lines.append(f"{keyword}の検索結果")
        lines.append("---")
        # This regex pattern will match Markdown links
        pattern = r'\[(.*?)\]\((.*?)\)'
        # Replacement function to strip the link formatting
        def replace_link(match):
            text = match.group(1)  # text between []
            url = match.group(2)   # url between ()
            return f'{text} ({url})'
        for i, info in enumerate(get_info(url, keyword, allcount, lim_per_page, page_no)):
            lines.append(f"# {info["title"]}\n")
            lines.append(f"###### {info["writer"]}\n")
            
            lines.append(f"##### {re.sub(pattern, replace_link, info["story"])}")
            lines.append(f"\n###### ジャンル：{info["genre"]}")
            # for attr in attrs:
            #     value = info[attr]
            #     lines.append(f"{attr}: {value}")
            lines.append("---")
        return "\n".join(lines)


if __name__ == "__main__":
    app = SyosetuApp()
    app.run()
