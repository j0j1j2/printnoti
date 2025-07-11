import asyncio
from typing import Literal
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from PIL import Image, ImageFont, ImageDraw

TARGET_PREFIX = "MXW"

SVC_UUID = "0000ae30-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ae020000-1000-8000-00805f9b34fb"
CMD_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
BUF_UUID = "0000ae03-0000-1000-8000-00805f9b34fb"


async def notify_callback(sender: BleakGATTCharacteristic, data: bytearray):
    print(f"Notification: {sender.uuid}: {data.hex()}")


async def init_print(client: BleakClient, width: int = 0x30, height: int = 0x71):
    await client.write_gatt_char(
        CMD_UUID,
        bytes(
            [
                0x22,
                0x21,
                0xA9,
                0x00,
                0x04,
                0x00,
                height & 0xFF,
                0x00,
                width & 0xFF,
                0x01,
                0x00,
                0x00,
            ]
        ),
        response=False,
    )


async def end_print(client: BleakClient):
    await client.write_gatt_char(
        CMD_UUID,
        b"\x22\x21\xad\x00\x01\x00\x00\x00\x00",
        response=False,
    )
    # should wait until print signal gone
    await asyncio.sleep(10)


def bitlist_to_bytes(bit_list: list[Literal[0, 1]]):
    if len(bit_list) % 8 != 0:
        pad_len = 8 - (len(bit_list) % 8)
        bit_list += [1] * pad_len

    byte_list = []
    for i in range(0, len(bit_list), 8):
        byte_bits = bit_list[i : i + 8]
        byte_bits = [bit ^ 1 for bit in byte_bits]
        byte_value = sum(bit << idx for idx, bit in enumerate(byte_bits))
        byte_list.append(byte_value)

    return bytes(byte_list)


def create_buffer(text: str, width: int = 0x30, height: int = 0x71):
    bitwidth = width * 8
    img = Image.new("1", (bitwidth, height), color=1)

    draw = ImageDraw.Draw(img)

    font_path = "./NanumGothicBold.ttf"
    font = ImageFont.truetype(font_path, 22)

    sx, sy, ex, ey = draw.textbbox((0, 0), text, font=font)
    text_width = ex - sx
    text_height = ey - sy
    x = (bitwidth - text_width) / 2
    y = (height - text_height) / 2

    draw.text((x, y), text, font=font)
    pixels = list(img.getdata())
    pixels = [
        bitlist_to_bytes(pixels[i : i + bitwidth])
        for i in range(0, len(pixels), bitwidth)
    ]

    return b"".join(pixels)


async def main():
    device = None
    print("Searching device...")
    devices = await BleakScanner.discover(timeout=20)
    for d in devices:
        if d.name and d.name.startswith(TARGET_PREFIX):
            device = d
            break
    if device is None:
        print("Failed to find device")
        return
    async with BleakClient(device) as client:
        if client.is_connected:
            print("Start notify..")
            await client.start_notify(NOTIFY_UUID, notify_callback)
            print("Start Printing..")
            await init_print(client, height=48)
            service = client.services.get_service(SVC_UUID)
            characteristic = service.get_characteristic(BUF_UUID)
            max_write = characteristic.max_write_without_response_size
            print(f"max_write: {max_write}")
            bufs = create_buffer("카리나 화이팅", height=48)
            for i in range(0, len(bufs), max_write):
                await client.write_gatt_char(
                    BUF_UUID,
                    bufs[i : i + max_write],
                    response=False,
                )
            await end_print(client)

if __name__ == "__main__":
    asyncio.run(main())
