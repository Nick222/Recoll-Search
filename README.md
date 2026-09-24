# Recoll Search for Zim

A Zim plugin that provides fast full-text search using [Recoll](https://www.lesbonscomptes.com/recoll/).

The plugin is intended for Zim notebooks containing a large amount of text, where Recoll's full-text index can provide faster and more powerful searching than Zim's built-in search.

## Features

* Full-text search using the Recoll index.
* Searches only within the currently open Zim notebook, even when the Recoll index contains several notebooks.
* Results are sorted by Recoll relevance.
* Result list with note names.
* Preview of the selected note.
* Displays:

      * note name;
      * internal Zim heading;
      * note path;
      * creation date;
      * modification date;
      * file size.

* Search-result snippets with the matching text highlighted.
* Navigation between multiple matches in a note.
* Direct navigation from a search result to the corresponding location in the Zim page.
* Uses the original Zim page for the preview, while Recoll provides the search index.

## Requirements

* [Zim](https://zim-wiki.org/)
* [Recoll](https://www.lesbonscomptes.com/recoll/)
* Python bindings for Recoll available to Zim.
* A working Recoll index containing the Zim notebook files.

The plugin was developed and tested with:

* Zim 0.77.2
* Recoll with Zim Wiki pages indexed as `text/x-zim-wiki`

Other versions may require adjustments.

## Installation

Install the plugin in the Zim user plugin directory:

```text
~/.local/share/zim/plugins/recoll_search/
```

The directory should contain the plugin Python file and the usual Zim plugin files.

Restart Zim and enable **Recoll Search** in the plugin preferences.

## Recoll / Zim integration

Recoll normally treats `.txt` files as ordinary text files. Zim pages, however, contain Zim Wiki markup.

This plugin uses a dedicated MIME type:

```text
text/x-zim-wiki
```

The repository contains two files used for this integration:

```text
files/
├── rclzim.py
└── x-zim-wiki.xml
```

### `rclzim.py`

`rclzim.py` is a Recoll filter for Zim Wiki pages.

It converts Zim Wiki source into clean searchable text while leaving the original Zim page unchanged.

Among other things, it handles:

* Zim page headings;
* Zim links;
* tags;
* basic inline formatting;
* images;
* tables;
* lists;
* standard Zim technical headers.

The resulting text is supplied to Recoll for indexing.

### `x-zim-wiki.xml`

This file defines the MIME type:

```text
text/x-zim-wiki
```

and identifies it as a subtype of `text/plain`.

The exact location and installation method for MIME type definitions depends on the operating system and MIME database used by the system.

## Recoll configuration

The following configuration changes are required.

**Do not replace your existing Recoll configuration files with the examples below.**

Recoll configuration files may contain other system-specific or user-specific settings. Add the required entries to the existing files.

### `mimemap`

Add:

```text
.txt = text/x-zim-wiki
```

This associates Zim's `.txt` pages with the Zim Wiki MIME type.

### `mimeconf`

Add the following entries to the existing configuration:

```ini
[index]
text/x-zim-wiki = execm rclzim.py

[icons]
text/x-zim-wiki = zim

[categories]
text = text/x-zim-wiki
```

The important part for indexing is:

```ini
text/x-zim-wiki = execm rclzim.py
```

This tells Recoll to use `rclzim.py` when indexing Zim Wiki pages.

### `mimeview`

Add:

```ini
[open]
text/x-zim-wiki = zim -p %f
```

This allows a result of this MIME type to be opened with Zim.

### `recoll.conf`

Add:

```ini
preferStoredTextMimes = text/x-zim-wiki
```

This tells Recoll to use the stored text associated with the Zim Wiki MIME type when searching.

## Important: configuration files are system-dependent

The locations and installation procedures for:

* `mimeconf`
* `mimemap`
* `mimeview`
* MIME type definitions
* `recoll.conf`

can differ between operating systems, Recoll versions, and installation methods.

Therefore this repository deliberately **does not provide complete replacement versions** of `mimeconf`, `mimemap`, or `mimeview`.

Add the required entries manually to the configuration used by your Recoll installation.

Likewise, install `x-zim-wiki.xml` using the MIME registration mechanism appropriate for your system.

## Rebuilding the Recoll index

After changing the MIME configuration and installing `rclzim.py`, the existing Recoll index should be rebuilt so that Zim pages are indexed using the new MIME type and filter.

The exact command or procedure depends on the Recoll installation.

After rebuilding the index, verify that Zim pages are recognized as:

```text
text/x-zim-wiki
```

and that their indexed text no longer contains the unwanted Zim Wiki markup.

## How the integration works

The indexing process is approximately:

```text
Zim .txt page
       │
       ▼
text/x-zim-wiki
       │
       ▼
Recoll
       │
       ▼
rclzim.py
       │
       ▼
clean searchable text
       │
       ▼
Recoll index
```

When a result is opened:

```text
Recoll result
      │
      ▼
text/x-zim-wiki
      │
      ▼
Zim
```

The original Zim file is never modified by `rclzim.py`.

## Searching

When a search is performed, the plugin queries the Recoll index and retrieves the most relevant results.

If the Recoll index contains several Zim notebooks, the plugin filters the results using the full filesystem path and displays only pages belonging to the notebook currently open in Zim.

The plugin therefore does not require a separate Recoll index for every notebook.

## Result preview

Selecting a result displays information about the corresponding Zim page and a text preview.

The preview is generated from the original Zim page rather than from the shortened Recoll search snippet. This makes it possible to display the surrounding text with the original content preserved.

The matching occurrence is highlighted.

When a page contains several matches, the navigation controls allow the user to move between them.

The **Go to match** action opens the corresponding Zim page and moves the cursor to the selected occurrence.

## Notes about Zim page names

The plugin derives the displayed note name from the physical Zim filename.

For example:

```text
My_research_note.txt
```

is displayed as:

```text
My research note
```

The `.txt` extension is not displayed.

The internal Zim heading is obtained separately from the first Zim heading in the page.

## Current status

The plugin is intended as a lightweight bridge between Zim and Recoll:

* Recoll provides indexing and full-text search.
* Zim remains responsible for displaying and editing pages.
* The plugin connects search results with the corresponding Zim pages.

The plugin does not replace Zim's page format or modify Zim's core functionality.
