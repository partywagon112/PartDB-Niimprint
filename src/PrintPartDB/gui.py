import wx

import PIL
from PIL import Image

from .tools import *

class MyFrame(wx.Frame):    
    def __init__(self):
        super().__init__(parent=None, title='PartDB Niimbot Printer')
        panel = wx.Panel(self)

        self.text_ctrl = wx.TextCtrl(panel, pos=(5, 5))
        my_btn = wx.Button(panel, label='Search', pos=(5, 55))


        pilImage = print_label_from_url()

        image = wx.EmptyImage(pilImage.size[0],pilImage.height)
        image.setData(Image.convert("RGB").tostring())
        image.setAlphaData(Image.convert("RGBA").tostring()[3::4]

        self.Show()

if __name__ == '__main__':
    app = wx.App()
    frame = MyFrame()
    app.MainLoop()