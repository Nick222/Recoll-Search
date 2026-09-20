from gi.repository import Gtk

from zim.plugins import PluginClass
from zim.actions import action
from zim.gui.mainwindow import MainWindowExtension

from recoll import recoll


class RecollSearchPlugin(PluginClass):
    plugin_info = {
        'name': 'Recoll Search',
        'description': 'Search with Recoll',
        'author': 'Nick',
    }


class RecollSearchMainWindowExtension(MainWindowExtension):

    def __init__(self, plugin, window):
        super().__init__(
            plugin,
            window
        )

        self.db = None
        self.window = None

    @action('Recoll Search', menuhints='tools')
    def recoll_search(self):

        if self.window is not None:
            self.window.present()
            return

        self.window = Gtk.Window(
            title='Recoll Search'
        )

        self.window.set_default_size(
            800,
            600
        )

        self.window.connect(
            'destroy',
            self._on_destroy
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

        self.textview = Gtk.TextView()

        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(
            Gtk.WrapMode.WORD_CHAR
        )

        scroll = Gtk.ScrolledWindow()

        scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC,
            Gtk.PolicyType.AUTOMATIC
        )

        scroll.set_hexpand(True)
        scroll.set_vexpand(True)

        scroll.add(
            self.textview
        )

        box.pack_start(
            scroll,
            True,
            True,
            0
        )

        self.window.add(
            box
        )

        try:
            self.db = recoll.connect()
        except Exception as error:
            self._show_error(
                'Не удалось подключиться к Recoll:\n\n'
                + str(error)
            )

        self.window.show_all()

    def _search(self, widget):

        text = self.entry.get_text().strip()

        if not text:
            return

        if self.db is None:
            return

        buffer = self.textview.get_buffer()

        buffer.set_text(
            'Поиск...\n'
        )

        try:
            query = self.db.query()

            nres = query.execute(
                text,
                fetchtext=True
            )

            output = []

            output.append(
                'Запрос: %s' % text
            )

            output.append(
                'Найдено: %d' % nres
            )

            output.append(
                '=' * 70
            )

            for doc in query.fetchmany(10):

                title = getattr(
                    doc,
                    'title',
                    ''
                )

                filename = getattr(
                    doc,
                    'filename',
                    ''
                )

                url = getattr(
                    doc,
                    'url',
                    ''
                )

                mtype = getattr(
                    doc,
                    'mtype',
                    ''
                )

                output.append('')
                output.append(
                    'TITLE: %s' % title
                )
                output.append(
                    'FILE:  %s' % filename
                )
                output.append(
                    'URL:   %s' % url
                )
                output.append(
                    'TYPE:  %s' % mtype
                )

                try:
                    snippets = query.getsnippets(
                        doc,
                        maxoccs=3,
                        ctxwords=8
                    )
                except Exception:
                    snippets = []

                if snippets:

                    output.append('')
                    output.append(
                        'SNIPPETS:'
                    )

                    for page, term, snippet in snippets:

                        output.append(
                            '[%s] %s'
                            % (
                                term,
                                snippet
                            )
                        )

                output.append('')
                output.append(
                    '-' * 70
                )

            buffer.set_text(
                '\n'.join(output)
            )

            query.close()

        except Exception as error:

            buffer.set_text(
                'Ошибка поиска:\n\n'
                + str(error)
            )

    def _show_error(self, message):

        dialog = Gtk.MessageDialog(
            transient_for=self.window,
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

    def _on_destroy(self, window):

        self.window = None

    def do_deactivate(self):

        if self.db is not None:

            try:
                self.db.close()
            except Exception:
                pass

            self.db = None

        if self.window is not None:

            self.window.destroy()

            self.window = None

        super().do_deactivate()
