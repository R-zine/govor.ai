from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass

from aioice.candidate import Candidate, candidate_foundation, candidate_priority
from aioice.ice import Connection, StunProtocol
from aiortc import RTCPeerConnection

LOGGER = logging.getLogger("uvicorn.error")


@dataclass(frozen=True, slots=True)
class ForwardedIceConfiguration:
    """Test-only ICE address presented through a loopback QEMU UDP forward."""

    advertise_host: str
    bind_port: int


class ForwardedIceConnection(Connection):
    """Bind one deterministic guest UDP port while advertising the host-side alias."""

    def __init__(
        self,
        *,
        configuration: ForwardedIceConfiguration,
        local_username: str,
        local_password: str,
    ) -> None:
        super().__init__(
            ice_controlling=False,
            local_username=local_username,
            local_password=local_password,
            use_ipv4=True,
            use_ipv6=False,
        )
        self.configuration = configuration

    async def get_component_candidates(
        self,
        component: int,
        addresses: list[str],
        timeout: int = 5,
    ) -> list[Candidate]:
        del addresses, timeout
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: StunProtocol(self),
            local_addr=("0.0.0.0", self.configuration.bind_port),  # noqa: S104
        )
        udp_socket = transport.get_extra_info("socket")
        if udp_socket is not None:
            udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        candidate = Candidate(
            foundation=candidate_foundation("host", "udp", self.configuration.advertise_host),
            component=component,
            transport="udp",
            priority=candidate_priority(component, "host"),
            host=self.configuration.advertise_host,
            port=self.configuration.bind_port,
            type="host",
        )
        protocol.local_candidate = candidate
        self._protocols.append(protocol)  # noqa: SLF001 - pinned aioice fixture seam
        LOGGER.info(
            "VM fixture ICE candidate prepared: host=%s port=%s",
            self.configuration.advertise_host,
            self.configuration.bind_port,
        )
        return [candidate]


async def install_forwarded_ice(
    peer: RTCPeerConnection,
    configuration: ForwardedIceConfiguration,
) -> None:
    transports = {transceiver.sender.transport.transport for transceiver in peer.getTransceivers()}
    if len(transports) != 1:
        raise RuntimeError("the VM ICE fixture requires a bundled WebRTC offer")
    transport = next(iter(transports))
    gatherer = transport.iceGatherer
    original = transport._connection  # noqa: SLF001 - pinned aiortc fixture seam
    replacement = ForwardedIceConnection(
        configuration=configuration,
        local_username=original.local_username,
        local_password=original.local_password,
    )
    for candidate in original.remote_candidates:
        await replacement.add_remote_candidate(candidate)
    if gatherer._remote_candidates_end:  # noqa: SLF001 - pinned aiortc fixture seam
        await replacement.add_remote_candidate(None)

    # aiortc pins the same aioice connection in both objects and caches its
    # receive/send methods. Keep all three references aligned for this fixture.
    gatherer._connection = replacement  # noqa: SLF001
    transport._connection = replacement  # noqa: SLF001
    transport._recv = replacement.recv  # noqa: SLF001
    transport._send = replacement.send  # noqa: SLF001
