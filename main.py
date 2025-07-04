import asyncio
from typing import Literal
from bleak import BleakScanner, BleakClient
from PIL import Image, ImageFont, ImageDraw
TARGET_PREFIX = "MXW"

SVC_UUID = "0000ae30-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ae02-0000-1000-8000-00805f9b34fb"
CMD_UUID = "0000ae01-0000-1000-8000-00805f9b34fb"
BUF_UUID = "0000ae03-0000-1000-8000-00805f9b34fb"


async def notify_callback(sender, data: bytearray):
    print(f"notification: {sender}: {data.hex()}")


async def init_print(client: BleakClient, width: int = 0x30, height: int = 0x71):
    await client.write_gatt_char(
        CMD_UUID,
        bytes([0x22, 0x21, 0xa9, 0x00, 0x04, 0x00, height & 0xff, 0x00, width & 0xff, 0x01, 0x00, 0x00]),
        response=False,
    )


async def end_print(client: BleakClient):
    await client.write_gatt_char(
        CMD_UUID,
        b"\x22\x21\xad\x00\x01\x00\x00\x00\x00",
        response=False,
    )
    # should be waited until print signal gone
    await asyncio.sleep(10)

def bitlist_to_bytes(bit_list: list[Literal[0, 1]]):
    if len(bit_list) % 8 != 0:
        pad_len = 8 - (len(bit_list) % 8)
        bit_list += [1] * pad_len

    byte_list = []
    for i in range(0, len(bit_list), 8):
        byte_bits = bit_list[i:i+8]
        byte_bits = [bit^1 for bit in byte_bits]
        byte_value = sum(bit << idx for idx, bit in enumerate(byte_bits))
        byte_list.append(byte_value)

    return bytes(byte_list)

def create_buffer(text: str, width: int= 0x30, height: int=0x71): 
    bitwidth = width * 8 
    img = Image.new('1', (bitwidth, height), color=1)
    
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
    pixels = [bitlist_to_bytes(pixels[i:i+bitwidth]) for i in range(0, len(pixels), bitwidth)]
   
    return b''.join(pixels)

async def main():
    device = None

    device = await BleakScanner.find_device_by_address(
        "4864CDA2-269D-42B4-F8B7-1E315572F900",
        timeout=20,
    )
    if device is None:
        print("failed to find device")
        return
    async with BleakClient(device) as client:
        print("Start notify..")
        if client.is_connected:
            await client.start_notify(NOTIFY_UUID, notify_callback)
            await init_print(client)
            service = client.services.get_service(SVC_UUID)
            characteristic = service.get_characteristic(
                BUF_UUID
            )
            max_write = characteristic.max_write_without_response_size

            bufs = create_buffer("난 최고다 블루투스의 신이다")
            print(f"buf len: {len(bufs)}")
            for i in range(0, len(bufs), max_write):
                print(f"Writing {(bufs[i : i + max_write],)}")
                print(f"start: {i}, end: {i + max_write}")
                await client.write_gatt_char(
                    BUF_UUID,
                    bufs[i : i + max_write],
                    response=False,
                )
            await end_print(client)


if __name__ == "__main__":
    asyncio.run(main())
