from urllib.parse import unquote, urlparse

from gi.repository import Gtk

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

        self.search_window.set_position(Gtk.WindowPosition.CENTER)

        self.search_window.connect(
            'destroy',
            self._on_window_destroy
        )

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )

        box.set_border_width(10)

        search_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)

        self.entry.connect(
            'activate',
            self._search
        )

        button = Gtk.Button(
            label='Искать'
        )

        button.connect(
            'clicked',
            self._search
        )

        search_box.pack_start(
            self.entry,
            True,
            True,
            0
        )

        search_box.pack_start(
            button,
            False,
            False,
            0
        )

        box.pack_start(
            search_box,
            False,
            False,
            0
        )

        # Результаты
        self.model = Gtk.ListStore(
            str,  # title
            str,  # filename
            str,  # url
            str,  # date
            object,  # tags
            object,  # snippets
        )

        self.tree = Gtk.TreeView(
            model=self.model
        )

        self.tree.set_headers_visible(False)

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
            'Result',
            renderer,
            text=0
        )

        column.set_expand(True)

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

        scroll = Gtk.ScrolledWindow()

        scroll.set_hexpand(True)
        scroll.set_vexpand(True)

        scroll.add(
            self.tree
        )

        box.pack_start(
            scroll,
            True,
            True,
            0
        )

        self.search_window.add(
            box
        )

        try:
            self.db = recoll.connect()
        except Exception as error:
            self._show_error(
                'Не удалось подключиться к Recoll:\n\n'
                + str(error)
            )

        self.search_window.show_all()

    def _search(self, widget):

        text = self.entry.get_text().strip()

        if not text:
            return

        if self.db is None:
            return

        self.model.clear()

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
                    doc
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

            if line.startswith('Creation-Date:'):

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

        date_line = lines[date_index].strip()

        if not date_line:
            return []

        tags_index = date_index + 2

        if tags_index >= len(lines):
            return []

        if lines[tags_index].strip() == '':
            return []

        tag_line = lines[tags_index].strip()

        if not tag_line.startswith('@'):
            return []

        tags = [
            tag
            for tag in tag_line.split()
            if tag.startswith('@')
        ]

        if not tags:
            return []

        return tags

    def _selection_changed(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            return

        snippets = model[iterator][5]

        print('\nSELECTED SNIPPETS:')

        for snippet in snippets:
            print(
                repr(snippet)
            )

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

    def _key_press(self, tree, event):

        if event.keyval == 65293:  # Enter

            model, iterator = tree.get_selection().get_selected()

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

        parsed = urlparse(url)

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
            file = LocalFile(filename)

            path, file_type = self.window.notebook.layout.map_file(
                file
            )

            page = self.window.notebook.get_page(
                path
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

    def _show_error(self, message):

        dialog = Gtk.MessageDialog(
            transient_for=self.search_window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )

        dialog.set_title(
            'Recoll Search'
        )

        dialog.run()
        dialog.destroy()

    def _on_window_destroy(self, window):

        self.search_window = None

    def do_deactivate(self):

        if self.db is not None:

            try:
                self.db.close()
            except Exception:
                pass

            self.db = None

        if self.search_window is not None:

            self.search_window.destroy()
            self.search_window = None

        super().do_deactivate()
