from bluetoothctl import BluetoothCtl, BluetoothDevice
import dbus
import subprocess
from typing import Union, Tuple

class NoConnectedDeviceError(RuntimeError):
    pass

class BluetoothAudio():
    """ Singleton class that implements bluetooth audio functions for the Raspberry Pi
        Requires bluetoothctl and bluealsa-aplay cli tools to be installed
        Also requires dbus and dbus python library
        These should all already be installed by default on Raspbian
    """

    instance: 'BluetoothAudio' = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance 

    def __init__(self):
        if self.instance is not None:
            raise RuntimeError('Only one instance of class BluetoothAudio should exist at a time. Use BluetoothAudio.get_instance() instead.')
        self.bluetoothctl: BluetoothCtl = BluetoothCtl()
        self.connected_device: BluetoothDevice = self.bluetoothctl.get_connected_device()
        self.bus = dbus.SystemBus()
        self.dbus_manager = dbus.Interface(self.bus.get_object("org.bluez","/"), "org.freedesktop.DBus.ObjectManager")
        self.audio_forwarding_subprocess = self._forward_audio_to_rpi_output()

    def _forward_audio_to_rpi_output(self) -> subprocess.Popen:
        """ Forwards the incoming bluetooth audio stream to the headphone jack of the Raspberry Pi
            Runs in a bluealsa-aplay 00:00:00:00:00:00 in a subprocess 
            Returns the Popen object of the subprocess.
        """
        audio_forwarding_subprocess = subprocess.Popen(['bluealsa-aplay', '00:00:00:00:00:00'])
        return audio_forwarding_subprocess

    def connect(self, device: Union[str, BluetoothDevice]) -> bool: 
        """ Connects to a device using its mac address.
            Returns True if the operation success and the device is connected, False otherwise. 
        """
        success = self.bluetoothctl.connect(device)
        if success:
            if type(self.connected_device) is BluetoothDevice:
                self.connected_device = device
            elif type(self.connected_device) is str:
                self.connected_device = BluetoothDevice(device)
        return success

    def disconnect(self) -> bool:
        """ Disconnects from the currently connected device and returns success of operation.
        """
        success = self.bluetoothctl.disconnect()
        if success:
            self.connected_device = BluetoothDevice.NullDevice()
        return success

    def autoconnect(self) -> bool:
        """ Automatically connects to a paired device.
            Returns True if the operation success and a device is connected, False otherwise. 
        """
        paired_devices = self.bluetoothctl.get_paired_devices()
        if self.connected_device:
            return True
        for device in paired_devices:
            success = self.connect(device)
            if success:
                return True
        return False

    def connect_different_device(self) -> bool:
        """ Connects to a different device than the device which is already connected.
        """
        paired_devices = self.bluetoothctl.get_paired_devices()
        for device in paired_devices:
            if device != self.connected_device:
                success = self.disconnect() and self.connect(device)
                if success:
                    return True
        return False

    def autopair(self) -> bool:
        """ Automatically pairs and connects to a device that is not already paired.
            Returns True if the operation success and a device is connected, False otherwise. 
        """
        self.bluetooth_ctl.make_discoverable()
        discoverable_devices = self.bluetoothctl.get_discoverable_devices()
        for device in discoverable_devices:
            success = self.bluetoothctl.pair(device) and self.connect(device)
            if success:
                return True
        return False

    def verify_connection(self) -> bool:
        """ Verifies that a device is still connected and has not been disconnected.
            It does not ensure the same device as earlier is connected, only that a device is connected.
            If the connected_device has changed, this updates it.
            This should be called every so often to ensure that connection has not been lost.
            Returns the connection status (True if a device is still connected, False if no device is connected)
        """
        actual_connected_device = self.bluetoothctl.get_connected_device()
        connection_status = bool(self.connected_device)
        if actual_connected_device != self.connected_device:
            self.connected_device = actual_connected_device
        return connection_status

    def _get_media_control_interface(self) -> Tuple[dbus.Interface, dbus.Dictionary]:
        """ Uses dbus to lookup the connected device and find the "org.bluez.MediaPlayer1" dbus interface.
            Returns a tuple with the "org.bluez.MediaPlayer1" dbus interface and the media state dbus dictionary.
        """
        objects = self.dbus_manager.GetManagedObjects()
        media = None
        media_control_interface = None

        for path in objects.keys():
            interfaces = objects[path]
            for interface in interfaces.keys():
                if interface == "org.bluez.Device1":
                    props = interfaces[interface]
                    if props["Connected"] == 1:
                        for player in range(0, 2): # Player can be 0 or 1
                            fullpath = path + '/player' + str(player)
                            if fullpath in objects:
                                media = objects[fullpath]["org.bluez.MediaPlayer1"]
                                break
                        media_control_interface = dbus.Interface(
                            self.bus.get_object("org.bluez", fullpath), "org.bluez.MediaPlayer1")

        if media is None or media_control_interface is None:
            raise NoConnectedDeviceError("Cannot get bluez MediaPlayer interface when no device is connected.")

        return media_control_interface, media

    def is_paused(self) -> bool:
        _, media = self._get_media_control_interface()
        return media["Status"]

    def play(self):
        media_control_interface, _ = self._get_media_control_interface()
        media_control_interface.Play()

    def pause(self):
        media_control_interface, _ = self._get_media_control_interface()
        media_control_interface.Pause()

    def play_pause_toggle(self):
        media_control_interface, media = self._get_media_control_interface()
        if media["Status"] == "paused":
            media_control_interface.Play()
        else:
            media_control_interface.Pause()

    def next_song(self):
        media_control_interface, _ = self._get_media_control_interface()
        media_control_interface.Next()

    def previous_song(self):
        media_control_interface, _ = self._get_media_control_interface()
        media_control_interface.Previous()

    def __del__(self):
        self.disconnect()
        del self.bluetoothctl
        self.audio_forwarding_subprocess.kill()

    def __getattr__(self, attr):
        # For any functions that don't exist in this module but exist in bluetoothctl, automatically use those functions
        # This removes the need to create a wrapper for every function in BluetoothCtl class
        if hasattr(self.bluetoothctl, attr):
            return self.bluetoothctl.__getattribute__(attr)

