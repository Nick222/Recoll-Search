from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from datetime import datetime
from gi.repository import Gtk, Pango, PangoCairo
import cairo
import os

# from zim.gui.pageview.find import FindQuery
from zim.plugins import PluginClass
from zim.actions import action
from zim.gui.mainwindow import MainWindowExtension
from zim.newfs import LocalFile

from recoll import recoll


class RecollSearchPlugin(PluginClass):

    plugin_info = {
        'name': 'Recoll Search',
        'description': 'Search with Recoll',
        'author': 'Nick',
    }


class RecollSearchMainWindowExtension(MainWindowExtension):

    PREVIEW_WIDTH = 950
    PREVIEW_PADDING = 32

    def __init__(self, plugin, window):
        super().__init__(plugin, window)

        self.db = None
        self.search_window = None
        self.model = None

        self.current_snippets = []
        self.current_snippet_index = 0

        self.preview_layout = None
        self.preview_page_height = 0
        self.preview_match_y = 0
        self.preview_match_height = 0

    @action('Recoll Search', menuhints='tools')
    def recoll_search(self):

        if self.search_window is not None:
            self.search_window.present()
            return

        self.search_window = Gtk.Window(
            title='Recoll Search'
        )

        self.search_window.set_default_size(
            1120,
            700
        )

        self.search_window.set_position(
            Gtk.WindowPosition.CENTER
        )

        self.search_window.connect(
            'destroy',
            self._on_window_destroy
        )

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        vbox.set_border_width(10)

        self.search_window.add(
            vbox
        )

        # -------------------------------------------------
        # Search controls
        # -------------------------------------------------

        search_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        self.entry = Gtk.Entry()

        self.entry.set_hexpand(
            True
        )

        self.entry.connect(
            'activate',
            self._search
        )

        search_box.pack_start(
            self.entry,
            True,
            True,
            0
        )

        button = Gtk.Button(
            label='Искать'
        )

        button.connect(
            'clicked',
            self._search
        )

        search_box.pack_start(
            button,
            False,
            False,
            0
        )

        vbox.pack_start(
            search_box,
            False,
            False,
            0
        )

        # -------------------------------------------------
        # Results
        # -------------------------------------------------

        self.model = Gtk.ListStore(
            int,      # 0 rank
            str,      # 1 note name / имя заметки
            # str,      # 2 filename
            str,      # 3 url
            str,      # 4 date
            # object,   # 5 tags
            object,   # 6 snippets
            str,      # 7 internal heading / внутренний заголовок
        )

        self.tree = Gtk.TreeView(
            model=self.model
        )

        self.tree.set_headers_visible(
            True
        )

        renderer = Gtk.CellRendererText()

        renderer.set_property(
            'xalign',
            0.5
        )

        column = Gtk.TreeViewColumn(
            '№',
            renderer,
            text=0
        )

        column.set_alignment(
            0.5
        )

        column.set_fixed_width(
            45
        )

        self.tree.append_column(
            column
        )

        renderer = Gtk.CellRendererText()

        renderer.set_property(
            'xalign',
            0.0
        )

        column = Gtk.TreeViewColumn(
            'Результат',
            renderer,
            text=1
        )

        column.set_expand(
            True
        )

        self.tree.append_column(
            column
        )

        selection = self.tree.get_selection()

        selection.set_mode(
            Gtk.SelectionMode.SINGLE
        )

        selection.connect(
            'changed',
            self._selection_changed
        )

        self.tree.set_enable_search(
            False
        )

        result_scroll = Gtk.ScrolledWindow()

        result_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        result_scroll.set_min_content_height(
            120
        )

        result_scroll.add(
            self.tree
        )

        # -------------------------------------------------
        # Results / Preview splitter
        # -------------------------------------------------

        paned = Gtk.Paned(
            orientation=Gtk.Orientation.VERTICAL
        )

        paned.set_position(
            180
        )

        paned.pack1(
            result_scroll,
            True,
            False
        )

        # -------------------------------------------------
        # Preview
        # -------------------------------------------------

        self.preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4
        )

        self.preview_title = Gtk.Label()

        self.preview_title.set_xalign(
            0
        )

        self.preview_title.set_selectable(
            True
        )

        self.preview_title.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_title,
            False,
            False,
            0
        )

        self.preview_heading = Gtk.Label()

        self.preview_heading.set_xalign(
            0
        )

        self.preview_heading.set_selectable(
            True
        )

        self.preview_heading.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_heading,
            False,
            False,
            0
        )

        self.preview_path = Gtk.Label()

        self.preview_path.set_xalign(
            0
        )

        self.preview_path.set_selectable(
            True
        )

        self.preview_path.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_path,
            False,
            False,
            0
        )

        self.preview_created = Gtk.Label()

        self.preview_created.set_xalign(
            0
        )

        self.preview_created.set_selectable(
            True
        )

        self.preview_created.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_created,
            False,
            False,
            0
        )

        self.preview_modified = Gtk.Label()

        self.preview_modified.set_xalign(
            0
        )

        self.preview_modified.set_selectable(
            True
        )

        self.preview_modified.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_modified,
            False,
            False,
            0
        )

        self.preview_size = Gtk.Label()

        self.preview_size.set_xalign(
            0
        )

        self.preview_size.set_selectable(
            True
        )

        self.preview_size.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_size,
            False,
            False,
            0
        )

        # -------------------------------------------------
        # Snippet navigation
        # -------------------------------------------------

        navigation_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        self.previous_button = Gtk.Button(
            label='←'
        )

        self.previous_button.set_tooltip_text(
            'Предыдущее совпадение'
        )

        self.previous_button.connect(
            'clicked',
            self._previous_snippet
        )

        navigation_box.pack_start(
            self.previous_button,
            False,
            False,
            0
        )

        self.preview_counter = Gtk.Label()

        self.preview_counter.set_xalign(
            0.5
        )

        navigation_box.pack_start(
            self.preview_counter,
            False,
            False,
            0
        )

        self.next_button = Gtk.Button(
            label='→'
        )

        self.next_button.set_tooltip_text(
            'Следующее совпадение'
        )

        self.next_button.connect(
            'clicked',
            self._next_snippet
        )

        navigation_box.pack_start(
            self.next_button,
            False,
            False,
            0
        )

        self.go_to_button = Gtk.Button(
            label='Перейти к совпадению'
        )

        self.go_to_button.set_tooltip_text(
            'Открыть заметку на текущем совпадении'
        )

        self.go_to_button.connect(
            'clicked',
            self._go_to_match
        )

        navigation_box.pack_start(
            self.go_to_button,
            False,
            False,
            12
        )

        self.preview_box.pack_start(
            navigation_box,
            False,
            False,
            0
        )

        # -------------------------------------------------
        # Snippet preview — Pango/Cairo
        # -------------------------------------------------

        self.preview_area = Gtk.DrawingArea()

        self.preview_area.set_size_request(
            self.PREVIEW_WIDTH,
            200
        )

        self.preview_area.connect(
            'draw',
            self._on_preview_draw
        )

        self.preview_area.connect(
            'size-allocate',
            self._on_preview_size_allocate
        )

        self.preview_scroll = Gtk.ScrolledWindow()

        self.preview_scroll.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )

        self.preview_scroll.add(
            self.preview_area
        )

        self.preview_box.pack_start(
            self.preview_scroll,
            True,
            True,
            0
        )

        paned.pack2(
            self.preview_box,
            True,
            False
        )

        vbox.pack_start(
            paned,
            True,
            True,
            0
        )

        # -------------------------------------------------
        # Initial preview state
        # -------------------------------------------------

        self._clear_preview()

        # -------------------------------------------------
        # Recoll
        # -------------------------------------------------

        try:
            self.db = recoll.connect()

        except Exception as error:

            self._show_error(
                'Не удалось подключиться к Recoll:\n\n'
                + str(error)
            )

        self.search_window.show_all()

        self.entry.grab_focus()

    # =====================================================
    # Search
    # =====================================================

    def _search(self, widget):

        text = self.entry.get_text().strip()

        if not text:
            return

        if self.db is None:
            return

        self.model.clear()

        self._clear_preview()

        try:

            query = self.db.query()

            query.sortby(
                'relevancyrating',
                ascending=False
            )

            query.execute(text, fetchtext=True)

            docs = query.fetchmany(50)

            for rank, doc in enumerate(docs, start=1):

                url = getattr(
                    doc,
                    'url',
                    ''
                )

                # filename = getattr(
                    # doc,
                    # 'filename',
                    # ''
                # )

                if not url:
                    continue

                parsed_url = urlparse(
                    url
                )

                if parsed_url.scheme != 'file':
                    continue

                result_path = os.path.realpath(
                    unquote(
                        parsed_url.path
                    )
                )

                notebook_path = os.path.realpath(
                    self.window.notebook.folder.path
                )

                if not (
                    result_path == notebook_path
                    or result_path.startswith(
                        notebook_path + os.sep
                    )
                ):
                    continue

                note_name = self._get_result_title(
                    doc
                )

                internal_title = self._get_internal_title(
                    doc
                )

                date = self._get_date(
                    doc
                )

                display_date = self._format_short_date(
                    date
                )

                # tags = self._get_tags(
                    # doc
                # )

                snippets = query.getsnippets(
                    doc,
                    maxoccs=300
                )

                preview_data = self._build_preview_data(
                    getattr(doc, 'text', ''),
                    snippets
                )

                self.model.append([
                    rank,
                    note_name,
                    # filename,
                    url,
                    display_date,
                    # tags,
                    preview_data,
                    internal_title,
                ])

            query.close()

        except Exception as error:

            self._show_error(
                'Ошибка поиска:\n\n'
                + str(error)
            )

    # =====================================================
    # Metadata
    # =====================================================

    def _get_note_name(self, doc):

        url = getattr(
            doc,
            'url',
            ''
        )

        if not url:
            return ''

        parsed = urlparse(url)

        if parsed.scheme != 'file':
            return ''

        filename = unquote(
            parsed.path
        )

        if not filename:
            return ''

        name = filename.rsplit(
            '/',
            1
        )[-1]

        if name.endswith('.txt'):
            name = name[:-4]

        return name.replace(
            '_',
            ' '
        )

    def _get_internal_title(self, doc):

        url = getattr(
            doc,
            'url',
            ''
        )

        if not url:
            return ''

        parsed = urlparse(
            url
        )

        if parsed.scheme != 'file':
            return ''

        filename = unquote(
            parsed.path
        )

        try:

            with open(
                filename,
                'r',
                encoding='utf-8'
            ) as file:

                text = file.read()

        except Exception:

            return ''

        for line in text.splitlines():

            line = line.strip()

            if (
                line.startswith('====== ')
                and line.endswith(' ======')
            ):

                return line[7:-7].strip()

        return ''

    def _get_result_title(self, doc):

        internal_title = self._get_internal_title(
            doc
        )

        note_name = self._get_note_name(
            doc
        )

        # -------------------------------------------------
        # Основной вариант:
        # имя заметки Zim
        # -------------------------------------------------

        if note_name:
            return note_name

        # -------------------------------------------------
        # Если имя заметки получить не удалось:
        # внутренний заголовок
        # -------------------------------------------------

        if internal_title:
            return internal_title

        # -------------------------------------------------
        # Последний fallback:
        # физическое имя файла
        #
        # Это только fallback.
        # Имя файла НЕ является именем заметки.
        # -------------------------------------------------

        filename = getattr(
            doc,
            'filename',
            ''
        )

        if filename.endswith('.txt'):
            filename = filename[:-4]

        return filename.replace(
            '_',
            ' '
        )

    def _get_date(self, doc):

        url = getattr(
            doc,
            'url',
            ''
        )

        if not url:
            return ''

        parsed = urlparse(
            url
        )

        if parsed.scheme != 'file':
            return ''

        filename = unquote(
            parsed.path
        )

        try:
            with open(
                filename,
                'r',
                encoding='utf-8'
            ) as file:

                for line in file:

                    line = line.rstrip(
                        '\r\n'
                    )

                    if line.startswith(
                        'Creation-Date:'
                    ):

                        value = line[
                            len('Creation-Date:'):
                        ].strip()

                        if value == 'Unknown':
                            return ''

                        return value[:10]

        except Exception:
            return ''

        return ''

    # def _get_tags(self, doc):

        # text = getattr(
            # doc,
            # 'text',
            # ''
        # )

        # lines = text.splitlines()

        # title_index = None

        # for index, line in enumerate(lines):

            # line = line.strip()

            # if (
                # line.startswith('====== ')
                # and line.endswith(' ======')
            # ):

                # title_index = index
                # break

        # if title_index is None:
            # return []

        # date_index = title_index + 1

        # if date_index >= len(lines):
            # return []

        # date_line = lines[
            # date_index
        # ].strip()

        # if not date_line.startswith(
            # 'Создано '
        # ):
            # return []

        # blank_before_tags = date_index + 1

        # if (
            # blank_before_tags >= len(lines)
            # or lines[blank_before_tags].strip() != ''
        # ):
            # return []

        # tags_index = date_index + 2

        # if tags_index >= len(lines):
            # return []

        # tags_line = lines[
            # tags_index
        # ].strip()

        # if not tags_line:
            # return []

        # tags = tags_line.split()

        # for tag in tags:

            # if not tag.startswith('@'):
                # return []

        # blank_after_tags = tags_index + 1

        # if (
            # blank_after_tags >= len(lines)
            # or lines[blank_after_tags].strip() != ''
        # ):
            # return []

        # return tags

    # =====================================================
    # Selection
    # =====================================================

    def _selection_changed(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self._clear_preview()
            return

        note_name = model[iterator][1]
        url = model[iterator][2]
        display_date = model[iterator][3]
        preview_data = model[iterator][4]
        internal_title = model[iterator][5]

        parsed = urlparse(
            url
        )

        filename = unquote(
            parsed.path
        )

        self.preview_title.set_text(
            'Имя заметки: ' + note_name
        )

        self.preview_heading.set_text(
            'Внутренний заголовок: ' + (
                internal_title
                if internal_title
                else '—'
            )
        )

        logical_path = ''

        try:

            file = LocalFile(
                filename
            )

            zim_path, _ = (
                self.window.notebook.layout.map_file(
                    file
                )
            )

            if zim_path is not None:

                logical_path = str(
                    zim_path.parent
                )

        except Exception:

            pass

        self.preview_path.set_text(
            'Путь: ' + (
                logical_path
                if logical_path
                else '—'
            )
        )

        self.preview_created.set_text(
            'Создано: ' + (
                display_date
                if display_date
                else '—'
            )
        )

        try:

            stat = os.stat(
                filename
            )

            modified = datetime.fromtimestamp(
                stat.st_mtime
            ).strftime(
                '%d.%m.%Y'
            )

            size = stat.st_size

            if size < 1024:

                size_text = (
                    str(size)
                    + ' Б'
                )

            else:

                size_text = (
                    f'{size / 1024:.1f}'
                    + ' КБ'
                )

            self.preview_modified.set_text(
                'Изменено: ' + modified
            )

            self.preview_size.set_text(
                'Размер: ' + size_text
            )

        except Exception:

            self.preview_modified.set_text(
                'Изменено: —'
            )

            self.preview_size.set_text(
                'Размер: —'
            )

        self.current_snippets = (
            preview_data or []
        )

        self.current_snippet_index = 0

        self._show_current_snippet()

    # =====================================================
    # Preview
    # =====================================================

    def _show_current_snippet(self):

        count = len(
            self.current_snippets
        )

        if count == 0:

            self.preview_counter.set_text(
                ''
            )

            self._clear_preview_rendering()

            self.previous_button.set_sensitive(
                False
            )

            self.next_button.set_sensitive(
                False
            )

            self.go_to_button.set_sensitive(
                False
            )

            return

        self.preview_counter.set_text(
            'Совпадение {} из {}'.format(
                self.current_snippet_index + 1,
                count
            )
        )

        self.previous_button.set_sensitive(
            self.current_snippet_index > 0
        )

        self.next_button.set_sensitive(
            self.current_snippet_index < count - 1
        )

        self.go_to_button.set_sensitive(
            True
        )

        preview = self.current_snippets[
            self.current_snippet_index
        ]

        self._set_context_text(
            preview
        )

    def _build_preview_data(
        self,
        text,
        snippets
    ):

        if not text or not snippets:
            return []

        matches = []

        parser = _MatchCollector()

        for snippet in snippets:

            if len(snippet) < 3:
                continue

            html = snippet[2]

            try:

                parser.feed(
                    html
                )

                parser.close()

            except Exception:
                pass

        for match in parser.matches:

            if not match:
                continue

            start = 0

            while True:

                position = text.lower().find(
                    match.lower(),
                    start
                )

                if position < 0:
                    break

                matches.append(
                    (
                        position,
                        position + len(match)
                    )
                )

                start = position + len(match)

        matches.sort()

        result = []

        for start, end in matches:

            # Если новое совпадение полностью или частично
            # перекрывает уже найденное, оставляем более длинное.

            if result:

                previous = result[-1]

                previous_start = previous['start']
                previous_end = previous['end']

                if start < previous_end:

                    if end <= previous_end:
                        continue

                    if end - start > previous_end - previous_start:
                        result[-1] = {
                            'text': text,
                            'start': start,
                            'end': end,
                        }

                    continue

            result.append({
                'text': text,
                'start': start,
                'end': end,
            })

        return result

    def _set_context_text(
        self,
        preview
    ):

        text = preview['text']
        start = preview['start']
        end = preview['end']

        if not text:
            self._clear_preview_rendering()
            return

        # -------------------------------------------------
        # Temporary Cairo surface for Pango layout
        # -------------------------------------------------

        tmp_surface = cairo.ImageSurface(
            cairo.FORMAT_ARGB32,
            1,
            1
        )

        cr = cairo.Context(
            tmp_surface
        )

        # -------------------------------------------------
        # Pango layout
        # -------------------------------------------------

        layout = PangoCairo.create_layout(
            cr
        )

        font = (
            self.window.pageview.textview
            .get_pango_context()
            .get_font_description()
        )

        layout.set_font_description(
            font
        )

        text_width = (
            self.PREVIEW_WIDTH
            - 2 * self.PREVIEW_PADDING
        )

        layout.set_width(
            text_width * Pango.SCALE
        )

        layout.set_wrap(
            Pango.WrapMode.WORD
        )

        # -------------------------------------------------
        # IMPORTANT:
        #
        # The REAL Recoll document text is used here.
        # No artificial line breaks are inserted.
        # -------------------------------------------------

        layout.set_text(
            text,
            -1
        )

        # -------------------------------------------------
        # Python character indexes -> UTF-8 byte indexes
        # -------------------------------------------------

        start_byte = len(
            text[:start].encode(
                'utf-8'
            )
        )

        end_byte = len(
            text[:end].encode(
                'utf-8'
            )
        )

        # -------------------------------------------------
        # Highlight
        # -------------------------------------------------

        attrs = Pango.AttrList()

        bg = Pango.attr_background_new(
            15163,
            30840,
            55512
        )

        bg.start_index = start_byte
        bg.end_index = end_byte

        attrs.insert(
            bg
        )

        # Pango foreground uses 0..65535.
        fg = Pango.attr_foreground_new(
            65535,
            65535,
            65535
        )

        fg.start_index = start_byte
        fg.end_index = end_byte

        attrs.insert(
            fg
        )

        layout.set_attributes(
            attrs
        )

        # -------------------------------------------------
        # Calculate page height
        # -------------------------------------------------

        _, logical = (
            layout.get_pixel_extents()
        )

        self.preview_page_height = max(
            1,
            logical.height
            + 2 * self.PREVIEW_PADDING
        )

        # -------------------------------------------------
        # Find match position
        # -------------------------------------------------

        pos_start = (
            layout.index_to_pos(
                start_byte
            )
        )

        self.preview_match_y = (
            self.PREVIEW_PADDING
            + pos_start.y / Pango.SCALE
        )

        self.preview_match_height = max(
            1,
            pos_start.height / Pango.SCALE
        )

        # -------------------------------------------------
        # Store layout
        # -------------------------------------------------

        self.preview_layout = layout

        # -------------------------------------------------
        # Tell Gtk the required content height
        # -------------------------------------------------

        self.preview_area.set_size_request(
            self.PREVIEW_WIDTH,
            int(self.preview_page_height)
        )

        self.preview_area.queue_draw()

        self._center_preview_match()

    def _on_preview_size_allocate(
        self,
        widget,
        allocation
    ):

        self._center_preview_match()

    def _center_preview_match(self):

        if self.preview_layout is None:
            return

        adjustment = (
            self.preview_scroll
            .get_vadjustment()
        )

        if adjustment is None:
            return

        page_size = (
            adjustment.get_page_size()
        )

        upper = (
            adjustment.get_upper()
        )

        target = (
            self.preview_match_y
            + self.preview_match_height / 2
            - page_size / 2
        )

        maximum = max(
            0,
            upper - page_size
        )

        value = max(
            0,
            min(
                target,
                maximum
            )
        )

        adjustment.set_value(
            value
        )

    def _on_preview_draw(
        self,
        widget,
        cr
    ):

        allocation = (
            widget.get_allocation()
        )

        width = allocation.width
        height = allocation.height

        # -------------------------------------------------
        # Background follows current GTK theme.
        # -------------------------------------------------

        style_context = (
            widget.get_style_context()
        )

        Gtk.render_background(
            style_context,
            cr,
            0,
            0,
            width,
            height
        )

        if self.preview_layout is None:
            return False

        # -------------------------------------------------
        # Base text color from current GTK theme
        # -------------------------------------------------

        color = style_context.get_color(
            Gtk.StateFlags.NORMAL
        )

        cr.set_source_rgba(
            color.red,
            color.green,
            color.blue,
            color.alpha
        )

        cr.save()

        cr.set_antialias(
            cairo.ANTIALIAS_GRAY
        )

        cr.translate(
            self.PREVIEW_PADDING,
            self.PREVIEW_PADDING
        )

        PangoCairo.update_layout(
            cr,
            self.preview_layout
        )

        PangoCairo.show_layout(
            cr,
            self.preview_layout
        )

        cr.restore()

        return False


    def _clear_preview_rendering(
        self
    ):

        self.preview_layout = None

        self.preview_page_height = 0
        self.preview_match_y = 0
        self.preview_match_height = 0

        self.preview_area.set_size_request(
            self.PREVIEW_WIDTH,
            1
        )

        self.preview_area.queue_draw()

    def _previous_snippet(self, button):

        if not self.current_snippets:
            return

        if self.current_snippet_index <= 0:
            return

        self.current_snippet_index -= 1

        self._show_current_snippet()

    def _next_snippet(self, button):

        if not self.current_snippets:
            return

        if (
            self.current_snippet_index
            >= len(self.current_snippets) - 1
        ):
            return

        self.current_snippet_index += 1

        self._show_current_snippet()

    # # =====================================================
    # # Snippet HTML → Gtk TextBuffer
    # # =====================================================

    # def _set_snippet_text(self, html):

        # buffer = self.preview_text.get_buffer()

        # buffer.set_text('')

        # parser = _SnippetParser(
            # buffer,
            # self.match_tag
        # )

        # try:

            # parser.feed(
                # html
            # )

            # parser.close()

        # except Exception:

            # buffer.set_text(
                # html
            # )

    # =====================================================
    # Date
    # =====================================================

    # def _format_date(self, value):

        # if not value:
            # return ''

        # if 'T' in value:

            # value = value.split(
                # 'T',
                # 1
            # )[0]

        # parts = value.split('-')

        # if len(parts) != 3:
            # return value

        # year, month, day = parts

        # months = {
            # '01': 'января',
            # '02': 'февраля',
            # '03': 'марта',
            # '04': 'апреля',
            # '05': 'мая',
            # '06': 'июня',
            # '07': 'июля',
            # '08': 'августа',
            # '09': 'сентября',
            # '10': 'октября',
            # '11': 'ноября',
            # '12': 'декабря',
        # }

        # month_name = months.get(
            # month
        # )

        # if month_name is None:
            # return value

        # return 'Создано {} {} {}'.format(
            # int(day),
            # month_name,
            # year
        # )

    def _format_short_date(self, value):

        if not value:
            return ''

        try:
            return datetime.strptime(
                value[:10],
                '%Y-%m-%d'
            ).strftime(
                '%d.%m.%Y'
            )

        except Exception:
            return value

    # =====================================================
    # Open current match
    # =====================================================

    def _go_to_match(self, button):

        if not self.current_snippets:
            return

        model, iterator = (
            self.tree.get_selection()
            .get_selected()
        )

        if iterator is None:
            return

        url = model[iterator][2]

        if not url:
            return

        parsed = urlparse(
            url
        )

        if parsed.scheme != 'file':

            self._show_error(
                'Это не локальный файл:\n\n'
                + url
            )

            return

        filename = unquote(
            parsed.path
        )

        try:

            file = LocalFile(
                filename
            )

            path, _ = (
                self.window.notebook.layout.map_file(
                    file
                )
            )

            page = (
                self.window.notebook.get_page(
                    path
                )
            )

            self.window.open_page(
                page
            )

            preview = self.current_snippets[
                self.current_snippet_index
            ]

            match_text = (
                preview['text'][
                    preview['start']:
                    preview['end']
                ]
            )

            if not match_text:
                return

            buffer = (
                self.window.pageview.textview
                .get_buffer()
            )

            search_iter = buffer.get_start_iter()

            match_start = None
            match_end = None

            for index in range(
                self.current_snippet_index + 1
            ):

                item = self.current_snippets[
                    index
                ]

                item_text = item['text'][
                    item['start']:
                    item['end']
                ]

                if not item_text:
                    return

                result = search_iter.forward_search(
                    item_text,
                    Gtk.TextSearchFlags.CASE_INSENSITIVE
                )

                if result is None:
                    return

                match_start, match_end = result

                search_iter = (
                    match_end.copy()
                )

            if (
                match_start is None
                or match_end is None
            ):
                return

            buffer.select_range(
                match_start,
                match_end
            )

            self.window.pageview.textview.scroll_to_iter(
                match_start,
                0.2,
                False,
                0.0,
                0.5
            )

        except Exception as error:

            self._show_error(
                'Не удалось перейти к совпадению:\n\n'
                + filename
                + '\n\n'
                + str(error)
            )

    # =====================================================
    # Preview reset
    # =====================================================

    def _clear_preview(self):

        self.preview_title.set_text('')
        self.preview_heading.set_text('')
        self.preview_path.set_text('')
        self.preview_created.set_text('')
        self.preview_modified.set_text('')
        self.preview_size.set_text('')

        self.preview_counter.set_text('')

        self._clear_preview_rendering()

        self.current_snippets = []

        self.current_snippet_index = 0

        self.previous_button.set_sensitive(
            False
        )

        self.next_button.set_sensitive(
            False
        )

        self.go_to_button.set_sensitive(
            False
        )

    # =====================================================
    # Error
    # =====================================================

    def _show_error(self, message):

        dialog = Gtk.MessageDialog(
            transient_for=self.search_window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )

        dialog.run()
        dialog.destroy()

    # =====================================================
    # Window lifecycle
    # =====================================================

    def _on_window_destroy(self, widget):

        self.search_window = None

        self.current_snippets = []

        self.current_snippet_index = 0

    def do_deactivate(self):

        if self.search_window is not None:

            self.search_window.destroy()

            self.search_window = None

        if self.db is not None:

            try:
                self.db.close()

            except Exception:
                pass

            self.db = None


class _MatchCollector(HTMLParser):

    def __init__(self):

        super().__init__(
            convert_charrefs=True
        )

        self.matches = []
        self.in_match = False

    def handle_starttag(
        self,
        tag,
        attrs
    ):

        if tag.lower() != 'span':
            return

        attributes = dict(
            attrs
        )

        classes = attributes.get(
            'class',
            ''
        ).split()

        if 'rclmatch' in classes:

            self.in_match = True

    def handle_endtag(
        self,
        tag
    ):

        if (
            tag.lower() == 'span'
            and self.in_match
        ):

            self.in_match = False

    def handle_data(
        self,
        data
    ):

        if (
            data
            and self.in_match
        ):

            self.matches.append(
                data
            )


# class _SnippetParser(HTMLParser):

    # def __init__(
        # self,
        # buffer,
        # match_tag
    # ):

        # super().__init__(
            # convert_charrefs=True
        # )

        # self.buffer = buffer
        # self.match_tag = match_tag
        # self.in_match = False

    # def handle_starttag(
        # self,
        # tag,
        # attrs
    # ):

        # if tag.lower() != 'span':
            # return

        # attributes = dict(
            # attrs
        # )

        # classes = attributes.get(
            # 'class',
            # ''
        # ).split()

        # if 'rclmatch' in classes:

            # self.in_match = True

    # def handle_endtag(
        # self,
        # tag
    # ):

        # if (
            # tag.lower() == 'span'
            # and self.in_match
        # ):

            # self.in_match = False

    # def handle_data(
        # self,
        # data
    # ):

        # if not data:
            # return

        # end_iter = (
            # self.buffer.get_end_iter()
        # )

        # if self.in_match:

            # self.buffer.insert_with_tags(
                # end_iter,
                # data,
                # self.match_tag
            # )

        # else:

            # self.buffer.insert(
                # end_iter,
                # data
            # )
