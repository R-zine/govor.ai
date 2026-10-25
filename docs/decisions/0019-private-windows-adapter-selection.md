# ADR-0019: Select only an active Private-profile Windows LAN adapter

- Status: accepted; software implementation verified, mixed physical path pending
- Date: 2026-10-25
- Scope: post-Milestone 9 maintenance

## Context

The release gateways already bind all IPv4 interfaces and aiortc gathers interface host
candidates. A Windows host on Ethernet and an Android phone on Wi-Fi therefore use the same wire,
security, and media architecture when the router bridges or routes both links. The launcher,
however, previously sorted addresses returned for the Windows hostname and advertised the first.
On a multi-homed machine that could be a disconnected, virtual, VPN, isolated, or Public-profile
interface. It was neither deterministic according to Windows routing nor safe enough for a QR.

The phone address is unknown before pairing, so the launcher cannot probe the learner's exact
subnet before it creates the bootstrap. A usable default and bounded diagnostic override are both
needed.

## Decision

Before creating a pairing code or QR, query the inbox Windows NetTCPIP PowerShell module for IPv4
addresses, adapter status/type, network category, default gateway, and active route/interface
metrics. Admit only an RFC1918 address on an active physical, non-virtual adapter whose Windows
network category is exactly Private. Fail closed when inventory cannot be read or no candidate
passes. Do not silently fall back to hostname resolution.

Select the candidate with the lowest active default-route plus interface metric, then stable
interface index/address ordering. Expose `Start-Govor.cmd --lan-address <IPv4>` for a multi-homed
PC. The requested address must be assigned locally and pass the identical physical/private checks;
the option cannot authorize a Public, VPN/virtual, disconnected, link-local, or arbitrary address.
Print the selected adapter and bounded eligible alternatives before startup.

Keep both gateways bound to all IPv4 interfaces and keep normal aiortc candidate gathering. This
avoids coupling media to adapter enumeration and permits Ethernet-to-Wi-Fi routing without a wire
contract change. Firewall guidance remains Private-profile-only. The application does not modify
Windows network categories, firewall rules, router client isolation, or VLAN policy.

## Consequences

- A normal single-adapter wired or wireless host gets a deterministic QR address.
- A Public Windows profile blocks startup before a pairing artifact or LAN listener is created.
- Multiple valid private networks have a predictable default and explicit bounded override.
- Existing encrypted Android credentials still bind to the stored host. An address change requires
  scanning a different host QR; it does not weaken certificate pinning.
- Unit and launcher tests can verify selection policy. Only a real phone over the intended
  Ethernet-to-access-point path can prove TCP, WSS, ICE, media, and microphone behavior.
- Guest/client isolation, unrouted VLANs, and upstream firewall rules remain explicit deployment
  failures rather than conditions govor.ai attempts to bypass.

## Rejected

- Continue sorting hostname-resolved addresses: it lacks adapter status, category, and routing
  evidence.
- Advertise every address or encode multiple endpoints: that exposes unsafe interfaces and makes
  first pairing ambiguous.
- Automatically switch Windows from Public to Private or add broad firewall rules: this is a
  security-sensitive system policy decision owned by the learner/administrator.
- Bind media to only the selected interface: this would add adapter-specific coupling without
  improving same-LAN WebRTC negotiation.
