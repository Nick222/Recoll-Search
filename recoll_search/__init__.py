from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
from datetime import datetime
from gi.repository import Gtk, Pango

from zim.gui.pageview.find import FindQuery
from zim.plugins import PluginClass
from zim.actions import action
from zim.gui.mainwindow import MainWindowExtension
from zim.newfs import LocalFile

from recoll import recoll

import xapian

print(
    'XAPIAN VERSION:',
    xapian.version_string()
)

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
            int,      # 0 rank
            str,      # 1 title
            str,      # 2 filename
            str,      # 3 url
            str,      # 4 date
            object,   # 5 tags
            object,   # 6 snippets
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

        self.tree.connect(
            'row-activated',
            self._row_activated
        )

        self.tree.connect(
            'key-press-event',
            self._key_press
        )

        self.tree.set_enable_search(
            False
        )

        result_scroll = Gtk.ScrolledWindow()

        result_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        result_scroll = Gtk.ScrolledWindow()

        result_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        result_scroll.set_min_content_height(
            120
        )

        result_scroll.set_max_content_height(
            160
        )

        result_scroll.set_vexpand(
            False
        )

        result_scroll.add(
            self.tree
        )

        vbox.pack_start(
            result_scroll,
            False,
            False,
            0
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

        self.preview_filename = Gtk.Label()

        self.preview_filename.set_xalign(
            0
        )

        self.preview_filename.set_selectable(
            True
        )

        self.preview_filename.set_line_wrap(
            True
        )

        self.preview_box.pack_start(
            self.preview_filename,
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

        zim_font = (
            self.window.pageview.textview
            .get_pango_context()
            .get_font_description()
        )

        self.preview_text.modify_font(
            zim_font
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

            print(
                'CONNECTION TYPE:',
                type(query.connection)
            )

            print(
                'CONNECTION DIR:',
                [
                    name
                    for name in dir(query.connection)
                    if not name.startswith('_')
                ]
            )

            cursor = self.db.cursor()

            print(
                'CURSOR TYPE:',
                type(cursor)
            )

            print(
                'CURSOR DIR:',
                [
                    name
                    for name in dir(cursor)
                    if not name.startswith('_')
                ]
            )

            print(
                'DB DIR:',
                [
                    name
                    for name in dir(self.db)
                    if not name.startswith('_')
                ]
            )

            print(
                'XAPIAN VERSION:',
                xapian.version_string()
            )

            print(
                'RECOLL MODULE:',
                recoll.__file__
            )

            print(
                'XAPIAN MODULE:',
                xapian.__file__
            )

            query.sortby(
                'relevancyrating',
                ascending=False
            )

            query.execute(text, fetchtext=True)

            docs = query.fetchmany(50)

            if docs:
                print(
                    'DOC KEYS:',
                    docs[0].keys()
                )

                print(
                    'DOC ITEMS:',
                    docs[0].items()
                )

            print(
                'DOC TEXT TEST:',
                repr(getattr(docs[0], 'text', '')) if docs else '<NO RESULTS>'
            )
            print(
                'GROUPS:',
                query.getgroups()
            )

            for rank, doc in enumerate(docs, start=1):

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

                display_date = self._format_short_date(
                    date
                )

                tags = self._get_tags(
                    doc
                )

                snippets = query.getsnippets(
                    doc,
                    maxoccs=300
                )

                self.model.append([
                    rank,
                    title,
                    filename,
                    url,
                    display_date,
                    tags,
                    snippets,
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

    def _get_title(self, doc):

        text = getattr(doc, 'text', '')

        for line in text.splitlines():

            line = line.strip()

            if line:
                return line

        return getattr(doc, 'filename', '')

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

        title = model[iterator][1]
        filename = model[iterator][2]
        url = model[iterator][3]
        snippets = model[iterator][6]

        parsed = urlparse(
            url
        )

        path = unquote(
            parsed.path
        )

        self.preview_title.set_text(
            'Заголовок: ' + title
        )

        self.preview_filename.set_text(
            'Имя файла: ' + filename
        )

        self.preview_path.set_text(
            'Путь: ' + path
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

        self.window.pageview.find_bar.find_previous()

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

        self.window.pageview.find_bar.find_next()

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

        url = row[3]

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

                url = model[iterator][3]

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

            self.window.pageview.find_bar.find(
                FindQuery(self.entry.get_text().strip())
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

        self.preview_filename.set_text(
            ''
        )

        self.preview_path.set_text(
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
