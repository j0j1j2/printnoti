import asyncio
from email.message import Message
from typing import cast
from aioimaplib import aioimaplib
from configtype import EmailCredential
import email
from email.header import decode_header


async def imap_from_credential(ec: EmailCredential) -> aioimaplib.IMAP4:
    if ec["provider"] == "gmail":
        imap_client = aioimaplib.IMAP4_SSL("imap.gmail.com")
        await imap_client.wait_hello_from_server()
        await imap_client.login(ec["id"], ec["password"])
        await imap_client.select("INBOX")
        return imap_client
    raise NotImplementedError(f"{ec['provider']} is not implemented")

def _extract(message: Message, field: str): 
    parts = decode_header(message.get(field))
    decoded = ''
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded += part.decode(enc or 'utf-8', errors='replace')
        else:
            decoded += part
    return decoded

async def get_latest_messages(ec: EmailCredential, count: int = 20):
    client = await imap_from_credential(ec)
    _, data = await client.search("ALL")
    data = cast(list[bytes], data)
    messages = data[0].decode().split()
    messages = messages[-count:]
    for msg_num in reversed(messages):
        _, msg_data = await client.fetch(msg_num, "(BODY.PEEK[HEADER])")
        raw_header = cast(bytearray, msg_data[1])
        header = email.message_from_bytes(raw_header)
        subject = _extract(header, 'Subject')
        from_ = _extract(header, 'From')
        print(f"메일 {msg_num}: {subject} / {from_}")


if __name__ == "__main__":
    from config import event_source

    async def main():
        await get_latest_messages(event_source["email"][0])

    asyncio.run(main())
