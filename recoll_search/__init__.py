from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

from gi.repository import Gtk, Pango

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

    def __init__(self, plugin, window):
        super().__init__(plugin, window)

        self.db = None
        self.search_window = None
        self.model = None

        self.current_snippets = []
        self.current_snippet_index = 0

    @action('Recoll Search', menuhints='tools')
    def recoll_search(self):

        if self.search_window is not None:
            self.search_window.present()
            return

        self.search_window = Gtk.Window(
            title='Recoll Search'
        )

        self.search_window.set_default_size(
            900,
            600
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
            str,      # 0 title
            str,      # 1 filename
            str,      # 2 url
            str,      # 3 date
            object,   # 4 tags
            object,   # 5 snippets
        )

        self.tree = Gtk.TreeView(
            model=self.model
        )

        self.tree.set_headers_visible(
            False
        )

        self.tree.set_enable_search(
            False
        )

        selection = self.tree.get_selection()

        selection.set_mode(
            Gtk.SelectionMode.SINGLE
        )

        selection.connect(
            'changed',
            self._selection_changed
        )

        renderer = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn(
            'Результат',
            renderer,
            text=0
        )

        self.tree.append_column(
            column
        )

        self.tree.connect(
            'row-activated',
            self._row_activated
        )

        self.tree.connect(
            'key-press-event',
            self._key_press
        )

        result_scroll = Gtk.ScrolledWindow()

        result_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        result_scroll.set_min_content_height(
            180
        )

        result_scroll.add(
            self.tree
        )

        vbox.pack_start(
            result_scroll,
            True,
            True,
            0
        )

        # -------------------------------------------------
        # Preview
        # -------------------------------------------------

        separator = Gtk.Separator(
            orientation=Gtk.Orientation.HORIZONTAL
        )

        vbox.pack_start(
            separator,
            False,
            False,
            4
        )

        self.preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        self.preview_title = Gtk.Label()

        self.preview_title.set_xalign(
            0
        )

        self.preview_title.set_selectable(
            True
        )

        self.preview_title.set_markup(
            ''
        )

        self.preview_title.set_ellipsize(
            Pango.EllipsizeMode.END
        )

        self.preview_box.pack_start(
            self.preview_title,
            False,
            False,
            0
        )

        self.preview_date = Gtk.Label()

        self.preview_date.set_xalign(
            0
        )

        self.preview_box.pack_start(
            self.preview_date,
            False,
            False,
            0
        )

        self.preview_tags = Gtk.Label()

        self.preview_tags.set_xalign(
            0
        )

        self.preview_box.pack_start(
            self.preview_tags,
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

        self.preview_box.pack_start(
            navigation_box,
            False,
            False,
            0
        )

        # -------------------------------------------------
        # Snippet text
        # -------------------------------------------------

        self.preview_text = Gtk.TextView()

        self.preview_text.set_editable(
            False
        )

        self.preview_text.set_cursor_visible(
            False
        )

        self.preview_text.set_wrap_mode(
            Gtk.WrapMode.WORD
        )

        self.preview_text.set_left_margin(
            6
        )

        self.preview_text.set_right_margin(
            6
        )

        self.preview_text.set_top_margin(
            6
        )

        self.preview_text.set_bottom_margin(
            6
        )

        buffer = self.preview_text.get_buffer()

        self.match_tag = buffer.create_tag(
            'recoll-match',
            weight=Pango.Weight.BOLD,
        )

        preview_scroll = Gtk.ScrolledWindow()

        preview_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        preview_scroll.add(
            self.preview_text
        )

        self.preview_box.pack_start(
            preview_scroll,
            True,
            True,
            0
        )

        vbox.pack_start(
            self.preview_box,
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

            query.execute(
                text,
                fetchtext=True
            )

            for doc in query.fetchmany(20):

                url = getattr(
                    doc,
                    'url',
                    ''
                )

                filename = getattr(
                    doc,
                    'filename',
                    ''
                )

                title = self._get_title(
                    doc
                )

                date = self._get_date(
                    doc
                )

                tags = self._get_tags(
                    doc
                )

                snippets = query.getsnippets(
                    doc,
                    maxoccs=300
                )

                self.model.append(
                    [
                        title,
                        filename,
                        url,
                        date,
                        tags,
                        snippets
                    ]
                )

            query.close()

        except Exception as error:

            self._show_error(
                'Ошибка поиска:\n\n'
                + str(error)
            )

    # =====================================================
    # Metadata
    # =====================================================

    def _get_title(self, doc):

        text = getattr(
            doc,
            'text',
            ''
        )

        for line in text.splitlines():

            line = line.strip()

            if (
                line.startswith('====== ')
                and line.endswith(' ======')
            ):
                return line[7:-7].strip()

        filename = getattr(
            doc,
            'filename',
            ''
        )

        return filename

    def _get_date(self, doc):

        text = getattr(
            doc,
            'text',
            ''
        )

        for line in text.splitlines():

            line = line.strip()

            if line.startswith(
                'Creation-Date:'
            ):

                value = line[
                    len('Creation-Date:'):
                ].strip()

                return value

        return ''

    def _get_tags(self, doc):

        text = getattr(
            doc,
            'text',
            ''
        )

        lines = text.splitlines()

        title_index = None

        for index, line in enumerate(lines):

            line = line.strip()

            if (
                line.startswith('====== ')
                and line.endswith(' ======')
            ):

                title_index = index
                break

        if title_index is None:
            return []

        date_index = title_index + 1

        if date_index >= len(lines):
            return []

        date_line = lines[
            date_index
        ].strip()

        if not date_line.startswith(
            'Создано '
        ):
            return []

        blank_before_tags = date_index + 1

        if (
            blank_before_tags >= len(lines)
            or lines[blank_before_tags].strip() != ''
        ):
            return []

        tags_index = date_index + 2

        if tags_index >= len(lines):
            return []

        tags_line = lines[
            tags_index
        ].strip()

        if not tags_line:
            return []

        tags = tags_line.split()

        for tag in tags:

            if not tag.startswith('@'):
                return []

        blank_after_tags = tags_index + 1

        if (
            blank_after_tags >= len(lines)
            or lines[blank_after_tags].strip() != ''
        ):
            return []

        return tags

    # =====================================================
    # Selection
    # =====================================================

    def _selection_changed(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self._clear_preview()
            return

        title = model[iterator][0]
        date = model[iterator][3]
        tags = model[iterator][4]
        snippets = model[iterator][5]

        self.preview_title.set_text(
            title
        )

        self.preview_date.set_text(
            self._format_date(
                date
            )
        )

        if tags:

            self.preview_tags.set_text(
                ' '.join(tags)
            )

        else:

            self.preview_tags.set_text(
                ''
            )

        self.current_snippets = (
            snippets or []
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

            self.preview_text.get_buffer().set_text(
                ''
            )

            self.previous_button.set_sensitive(
                False
            )

            self.next_button.set_sensitive(
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

        snippet = self.current_snippets[
            self.current_snippet_index
        ]

        if len(snippet) >= 3:
            text = snippet[2]
        else:
            text = ''

        self._set_snippet_text(
            text
        )

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

    # =====================================================
    # Snippet HTML → Gtk TextBuffer
    # =====================================================

    def _set_snippet_text(self, html):

        buffer = self.preview_text.get_buffer()

        buffer.set_text('')

        parser = _SnippetParser(
            buffer,
            self.match_tag
        )

        try:

            parser.feed(
                html
            )

            parser.close()

        except Exception:

            buffer.set_text(
                html
            )

    # =====================================================
    # Date
    # =====================================================

    def _format_date(self, value):

        if not value:
            return ''

        if 'T' in value:

            value = value.split(
                'T',
                1
            )[0]

        parts = value.split('-')

        if len(parts) != 3:
            return value

        year, month, day = parts

        months = {
            '01': 'января',
            '02': 'февраля',
            '03': 'марта',
            '04': 'апреля',
            '05': 'мая',
            '06': 'июня',
            '07': 'июля',
            '08': 'августа',
            '09': 'сентября',
            '10': 'октября',
            '11': 'ноября',
            '12': 'декабря',
        }

        month_name = months.get(
            month
        )

        if month_name is None:
            return value

        return 'Создано {} {} {}'.format(
            int(day),
            month_name,
            year
        )

    # =====================================================
    # Open result
    # =====================================================

    def _row_activated(
        self,
        tree,
        path,
        column
    ):

        model = tree.get_model()

        row = model[path]

        url = row[2]

        self._open_result(
            url
        )

    def _key_press(
        self,
        tree,
        event
    ):

        if event.keyval == 65293:  # Enter

            model, iterator = (
                tree.get_selection()
                .get_selected()
            )

            if iterator is not None:

                url = model[iterator][2]

                self._open_result(
                    url
                )

                return True

        return False

    def _open_result(self, url):

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

            path, file_type = (
                self.window.notebook.layout.map_file(
                    file
                )
            )

            page = (
                self.window.notebook.get_page(
                    path
                )
            )

            self.window.pageview.set_page(
                page
            )

        except Exception as error:

            self._show_error(
                'Не удалось открыть страницу:\n\n'
                + filename
                + '\n\n'
                + str(error)
            )

    # =====================================================
    # Preview reset
    # =====================================================

    def _clear_preview(self):

        self.preview_title.set_text(
            ''
        )

        self.preview_date.set_text(
            ''
        )

        self.preview_tags.set_text(
            ''
        )

        self.preview_counter.set_text(
            ''
        )

        self.preview_text.get_buffer().set_text(
            ''
        )

        self.current_snippets = []

        self.current_snippet_index = 0

        self.previous_button.set_sensitive(
            False
        )

        self.next_button.set_sensitive(
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


class _SnippetParser(HTMLParser):

    def __init__(
        self,
        buffer,
        match_tag
    ):

        super().__init__(
            convert_charrefs=True
        )

        self.buffer = buffer
        self.match_tag = match_tag
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

        if not data:
            return

        end_iter = (
            self.buffer.get_end_iter()
        )

        if self.in_match:

            self.buffer.insert_with_tags(
                end_iter,
                data,
                self.match_tag
            )

        else:

            self.buffer.insert(
                end_iter,
                data
            )
