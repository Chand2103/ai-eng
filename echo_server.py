from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    client_info = f"{websocket.client.host}:{websocket.client.port}"
    logger.info(f"WebSocket connection accepted from {client_info}")
    
    try:
        while True:
            data = await websocket.receive_bytes()
            logger.info(f"Received {len(data)} bytes from {client_info}")
            await websocket.send_bytes(data)
            logger.info(f"Echoed {len(data)} bytes back to {client_info}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from {client_info}")
    except Exception as e:
        logger.error(f"WebSocket error from {client_info}: {e}")
        raise

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
