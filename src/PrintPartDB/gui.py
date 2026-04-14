import wx
import json
import threading
import requests
from appdata import AppDataPaths

import PIL
from PIL import Image

import serial.tools.list_ports

from PyPartDB import PartDB
from niimprint.printer import InfoEnum
from niimprint import PrinterClient, BluetoothTransport, SerialTransport

from tools import *


class PartDBConfigureFrame(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)


class SetupPanel(wx.Panel):
    PRINTER_CONNECTION_TYPES = ['Bluetooth', 'Serial']

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Radio box for selecting connection type
        self.connection_rbox = wx.RadioBox(
            self,
            label='Connection Type',
            choices=SetupPanel.PRINTER_CONNECTION_TYPES,
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS
        )
        self.connection_rbox.Bind(wx.EVT_RADIOBOX, self.set_connection)

        # Setup panels for each connection type
        self.bluetooth_connection = SetupPanel.BluetoothSetup(self)
        self.serial_connection = SetupPanel.SerialSetup(self)
        self.partdb_conn = SetupPanel.PartDBAPISetup(self)

        self.load_app_path()
        self.save_button = wx.Button(self, label="Save")
        self.save_button.Bind(wx.EVT_BUTTON, self.save_config)

        # Add widgets to sizer
        sizer.Add(self.connection_rbox, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.bluetooth_connection, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.serial_connection, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.partdb_conn, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.save_button, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(sizer)

        # Show only the first option initially
        self.set_connection(None)

    def load_app_path(self):
        self.app_path = AppDataPaths("printpartdb", default_config_ext="json")
        self.app_path.setup()

        try:
            with open(self.app_path.config_path, "r") as file:
                self.update_config(json.load(file))
        except Exception as exception:
            print("Ignored config")
            print(exception)
            # Assume any error means you get to just make a new config :(
            self.save_config()

    def set_connection(self, event):
        selection = self.connection_rbox.GetStringSelection()
        self.bluetooth_connection.Show(selection == "Bluetooth")
        self.serial_connection.Show(selection == "Serial")
        self.Layout()

    @property
    def connection(self) -> dict:
        return {"connection": self.connection_rbox.GetStringSelection()}

    @connection.setter
    def connection(self, connection: str = "Serial"):
        if connection not in ["Serial", "Bluetooth"]:
            raise KeyError("Only Serial or Bluetooth allowed as connection key")
        self.connection_rbox.SetStringSelection(connection)

    @property
    def printer(self) -> PrinterClient:
        if self.connection == "Serial":
            return self.serial_connection.printer
        else:
            return self.bluetooth_connection.printer

    @property 
    def api(self) -> PartDB:
        return PartDB(self.partdb_conn.config["url"], self.partdb_conn.config["key"])

    def save_config(self, e=None):
        """
        Builds up a config
        """
        config = dict()
        config.update(self.connection)
        config['bluetooth'] = self.bluetooth_connection.config
        config['serial'] = self.serial_connection.config
        config['partdb'] = self.partdb_conn.config
        with open(self.app_path.config_path, "w") as file:
            json.dump(config, file, indent=4)
        return config

    def update_config(self, config: dict):
        self.connection = config["connection"]
        self.bluetooth_connection.config = config["bluetooth"]
        self.serial_connection.config = config["serial"]
        self.partdb_conn.config = config['partdb']
        self.Layout()

    class BluetoothSetup(wx.Panel):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            box = wx.StaticBox(self, label="Bluetooth Settings")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            self.mac_textbox = wx.TextCtrl(self, value="")
            self.connect_button = wx.Button(self, label="Connect")
            self.connect_button.Bind(wx.EVT_BUTTON, self.on_connect)
            self.connection_status = wx.StaticText(self, label="Unconnected")

            sizer.Add(wx.StaticText(self, label="MAC Address:"), 0, wx.ALL, 5)
            sizer.Add(self.mac_textbox, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connect_button, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connection_status, 0, wx.ALL | wx.EXPAND, 5)
            self.SetSizer(sizer)

        def on_connect(self, event):
            """
            Quickly test connection, will have to start a thread to stop this from blocking.
            """
            try:
                printer = self.printer
                hb = printer.heartbeat()
                self.connection_status.SetLabel(f"Connected\t\t\tBattery = {(hb["powerlevel"]/10)*100}%")

            except OSError as exception:
                # not connected
                self.connection_status.SetLabel("Unconnected")
        
        @property
        def printer(self):
            return PrinterClient(BluetoothTransport(self.config['mac']))

        @property
        def config(self) -> dict:
            return {
                "mac": self.mac_textbox.GetValue().strip()
            }

        @config.setter
        def config(self, opts):
            # TODO type check
            self.mac_textbox.SetValue(opts["mac"])
            self.Layout()

    class SerialSetup(wx.Panel):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            box = wx.StaticBox(self, label="Serial Settings")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            self.port_list = wx.ComboBox(self, value=self.__get_serial()[0], choices=self.__get_serial())
            self.connect_button = wx.Button(self, label="Connect")
            self.connect_button.Bind(wx.EVT_BUTTON, self.on_connect)
            self.connection_status = wx.StaticText(self, label="Unconnected")

            sizer.Add(wx.StaticText(self, label="Serial Port:"), 0, wx.ALL, 5)
            sizer.Add(self.port_list, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connect_button, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connection_status, 0, wx.ALL | wx.EXPAND, 5)
            self.SetSizer(sizer)
        
        def __get_serial(self) -> list[str]:
            ports = list(serial.tools.list_ports.comports())
            ports = [port for port, desc, hwid in sorted(ports)]
            return ports if len(ports) > 0 else [""]

        @property
        def config(self) -> dict:
            return {
                "port": self.port_list.GetValue().strip()
            }
        
        @config.setter
        def config(self, opts: dict):
            # TODO type check
            self.port_list.SetValue(opts["port"])
            self.Layout()

        def on_connect(self, event):
            """
            Quickly test connection, will have to start a thread to stop this from blocking.
            """
            try:
                printer = self.printer
                hb = printer.heartbeat()
                self.connection_status.SetLabel(f"Connected\t\t\tBattery = {(hb["powerlevel"]/10)*100}%")

            except OSError as exception:
                # not connected
                self.connection_status.SetLabel("Unconnected")
        
        @property
        def printer(self):
            return PrinterClient(SerialTransport(self.config['port']))


    class PartDBAPISetup(wx.Panel):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            box = wx.StaticBox(self, label="PartDB API Settings")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            self.url_box = wx.TextCtrl(self, value="")
            self.key_box = wx.TextCtrl(self, value="")

            self.test_button = wx.Button(self, label="Test Connection")
            self.test_button.Bind(wx.EVT_BUTTON, self.on_test_connection)
            self.connection_status = wx.StaticText(self, label="Unconnected")

            sizer.Add(wx.StaticText(self, label="API URL:"), 0, wx.ALL, 5)
            sizer.Add(self.url_box, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(wx.StaticText(self, label="API Key:"), 0, wx.ALL, 5)
            sizer.Add(self.key_box, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.test_button, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connection_status, 0, wx.ALL | wx.EXPAND, 5)
            self.SetSizer(sizer)
        
        @property
        def api(self) -> PartDB:
            return PartDB(self.config["url"], self.config["key"])

        @property
        def config(self) -> dict:
            return {
                "url": self.url_box.GetValue().strip(),
                "key": self.key_box.GetValue().strip()
            }

        @config.setter
        def config(self, opts):
            # TODO type check
            self.url_box.SetValue(opts["url"])
            self.key_box.SetValue(opts["key"])
            self.Layout()

        @staticmethod
        def __url_exists(url):
            # TODO bit of a mess
            try:
                response = requests.get(url)           
            except Exception as exception:
                return False # Lets just assume it's bad i guess
            
            if response.status_code != 200:
                return False

            return True
                
        def on_test_connection(self, event) -> None:
            if SetupPanel.PartDBAPISetup.__url_exists(self.config["url"]) == False:
                self.connection_status.SetLabel(f"Unconnected")
                return

            info = self.api.getInfo()
            if type(info) != dict:
                self.connection_status.SetLabel(f"Unconnected\t\t\tERROR {info}")
                return

            self.connection_status.SetLabel(f"Connected: {info["title"]} Version: {info["version"]}")

                

class PrintFromURLTab(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='PartDB Niimbot Printer')
        self.SetSize(400, 600)

        # Setup each tab of the interface
        nb = wx.Notebook(self)
        self.connections_tab = SetupPanel(nb)
        self.print_from_url = PrintFromURLTab(nb)
        nb.AddPage(self.connections_tab, "Setup")
        nb.AddPage(self.print_from_url, "Print from URL")

        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.Show()

if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    app.MainLoop()
