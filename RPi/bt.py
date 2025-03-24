import time
from bluepy import btle
import hike
from datetime import datetime
import db

WATCH_BT_MAC = '94:B5:55:C8:E9:3E'

class HubBluetooth:
    """Handles Bluetooth pairing and synchronization with the Watch. """

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
                # Assuming handle 45 is the correct characteristic for writing
                handle = 45
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

        If does not receive data, then it tries to send `a` as a confirmation of the established
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
                self.peripheral.setDelegate(NotificationDelegate(callback))

                while True:
                    if self.peripheral.waitForNotifications(1.0):
                        self.send_message("r")
                        continue
                    self.send_message("a")  # Send heartbeat to confirm connection
                    
            except KeyboardInterrupt:
                self.peripheral.disconnect()
                print("Shutting down the receiver.")
                break

            except btle.BTLEException as e:
                print(f"Lost connection with the watch: {e}")
                self.connected = False
                self.peripheral.disconnect()
                break
    
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

        return [HubBluetooth.mtos(msg.encode()) for msg in messages if msg]


    @staticmethod
    def mtos(message: bytes) -> hike.HikeSession:
        """Transforms a single message into a hike.HikeSession object.

        Args:
            message: bytes to transform.

        Returns:
            hike.HikeSession: representing a hiking session from transforming a message.

        Raises:
            AssertionError: if the message misses information, or if it is badly formatted.
        """
        m = message.decode('utf-8')
        steps = int(m)
        #print("steps", steps)

        hs = hike.HikeSession()
        hs.id     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hs.steps  = steps
        hs.km     = round(steps * 0.0008, 3)
        hs.kcal   = hs.calc_kcal()
            
        return hs


class NotificationDelegate(btle.DefaultDelegate):
    """Handles incoming BLE notifications from the Watch."""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def handleNotification(self, cHandle, data):
        try:
            hubbt = HubBluetooth()
            messages = data.decode("utf-8").split("\n")
            sessions = hubbt.messages_to_sessions(messages)
            for h in sessions:
                print(hike.to_list(h))
            self.callback(sessions, db.user0)
            print(f"Received data: {messages}")
    
            
        except Exception as e:
            print(f"Error processing data: {e}")

