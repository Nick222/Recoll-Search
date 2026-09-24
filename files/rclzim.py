#!/usr/bin/env python3

"""
Recoll filter for Zim Wiki pages.

Converts Zim Wiki markup into plain searchable text.

The original Zim file is never modified.
The cleaned text is returned to Recoll as text/html.
"""

import re
import html

import rclexecm
from rclbasehandler import RclBaseHandler


# ----------------------------------------------------------------------
# Technical Zim page header
#
# Remove standard Zim properties at the beginning of the file.
# ----------------------------------------------------------------------

TECHNICAL_HEADER = re.compile(
    r"""
    \A
    (?:
        (?:Content-Type|Wiki-Format|Creation-Date):[^\n]*\n
    )+
    [ \t\r]*\n?
    """,
    re.VERBOSE,
)


# ----------------------------------------------------------------------
# Zim links
#
# [[target|label]] -> label
# [[target]]       -> target
#
# Examples:
#
# [[http://yandex.ru|Яндекс]]
#     -> Яндекс
#
# [[:0 Вход:TMP:2026-09-20-0|2026-09-20-0]]
#     -> 2026-09-20-0
# ----------------------------------------------------------------------

LINK_WITH_LABEL = re.compile(
    r"\[\[[^\]\n|]*\|([^\]\n]*)\]\]"
)

LINK_WITHOUT_LABEL = re.compile(
    r"\[\[([^\]\n]*)\]\]"
)


# ----------------------------------------------------------------------
# Zim headings
#
# ====== Heading ======
# ===== Heading =====
# etc.
#
# Keep the heading text.
# ----------------------------------------------------------------------

HEADING = re.compile(
    r"^\s*=+\s*(.*?)\s*=+\s*$"
)


# ----------------------------------------------------------------------
# Zim tags
#
# @tag      -> tag
#
# The tag remains searchable.
# Only the '@' character is removed.
# ----------------------------------------------------------------------

TAG = re.compile(
    r"(?<![\w@])@([^\s@]+)"
)


# ----------------------------------------------------------------------
# Zim inline formatting
#
# Remove formatting markers while preserving their contents.
#
# **bold**
# __underline__
# //italic//
# ''monospace''
# ~~strike~~
# ----------------------------------------------------------------------

FORMAT_MARKER = re.compile(
    r"(\*\*|__|//|''|~~)"
)


# ----------------------------------------------------------------------
# Zim images
# ----------------------------------------------------------------------

IMAGE = re.compile(
    r"\{\{\s*(?:[^{}]*[/\\])?([^{}|]+?)\."
    r"(?:png|jpg|jpeg|gif|webp|svg)"
    r"(?:\?[^{}]*)?\s*\}\}",
    re.IGNORECASE,
)


# ----------------------------------------------------------------------
# Zim table separator
#
# |:------|:-----|
# |:----------|:----------|
#
# The separator row itself contains no searchable information.
# ----------------------------------------------------------------------

TABLE_SEPARATOR = re.compile(
    r"""
    ^\s*
    \|?
    (?:
        \s*:?-+:?\s*
        \|+
    )+
    \s*$
    """,
    re.VERBOSE,
)


# ----------------------------------------------------------------------
# Zim table row
#
# | 111 | 222 |
#
# becomes:
#
# 111 222
# ----------------------------------------------------------------------

TABLE_ROW = re.compile(
    r"^\s*\|(.*?)\|\s*$"
)


# ----------------------------------------------------------------------
# List markers
# ----------------------------------------------------------------------

BULLET = re.compile(
    r"^(\s*)\*\s+"
)

NUMBERED = re.compile(
    r"^(\s*)\d+\.\s+"
)


class ZimDump(RclBaseHandler):

    def __init__(self, em):
        super(ZimDump, self).__init__(em)

    def clean_text(self, text):
        """
        Convert Zim Wiki source to searchable plain text.
        """

        # --------------------------------------------------------------
        # 1. Remove technical Zim properties.
        # --------------------------------------------------------------

        text = TECHNICAL_HEADER.sub("", text, count=1)

        result = []

        for line in text.splitlines():

            # ----------------------------------------------------------
            # 2. Headings
            # ----------------------------------------------------------

            match = HEADING.match(line)

            if match:
                line = match.group(1)

            # ----------------------------------------------------------
            # 3. Tables
            # ----------------------------------------------------------

            if TABLE_SEPARATOR.match(line):
                continue

            match = TABLE_ROW.match(line)

            if match:
                cells = match.group(1).split("|")

                cells = [
                    cell.strip()
                    for cell in cells
                ]

                cells = [
                    cell
                    for cell in cells
                    if cell
                ]

                line = " ".join(cells)

            # ----------------------------------------------------------
            # 4. Links
            # ----------------------------------------------------------

            line = LINK_WITH_LABEL.sub(
                lambda m: m.group(1),
                line,
            )

            line = LINK_WITHOUT_LABEL.sub(
                lambda m: m.group(1),
                line,
            )

            # ----------------------------------------------------------
            # 5. Images
            # ----------------------------------------------------------

            line = IMAGE.sub(
                lambda m: m.group(1),
                line,
            )

            # ----------------------------------------------------------
            # 6. Inline formatting
            # ----------------------------------------------------------

            line = FORMAT_MARKER.sub("", line)

            # ----------------------------------------------------------
            # 7. Tags
            # ----------------------------------------------------------

            line = TAG.sub(r"\1", line)

            # ----------------------------------------------------------
            # 8. Basic list markers
            # ----------------------------------------------------------

            line = BULLET.sub(r"\1", line)
            line = NUMBERED.sub(r"\1", line)

            result.append(line)

        # --------------------------------------------------------------
        # 9. Remove excessive empty lines.
        # --------------------------------------------------------------

        cleaned = "\n".join(result)

        cleaned = re.sub(
            r"\n[ \t]*\n(?:[ \t]*\n)+",
            "\n\n",
            cleaned,
        )

        return cleaned.strip()

    def html_text(self, fn):
        """
        Read the Zim file and return cleaned text as HTML.
        """

        with open(
            fn,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as f:
            text = f.read()

        text = self.clean_text(text)

        escaped = html.escape(text)

        return (
            "<html>"
            "<head>"
            '<meta charset="utf-8">'
            "</head>"
            "<body>"
            "<pre>"
            + escaped
            + "</pre>"
            "</body>"
            "</html>"
        ).encode("utf-8")


if __name__ == "__main__":
    proto = rclexecm.RclExecM()
    extract = ZimDump(proto)
    rclexecm.main(proto, extract)
