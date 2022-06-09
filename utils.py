#!/usr/bin/python3

from bs4 import BeautifulSoup


def convert_html_to_text(html: str) -> str:
    bs = BeautifulSoup(html, "html.parser")
    return bs.get_text()
