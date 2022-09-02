from typing import Optional
import re

class BluetoothDevice:
    """A class represeting a bluetooth device with a mac address and name."""

    MAC_ADDRESS_RE = re.compile(r"(?:[0-9a-fA-F]:?){12}") # Regex for a mac address

    def __init__(self, mac_address: str, name: Optional[str] = None):
        self.mac_address = mac_address
        self.name = name

    @classmethod
    def NullDevice(cls) -> 'BluetoothDevice':
        return cls('null')

    @staticmethod
    def is_valid_mac_address(mac_address) -> bool:
        return mac_address is not None and BluetoothDevice.MAC_ADDRESS_RE.fullmatch(mac_address) is not None

    @property
    def mac_address(self):
        return self._mac_address
    
    @mac_address.setter
    def mac_address(self, mac_address: str):
        if not self.is_valid_mac_address(mac_address) and mac_address != 'null':
            raise ValueError(f'{mac_address} is not a valid mac address')
        self._mac_address = mac_address

    def __bool__(self) -> bool:
        """ Magic method for boolean value of device.
        True if the device object is not a 'null' device
        """
        return not self.__eq__(self.NullDevice())

    def __repr__(self) -> bool:
        if self.__eq__(self.NullDevice()):
            return 'Null Device'
        name = self.name
        if name is None:
            name = "Unknown Name"
        return f"Device {self.mac_address} {name}"
    
    def __eq__(self, other: 'BluetoothDevice') -> bool:
        return self.mac_address == other.mac_address
        