# ADR-0019: Select an active physical RFC1918 Windows LAN adapter

- Status: amended 2026-10-26; software implementation verified, mixed physical path pending
- Date: 2026-10-25
- Scope: post-Milestone 9 LAN maintenance

## Context

The release gateways already bind all IPv4 interfaces and aiortc gathers interface host
candidates. A Windows host on Ethernet and an Android phone on Wi-Fi therefore use the same wire,
security, and media architecture when the router bridges or routes both links. The launcher,
however, previously sorted addresses returned for the Windows hostname and advertised the first.
On a multi-homed machine that could be a disconnected, virtual, VPN, or isolated interface. It was
neither deterministic according to Windows routing nor safe enough for a QR.

The first implementation also rejected Windows' Public network category. The target Ethernet link
is RFC1918 and sits behind the same trusted router that supplies the phone's Wi-Fi, but Windows
labels it Public. That label selects discovery and firewall defaults; it does not mean the local
address is internet-routable. Treating it as address-scope evidence blocked the intended topology.

The phone address is unknown before pairing, so the launcher cannot probe the learner's exact
subnet before it creates the bootstrap. A usable default and bounded diagnostic override are both
needed.

## Decision

Before creating a pairing code or QR, query the inbox Windows NetTCPIP PowerShell module for IPv4
addresses, adapter status/type, network category, default gateway, and active route/interface
metrics. Admit only an RFC1918 address on an active physical, non-virtual adapter with a recognized
Windows network category. Fail closed when inventory cannot be read or no candidate passes. Do not
silently fall back to hostname resolution.

Prefer Private-category candidates, then select the lowest active default-route plus interface
metric followed by stable interface index/address ordering. A Public-category RFC1918 adapter is
eligible when no Private candidate is chosen; startup prints an explicit warning to confirm the
trusted router, scope Windows Firewall to the local network, and forbid router port forwarding.
Expose `Start-Govor.cmd --lan-address <IPv4>` for a multi-homed PC. The requested address must be
assigned locally and pass the identical physical/RFC1918/recognized-profile checks; the option
cannot authorize a VPN/virtual, disconnected, unidentified, link-local, or arbitrary address.
Print the selected adapter and bounded eligible alternatives before startup.

Keep both gateways bound to all IPv4 interfaces and keep normal aiortc candidate gathering. This
avoids coupling media to adapter enumeration and permits Ethernet-to-Wi-Fi routing without a wire
contract change. The application does not modify Windows network categories, firewall rules,
router client isolation, or VLAN policy.

Firewall guidance follows the selected Windows profile and keeps access on the trusted local
network. It never instructs the operator to forward gateway ports from the router.

## Consequences

- A normal single-adapter wired or wireless host gets a deterministic QR address.
- A Public Windows category does not block an otherwise eligible RFC1918 adapter; it produces a
  trusted-router/firewall warning.
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
- Treat Windows Public as proof of internet exposure: it is only a firewall/discovery category and
  incorrectly rejects RFC1918 Ethernet behind the learner's trusted router.
- Automatically switch Windows from Public to Private or add broad firewall rules: this is a
  security-sensitive system policy decision owned by the learner/administrator.
- Bind media to only the selected interface: this would add adapter-specific coupling without
  improving same-LAN WebRTC negotiation.
