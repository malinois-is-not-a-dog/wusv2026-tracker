#!/usr/bin/env python3
"""src/app.html + CSS → index.html（1ファイル）"""
import pathlib
root = pathlib.Path(__file__).resolve().parent.parent
css = (root/"src/base.css").read_text() + "\n" + (root/"src/extra.css").read_text()
html = (root/"src/app.html").read_text().replace("/*__CSS__*/", css)
(root/"index.html").write_text(html)
print("index.html", len(html))
