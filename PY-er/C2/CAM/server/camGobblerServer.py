"""Local WebRTC benchmark receiver. Start before camTest_webrtc.py."""
import asyncio
import time

import cv2
import sys
import numpy as np
from aiohttp import web
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError
import signal

HOST = '0.0.0.0'
PORT = 6060
WINDOW = 'WebRTC local test - Q to quit'


async def main():
    peers = dict()
    tasks = set()

    async def cleanup_peer(host_id):
        v_dict = peers.get(host_id)

        if v_dict is None or v_dict.get('closing', False):
            return

        v_dict['closing'] = True

        try:
            if 'display_task' in v_dict:
                v_dict['display_task'].cancel()
                await asyncio.gather(
                    v_dict['display_task'],
                    return_exceptions=True
                )

            if 'consume_task' in v_dict:
                v_dict['consume_task'].cancel()
                await asyncio.gather(
                    v_dict['consume_task'],
                    return_exceptions=True
                )

            if 'pc' in v_dict:
                await v_dict['pc'].close()

        except asyncio.CancelledError:
            v_dict['closing'] = False
            raise

        except Exception as e:
            print(f'Cleanup failed for {host_id}: {e}', flush=True)
            v_dict['closing'] = False

        else:
            if peers.get(host_id) is v_dict:
                peers.pop(host_id, None)

            print(f'Cleanup completed for {host_id}', flush=True)

    async def consume(track, client_ip):
        try:
            while True:
                frame = await track.recv()
                peers[client_ip]['latest'] = frame.to_ndarray(format='bgr24')
                peers[client_ip]['count'] += 1
        except MediaStreamError:
            pass

    async def offer(request):
        params = await request.json()
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        host_id = params['host_id']
        if host_id in peers:
            print(f'Host {host_id} already exists, only one connection per host is allowed.')
            return web.Response(status=400, text=f'Host {host_id} already exists')
        
        peers[host_id] = {'pc': pc, 'shown_fps': 0.0, 'sample_time': time.monotonic(), 'sample_count': 0, 'latest': None, 'count': 0}

        @pc.on('track')
        def on_track(track):
            if track.kind == 'video':
                peers[host_id]['consume_task'] = asyncio.create_task(consume(track, host_id))
                tasks.add(peers[host_id]['consume_task'])
                peers[host_id]['consume_task'].add_done_callback(tasks.discard)

        @pc.on('connectionstatechange')
        async def state_changed():
            print('WebRTC:', pc.connectionState, flush=True)
            if pc.connectionState == 'failed':
                await cleanup_peer(host_id)

            if pc.connectionState == 'closed':
                await cleanup_peer(host_id)

        try:
            await pc.setRemoteDescription(RTCSessionDescription(params['sdp'], params['type']))
            await pc.setLocalDescription(await pc.createAnswer())
            return web.json_response({'sdp': pc.localDescription.sdp,
                                      'type': pc.localDescription.type})
        except Exception:
            if host_id in peers:
                await cleanup_peer(host_id)
            raise

    async def display_loop(host_id):
        try:
            cv2.namedWindow(host_id, cv2.WINDOW_NORMAL)
            waiting = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(waiting, 'Waiting for local test sender', (25, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.imshow(host_id, waiting)
            print(f'Listening on {HOST}:{PORT}. Start sender in another terminal.', flush=True)
            while True:
                now = time.monotonic()
                if now - peers[host_id]['sample_time'] >= 1:
                    peers[host_id]['shown_fps'] = (peers[host_id]['count'] - peers[host_id]['sample_count']) / (now - peers[host_id]['sample_time'])
                    peers[host_id]['sample_time'], peers[host_id]['sample_count'] = now, peers[host_id]['count']
                    print(f'Received FPS: {peers[host_id]["shown_fps"]:.1f}', flush=True)
                if peers[host_id]['latest'] is not None:
                    image = peers[host_id]['latest'].copy()
                    cv2.putText(image, f'RX FPS: {peers[host_id]["shown_fps"]:.1f}', (20, 450),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow(host_id, image)
                if cv2.waitKey(1) & 0xff == ord('q'):
                    break
                if cv2.getWindowProperty(host_id, cv2.WND_PROP_VISIBLE) < 1:
                    break
                await asyncio.sleep(0.01)
        finally:
            try:
                cv2.destroyWindow(host_id)
            except cv2.error:
                pass
                    

    app = web.Application(client_max_size=100_000)
    app.router.add_post('/offer', offer)
    runner = web.AppRunner(app)
    await runner.setup()
    try:    
        await web.TCPSite(runner, HOST, PORT).start()

        while True:
            for host_id, v_dict in peers.copy().items():
                if v_dict.get('closing', False):
                    continue

                if not "display_task" in v_dict:
                    task = asyncio.create_task(display_loop(host_id))
                    tasks.add(task)
                    task.add_done_callback(lambda t: tasks.discard(t))
                    v_dict['display_task'] = task

                elif v_dict['display_task'].done():
                    await cleanup_peer(host_id)
                    
            await asyncio.sleep(1)
    finally:
        await asyncio.gather(*(v_dict['pc'].close() for v_dict in list(peers.values())), return_exceptions=True)
        remaining = list(tasks)
        for task in remaining:
            task.cancel()
        await asyncio.gather(*remaining, return_exceptions=True)
        await runner.cleanup()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    try:
        asyncio.run(main())
        input('Press Enter to exit...')
        sys.exit(0)
    except KeyboardInterrupt:
        print('Server stopped by user.', flush=True)

    finally:
        print('Exiting.', flush=True)
