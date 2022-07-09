import pexpect
import re
from typing import List, Union
from bluetoothdevice import BluetoothDevice

class BluetoothCtlError(RuntimeError):
    """An error with the bluetoothctl cli tool."""
    pass


class BluetoothCtl:
    """A wrapper for bluetoothctl command line tool using pexpect."""

    BLUETOOTHCTL_EXPECT_RE = re.compile(rb"#") # Regex indicating end of bluetoothctl command (only a hash mark is needed)
    ANSI_COLOR_CODE_RE = re.compile('\033\\[([0-9]+)(;[0-9]+)*m') # Regex for ANSI color codes

    def __init__(self):
        self.child = pexpect.spawn("sudo bluetoothctl", echo=False, timeout=60)

    def _run_command(self, command: str) -> List[str]:
        """Run a command in bluetoothctl prompt and return the output as a list of lines.

        Args:
            command: the command to run

         Returns:
            out: A list of the lines in the output of the command after an expectation has been met
        """
        self.child.sendline(command)
        matched_index = self.child.expect([pexpect.EOF, self.BLUETOOTHCTL_EXPECT_RE])
        if matched_index == 0:
            raise BluetoothCtlError("bluetoothctl failed while running " + command)
        out = self._get_command_output()
        return out

    def _run_command_get_success(self, command: str, success_expect: List[str] = [], fail_expect: List[str] = []) -> bool:
        """Run a command in bluetoothctl prompt and return the output as a list of lines.

        Args:
            command: the command to run
            success_expect: a list of strings for pexpect.spawn().expect() to expect when command is ran succesfully
            fail_expect: a list of strings for pexpect.spawn().expect() to expect when command is ran unsucessfully

         Returns:
            success: True if the command was run succesfully, False otherwise
        """
        self.child.sendline(command)
        matched_index = self.child.expect([pexpect.EOF] + success_expect + fail_expect)
        if matched_index == 0:
            raise BluetoothCtlError("bluetoothctl failed while running " + command)
        success = matched_index <= len(success_expect)
        return success

    def _run_command_for_duration(self, command: str, runtime: float) -> List[str]:
        """Run a command in bluetoothctl prompt for certain amount of time or until the finished_expect is found.

        Args:
            command: the command to run
            runtime: the max time in seconds to run the command for

         Returns:
            out: A list of the lines in the output of the command
        """
        self.child.sendline(command, timeout=runtime)
        matched_index = self.child.expect([pexpect.EOF, pexpect.TIMEOUT, self.BLUETOOTHCTL_EXPECT_RE])
        if matched_index == 0:
            raise BluetoothCtlError("bluetoothctl failed while running " + command)
        out = self._get_command_output()
        return out

    def _get_command_output(self) -> List[str]:
        """ Returns the output of the last command run as a list of lines (strings).
            Automatically called and returned by _run_command and run_command_for_duration functions.
        """
        out = self.child.before.split(b"\r\n")
        decoded_out = []
        for line in out:
            line = line.decode("utf-8")
            line = re.sub(self.ANSI_COLOR_CODE_RE, '', line) # remove ANSI color codes
            decoded_out.append(line)
        return decoded_out

    def _parse_device_string(self, device_string: str) -> BluetoothDevice:
        """Parse a string corresponding to a device and returns a device object."""
        match = BluetoothDevice.MAC_ADDRESS_RE.search(device_string)
        if match:
            mac_address = device_string[match.start():match.end()]
            device_name = device_string[match.end():]
            return BluetoothDevice(mac_address, device_name)
        else:
            return BluetoothDevice.NullDevice()

    def get_connected_device(self) -> BluetoothDevice:
        """ Gets the currently connected device as a device object. Returns NullDevice if no device is connected."""
        out = self._run_command('info')
        device_name = None
        mac_address = None
        for line in out:
            if mac_address is None:
                match = BluetoothDevice.MAC_ADDRESS_RE.search(line)
                if match:
                    mac_address = line[match.start():match.end()]
            if device_name is None:
                name_index = line.find('Name: ')
                if name_index != -1 and device_name is None:
                    device_name = line[name_index + 6:]
        if mac_address is None:
            return BluetoothDevice.NullDevice()
        else:
            return BluetoothDevice(mac_address, device_name)

    def scan_for_bluetooth_devices(self, scantime) -> List[BluetoothDevice]:
        """Scan for bluetooth devices and return list of devices found"""
        out = self._run_command_for_duration("scan on", scantime)
        devices = []
        for line in out:
            mac_addresses = BluetoothDevice.MAC_ADDRESS_RE.findall(line)
            if len(mac_addresses) > 0:
                devices.append(BluetoothDevice(mac_addresses[0]))
        return devices

    def make_discoverable(self):
        """Make device discoverable."""
        self._run_command("discoverable on")

    def get_available_devices(self) -> List[BluetoothDevice]:
        """Returns a list of paired and discoverable devices."""
        out = self._run_command("devices")
        available_devices = []
        for line in out:
            device = self._parse_device_string(line)
            if device:
                available_devices.append(device)
        return available_devices

    def get_paired_devices(self) -> List[BluetoothDevice]:
        """Returns a list of paired devices."""
        out = self._run_command("paired-devices")
        paired_devices = []
        for line in out:
            device = self._parse_device_string(line)
            if device:
                paired_devices.append(device)
        return paired_devices

    def get_discoverable_devices(self) -> List[BluetoothDevice]:
        """Filter paired devices out of available."""
        available = self.get_available_devices()
        paired = self.get_paired_devices()

        return [d for d in available if d not in paired]

    def _validate_mac_address(self, device: Union[BluetoothDevice, str]) -> str:
        mac_address = None
        if type(device) is BluetoothDevice:
            mac_address = device.mac_address
        elif type(device) is str:
            mac_address = device
        if BluetoothDevice.is_valid_mac_address(mac_address):
            return mac_address
        else:
            raise ValueError(f"{mac_address} is not a valid mac address")

    def get_device_info(self, device: Union[BluetoothDevice, str]) -> str:
        """Get device info by mac address."""
        mac_address = self._validate_mac_address(device)
        out = self._run_command("info " + mac_address)
        return out

    def pair(self, device: Union[BluetoothDevice, str]) -> bool:
        """Try to pair with a device by mac address, return success of the operation.."""
        mac_address = self._validate_mac_address(device)
        success_expect = ['Pairing sucessful']
        fail_expect = ["Failed to pair", pexpect.TIMEOUT]
        success = self._run_command_get_success("pair " + mac_address, success_expect, fail_expect)
        return success

    def remove(self, device: Union[BluetoothDevice, str]) -> bool:
        """Remove paired device by mac address, return success of the operation."""
        mac_address = self._validate_mac_address(device)
        success_expect = ['Device has been removed']
        fail_expect = ["not available", pexpect.TIMEOUT]
        success = self._run_command_get_success("remove " + mac_address, success_expect, fail_expect)
        return success

    def connect(self, device: Union[BluetoothDevice, str]) -> bool:
        """Try to connect to a device by mac address, return success of operation."""
        mac_address = self._validate_mac_address(device)
        success_expect = ["Connection successful"]
        fail_expect = ["Failed to connect", pexpect.TIMEOUT]
        success = self._run_command_get_success("connect " + mac_address, success_expect, fail_expect)
        return success

    def disconnect(self) -> bool:
        """Disconnect from the currently connected device, return success of operation."""
        success_expect = ["Successful disconnected", "Missing device address argument"]
        # If bluetoothctl says we are missing device address argument that means there is no device connected
        fail_expect = ["Failed to disconnect", pexpect.TIMEOUT]
        success = self._run_command_get_success("disconnect", success_expect, fail_expect)
        return success

    def __del__(self):
        self.child.close()
