"""Local WebRTC benchmark: generated video only, no camera access."""
import asyncio
import socket
import time
import aiohttp
import uuid
import cv2
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

URL = 'http://172.16.50.168:6060/offer'
HOST_ID = f'{socket.gethostname()}-{uuid.getnode():012x}'

class TestVideo(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.index = 0
        self.started = time.monotonic()
        self.cap = cv2.VideoCapture(0)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ret, image = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to read frame from camera")
        self.index += 1
        frame = VideoFrame.from_ndarray(image, format='bgr24')
        frame.pts = pts
        frame.time_base = time_base
        return frame


async def main():
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    done = asyncio.Event()
    track = TestVideo()

    @pc.on('connectionstatechange')
    async def state_changed():
        if pc.connectionState in ('failed', 'closed'):
            done.set()

    try:
        pc.addTrack(track)
        await pc.setLocalDescription(await pc.createOffer())
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.post(URL, json={
                'sdp': pc.localDescription.sdp,
                'type': pc.localDescription.type,
                'host_id': HOST_ID
            }) as response:
                response.raise_for_status()
                answer = await response.json()
        await pc.setRemoteDescription(RTCSessionDescription(**answer))
        await done.wait()
    finally:
        track.stop()
        track.cap.release()
        await pc.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
