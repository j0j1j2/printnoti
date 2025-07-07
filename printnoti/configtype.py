from typing import Literal, TypedDict

class EmailCredential(TypedDict): 
  id: str 
  password: str
  provider: Literal["gmail"]

class EventSource(TypedDict):
  email: list[EmailCredential]