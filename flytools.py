#!/usr/bin/env python3

import os
import json

import pcbnew
import wx

class FlyToolsPage:
    def __init__(self, name: str):
        self.name = name

    @classmethod
    def from_config(cls, config: dict):
        return cls(config['name'])

    def to_config(self) -> dict:
        return {
            'name': self.name
        }

class FlyTools:

    def default_config(self) -> dict:
        return json.load(open(os.path.join(self.install_dir, "flytools_defaults.json")))

    def save_config(self) -> None:

        config = self.default_config()

        # save all flytime pages
        for page in self.pages:
            config['pages'].append(page.to_config())

        json.dump(config, open(self.config_file, 'w'), indent=4)

    def load_config(self) -> None:
        if os.path.exists(self.config_file):
            config = json.load(open(self.config_file))
        else:
            config = self.default_config()

        # load all flytime pages
        self.pages = []
        for page in config['pages']:
            self.pages.append(FlyToolsPage.from_config(page))

    def __init__(self, pcb: pcbnew.BOARD, config_file: str) -> None:
        self.install_dir = os.path.dirname(__file__)
        self.pcb = pcb
        self.config_file = config_file
        self.load_config()

    def get_pages(self) -> list:
        return self.pages

    def add_page(self, name: str) -> None:
        if name not in [page.name for page in self.pages]:
            self.pages.append(FlyToolsPage(name))
            self.save_config()

    def remove_page(self, name: str) -> None:
        if name in [page.name for page in self.pages]:
            self.pages = [page for page in self.pages if page.name != name]
            self.save_config()

class SetupPanel(wx.Panel):

    def set_add_page_cb(self, cb) -> None:
        self.remote_add_page_cb = cb

    def set_remove_page_cb(self, cb) -> None:
        self.remote_remove_page_cb = cb

    def add_page_cb(self, event) -> None:
        if self.remote_add_page_cb is None:
            raise Exception("add_page_cb not registered")
        self.remote_add_page_cb(event)

    def remove_page_cb(self, event) -> None:
        if self.remote_remove_page_cb is None:
            raise Exception("remove_page_cb not registered")
        self.remote_remove_page_cb(event)

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)
        self.parent = parent
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.remote_add_page_cb = None
        self.remote_remove_page_cb = None

        # page name entry box
        self.pagesizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Page Setup")
        self.page_name_box = wx.TextCtrl(self, size=(100, -1))
        self.pagesizer.Add(self.page_name_box, 0, wx.ALL | wx.ALIGN_CENTER | wx.EXPAND, 5)
        self.add_page_button = wx.Button(self, label="Add Page")
        self.add_page_button.Bind(wx.EVT_BUTTON, self.add_page_cb)
        self.remove_page_button = wx.Button(self, label="Remove Page")
        self.remove_page_button.Bind(wx.EVT_BUTTON, self.remove_page_cb)
        self.pagesizer.Add(self.add_page_button, 0, wx.ALL, 5)
        self.pagesizer.Add(self.remove_page_button, 0, wx.ALL, 5)

        self.sizer.Add(self.pagesizer, 0, wx.ALL, 5)

        self.SetSizer(self.sizer)

class FlyPage(wx.Panel):
    def __init__(self, parent, flytools_page: FlyToolsPage):
        super().__init__(parent)

        self.parent = parent
        self.flytools_page = flytools_page

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sizer.Add(wx.StaticText(self, label="Fly"), 0, wx.ALL, 5)

        self.SetSizer(self.sizer)

class DmPage(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.sizer.Add(wx.StaticText(self, label="Delay Matching"), 0, wx.ALL, 5)

        # self.SetSizer(self.sizer)

class FlyToolsFrame(wx.Frame):

    def add_page_cb(self, event) -> None:
        self.flytools.add_page(self.setup_panel.page_name_box.GetValue())
        self.add_pages(self.nb)

    def remove_page_cb(self, event) -> None:
        self.flytools.remove_page(self.setup_panel.page_name_box.GetValue())
        self.add_pages(self.nb)

    def add_pages(self, nb: wx.Notebook) -> None:

        self.pagepanels = []
        while self.nb.GetPageCount() > 0:
            self.nb.RemovePage(0)

        self.nb.AddPage(self.setup_panel, "Setup")
        self.nb.AddPage(self.dm_panel, "Delay Matching")

        for page in self.flytools.get_pages():
            self.pagepanels.append(FlyPage(nb, page))
            nb.AddPage(self.pagepanels[-1], page.name)

    def __init__(self, pcb: pcbnew.BOARD, parent=None, style=wx.DEFAULT_FRAME_STYLE):
        super().__init__(parent=parent, style=style, title='flytools')

        self.install_dir = os.path.dirname(__file__)
        self.SetIcon(wx.Icon(os.path.join(self.install_dir, 'flytools.png')))

        config_file = os.path.join(os.path.dirname(pcb.GetFileName()), 'flytools.json')
        self.flytools = FlyTools(pcb, config_file)

        self.nb = wx.Notebook(self)

        self.setup_panel = SetupPanel(self.nb)
        self.setup_panel.set_add_page_cb(self.add_page_cb)
        self.setup_panel.set_remove_page_cb(self.remove_page_cb)

        self.dm_panel = DmPage(self.nb)

        self.add_pages(self.nb)

if __name__ == '__main__':
    app = wx.App()
    dlg = wx.FileDialog(None, "select a kicad pcb", style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST, wildcard="*.kicad_pcb")
    if dlg.ShowModal() != wx.ID_OK:
        exit(1)
    pcb = pcbnew.LoadBoard(dlg.GetPath())
    frame = FlyToolsFrame(pcb)
    frame.Show()
    app.MainLoop()
