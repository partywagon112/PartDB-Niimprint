import wx
import json
import threading
import requests
from appdata import AppDataPaths
import serial.tools.list_ports
from PIL import Image

from PyPartDB import PartDB
from niimprint import PrinterClient, BluetoothTransport, SerialTransport

from PrintPartDB.tools import print_label_from_url, PIL_from_url


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
        self.partdb_connection = SetupPanel.PartDBAPISetup(self)

        self.load_app_path()
        self.save_button = wx.Button(self, label="Save")
        self.save_button.Bind(wx.EVT_BUTTON, self.dump_config)

        # Add widgets to sizer
        sizer.Add(self.connection_rbox, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.bluetooth_connection, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.serial_connection, 0, wx.ALL | wx.EXPAND, 10)
        sizer.Add(self.partdb_connection, 0, wx.ALL | wx.EXPAND, 10)
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
        except Exception as e:
            wx.MessageBox(
                f"Failed to load config:\n{e}\n\nUsing defaults.",
                "Config Error",
                wx.OK | wx.ICON_WARNING
            )
            self.dump_config()

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
        return PartDB(self.partdb_connection.config["url"], self.partdb_connection.config["key"])

    def dump_config(self, e=None):
        """
        Builds up a config
        """
        config = dict()
        config.update(self.connection)
        config['bluetooth'] = self.bluetooth_connection.config
        config['serial'] = self.serial_connection.config
        config['partdb'] = self.partdb_connection.config
        with open(self.app_path.config_path, "w") as file:
            json.dump(config, file, indent=4)
        return config

    def update_config(self, config: dict):
        self.connection = config["connection"]
        self.bluetooth_connection.config = config["bluetooth"]
        self.serial_connection.config = config["serial"]
        self.partdb_connection.config = config['partdb']
        self.test_connections()
        self.Layout()
    
    def test_connections(self):
        if self.connection_rbox.GetStringSelection() == "Bluetooth":
            self.bluetooth_connection.on_connect(None)
        else:
            self.serial_connection.on_connect(None)
        self.partdb_connection.on_test_connection(None)


    class PrinterSetupBase(wx.Panel):
        """
        Base Class to share some common functions.
        """

        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            self.connect_button = wx.Button(self, label="Connect")
            self.connect_button.Bind(wx.EVT_BUTTON, self.on_connect)
            self.connection_status = wx.StaticText(self, label="Unconnected")

        def on_connect(self, event):
            self.connect_button.Disable()
            self.connection_status.SetLabel("Connecting...")

            thread = threading.Thread(target=self._connect_worker, daemon=True)
            thread.start()

        def _connect_worker(self):
            try:
                printer = self.printer
                hb = printer.heartbeat()

                battery = (hb.get("powerlevel", 0) / 10) * 100

                wx.CallAfter(
                    self.connection_status.SetLabel,
                    f"Connected\t\t\tBattery = {battery:.0f}%"
                )

            except OSError as e:
                msg = "Device not reachable"
            except TimeoutError:
                msg = "Connection timed out"
            except ValueError as e:
                msg = f"Invalid config: {e}"
            except Exception as e:
                msg = f"Error: {str(e)}"

            else:
                return

            wx.CallAfter(
                self.connection_status.SetLabel,
                f"Unconnected: {msg}"
            )

            wx.CallAfter(self.connect_button.Enable)


    class BluetoothSetup(PrinterSetupBase):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            box = wx.StaticBox(self, label="Bluetooth Settings")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            self.mac_textbox = wx.TextCtrl(self, value="")


            sizer.Add(wx.StaticText(self, label="MAC Address:"), 0, wx.ALL, 5)
            sizer.Add(self.mac_textbox, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connect_button, 0, wx.ALL | wx.EXPAND, 5)
            sizer.Add(self.connection_status, 0, wx.ALL | wx.EXPAND, 5)
            self.SetSizer(sizer)

            
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


    class SerialSetup(PrinterSetupBase):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            box = wx.StaticBox(self, label="Serial Settings")
            sizer = wx.StaticBoxSizer(box, wx.VERTICAL)

            self.port_list = wx.ComboBox(
                self,
                value=self.__get_serial()[0],
                choices=self.__get_serial(),
                style=wx.CB_READONLY  # optional but recommended
            )

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
                response = requests.get(url, timeout=5)           
            except Exception as exception:
                return False # Lets just assume it's bad i guess
            
            if response.status_code != 200:
                return False

            return True
                
        def on_test_connection(self, event):
            self.test_button.Disable()
            self.connection_status.SetLabel("Testing...")

            threading.Thread(target=self._test_worker, daemon=True).start()


        def _test_worker(self):
            try:
                if not self.__url_exists(self.config["url"]):
                    raise ConnectionError("API URL not reachable")

                info = self.api.getInfo()

                if not isinstance(info, dict):
                    raise ValueError(info)

                msg = f"Connected: {info.get('title', '?')} Version: {info.get('version', '?')}"

                wx.CallAfter(self.connection_status.SetLabel, msg)

            except requests.exceptions.RequestException:
                wx.CallAfter(self.connection_status.SetLabel, "Network error")
            except Exception as e:
                wx.CallAfter(self.connection_status.SetLabel, f"Unconnected\t\t\t{e}")

            finally:
                wx.CallAfter(self.test_button.Enable)

class PrintPanel(wx.Panel):
    def __init__(self, parent, setup: SetupPanel, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)

        self.setup = setup
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.url_textbox = wx.TextCtrl(self, value="")

        self.preview_button = wx.Button(self, label="Preview")
        self.preview_button.Bind(wx.EVT_BUTTON, self.preview)

        self.print_button = wx.Button(self, label="Print")
        self.print_button.Bind(wx.EVT_BUTTON, self.print)

        # Placeholder for preview image
        self.preview_image = wx.StaticBitmap(self)

        self.sizer.Add(self.url_textbox, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.preview_button, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.print_button, 0, wx.ALL | wx.EXPAND, 5)
        self.sizer.Add(self.preview_image, 1, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(self.sizer)

    @staticmethod
    def __convert_pil_to_wxStaticBitmap(pil_image):
        width, height = pil_image.size

        wx_image = wx.Image(width, height)
        wx_image.SetData(pil_image.convert("RGB").tobytes())

        return wx_image.ConvertToBitmap()

    @property
    def uri(self):
        return self.url_textbox.GetValue().strip()

    def preview(self, event):
        try:
            pil_img = PIL_from_url(self.setup.api, self.uri, profileId=2)
            bitmap = self.__convert_pil_to_wxStaticBitmap(pil_img)

            self.preview_image.SetBitmap(bitmap)
            self.Layout()

        except Exception as e:
            wx.MessageBox(f"Preview failed:\n{e}", "Error", wx.OK | wx.ICON_ERROR)

    def print(self, event):
        print_label_from_url(
            self.setup.api,
            self.setup.printer,
            self.uri,
            15, 30, 132, 2, True
        )


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title='PartDB Niimbot Printer')

        # Setup each tab of the interface
        nb = wx.Notebook(self)
        self.setup_tab = SetupPanel(nb)
        self.print_tab = PrintPanel(nb, self.setup_tab)
        nb.AddPage(self.setup_tab, "Setup")
        nb.AddPage(self.print_tab, "Print")

        sizer = wx.BoxSizer()
        sizer.Add(nb, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.Fit()

        w, h = self.GetSize()

        # Force a more reasonable width
        min_width = 500
        self.SetSize((max(w, min_width), h))

        self.SetSizeHints(self.GetSize())

        self.Show()

if __name__ == '__main__':
    app = wx.App()
    frame = MainFrame()
    app.MainLoop()
