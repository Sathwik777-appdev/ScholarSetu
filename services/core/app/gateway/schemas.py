from pydantic import BaseModel

class GatewayResponse(BaseModel):
    message: str
