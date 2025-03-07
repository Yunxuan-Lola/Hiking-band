import time
from bluepy import btle
import hike

WATCH_BT_MAC = '94:B5:55:C8:E9:3E'

class HubBluetooth:
    """Handles Bluetooth pairing and synchronization with the Watch.

    Attributes:
        connected: A boolean indicating if the connection is currently established with the Watch.
        sock: the socket object created with bluetooth.BluetoothSocket(),
              through which the Bluetooth communication is handled.
    """

    connected = False
    peripheral = None
    
    def wait_for_connection(self):
        """Synchronous function continuously trying to connect to the Watch by 2 sec intervals.
        If a connection has been made, it sends the watch a `c` ASCII character as a confirmation.
        """

        if not self.connected:
            # try to connect every sec while connection is made
            while True:
                print("Waiting for connection...")
                try:
                    self.peripheral = btle.Peripheral(WATCH_BT_MAC, iface=0)
                    self.connected = True
                    print("Connected to Watch!")
                    self.send_message("c")
                    break
                except btle.BTLEException as e:
                    print(f"Connection failed: {e}. Retrying in 2 seconds...")
                    time.sleep(2)
            print("Hub: Established Bluetooth connection with Watch!")
        else:
            print("WARNING Hub: the has already connected via Bluetooth.")

    def send_message(self, message):
        """Sends a message to the Watch over BLE."""
        if self.connected:
            try:
                # Assuming handle 0x0025 is the correct characteristic for writing
                handle = 0x0025
                self.peripheral.writeCharacteristic(handle, message.encode())
                print(f"Sent '{message}' to Watch")
            except btle.BTLEException as e:
                print(f"Error sending message: {e}")

    def synchronize(self, callback):
        """Continuously tries to receive data from an established connection with the Watch.

        If receives data, then transforms it to a list of `hike.HikeSession` object.
        After that, calls the `callback` function with the transformed data.
        Finally sends a `r` as a response to the Watch for successfully processing the
        incoming data.

        If does not receive data, then it tries to send `c` as a confirmation of the established
        connection at every second to inform the Watch that the Hub is able to receive sessions.

        Args:
            callback: One parameter function able to accept a list[hike.HikeSession].
                      Used to process incoming sessions arbitrarly

        Raises:
            KeyboardInterrupt: to be able to close a running application.
        """
        print("Synchronizing with watch...")
        remainder = b''
        while True:
            try:
                # Assuming handle 0x0025 is for notifications
                self.peripheral.setDelegate(NotificationDelegate(callback))

                while True:
                    if self.peripheral.waitForNotifications(1.0):
                        continue
                    self.send_message("c")  # Send heartbeat to confirm connection

            except KeyboardInterrupt:
                self.peripheral.disconnect()
                print("Shutting down the receiver.")
                break

            except btle.BTLEException as e:
                print(f"Lost connection with the watch: {e}")
                self.connected = False
                self.peripheral.disconnect()
                break

class NotificationDelegate(btle.DefaultDelegate):
        """Handles incoming BLE notifications from the Watch."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def handleNotification(self, cHandle, data):
        try:
            messages = data.decode("utf-8").split("\n")
            sessions = HubBluetooth.messages_to_sessions(messages)
            self.callback(sessions)
            print(f"Received data: {messages}")
        except Exception as e:
            print(f"Error processing data: {e}")


    @staticmethod
    def messages_to_sessions(messages): #(messages: list[bytes]) -> list[hike.HikeSession]:
        """Transforms multiple incoming messages to a list of hike.HikeSession objects.

        Args:
            messages: list of bytes, in the form of the simple protocol between
                      the Hub and the Watch.

        Returns:
            list[hike.HikeSession]: a list of hike.HikeSession objects representing the
                                    interpreted messages.
        """

        #return list(map(HubBluetooth.mtos, messages))
        return [HubBluetooth.mtos(msg.encode()) for msg in messages if msg]


    @staticmethod
    def mtos(message: bytes) -> hike.HikeSession:
        """Transforms a single message into a hike.HikeSession object.

        A single message is in the following format with 0->inf number of latitude and longitude pairs:
            id;steps;km;lat1,long1;lat2,long2;...;\\n

        For example:
            b'4;2425;324;64.83458747762428,24.83458747762428;...,...;\\n'

        Args:
            message: bytes to transform.

        Returns:
            hike.HikeSession: representing a hiking session from transforming a message.

        Raises:
            AssertionError: if the message misses information, or if it is badly formatted.
        """
        m = message.decode('utf-8')

        # filtering because we might have a semi-column at the end of the message, right before the new-line character
        parts = list(filter(lambda p: len(p) > 0, m.split(';')))
        assert len(parts) >= 3, f"MessageProcessingError -> The incoming message doesn't contain enough information: {m}"

        hs = hike.HikeSession()
        hs.id     = int(parts[0])
        hs.steps  = int(parts[1])
        hs.km     = float(parts[2])

        def cvt_coord(c):
            sc = c.split(',')
            assert len(sc) == 2, f"MessageProcessingError -> Unable to process coordinate: {c}"
            return float(sc[0]), float(sc[1])

        if len(parts) > 3:
            hs.coords = map(cvt_coord, parts[3:])

        return hs
