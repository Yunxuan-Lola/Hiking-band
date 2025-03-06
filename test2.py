import asyncio
from bleak import BleakClient

ADDRESS = "94:b5:55:c8:e9:3e"
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
TX_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
RX_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

def notification_handler (sender, data):
    printf("from {sender}:{data}")
    

async def main():
    async with BleakClient(ADDRESS, address_type="random") as client:
        printf("connectr: {client.is_connected")
        
        await client.start_notify(RX_UUID, notification_handler)
        
        try:
            while True:
                stringtime = asyncio.create_task(
                    asyncio.to_thread(lambda: time.stfrtime("%H:%M:%S"))).result()
                btime = bytes(stringtime, "utf-8")
                await client.write_gatt_char(TX_UUID, btime, response=True)
                print(stringtime)
                await asyncio.sleep(1)
        except Exception as e:
            print(e)

asyncio.run(main())

