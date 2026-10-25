using System.Text.Json;
using Godot;
using Govor.Contracts;

namespace Govor.Renderer;

/// <summary>
/// Connects outward to the host's loopback control endpoint and applies allow-listed visual state.
/// Dialogue, lesson policy, and network listening remain outside the renderer.
/// </summary>
public partial class RendererSessionController : Node
{
    private readonly Guid _rendererId = Guid.NewGuid();
    private WebSocketPeer? _socket;
    private StylizedTeacherAvatar? _teacher;
    private DynamicSceneDirector? _sceneDirector;
    private bool _readySent;
    private ulong _nextConnectAtUs;

    public string ControlUrl { get; set; } = string.Empty;
    public string? ControlCaPath { get; set; }
    public PairingQrOverlay? PairingOverlay { get; set; }

    public override void _Ready()
    {
        _teacher = GetNode<StylizedTeacherAvatar>(
            "../CaptureViewport1280x720/World/StylizedTeacherAvatar");
        _sceneDirector = GetNode<DynamicSceneDirector>(
            "../CaptureViewport1280x720/World/DynamicSceneDirector");
        ConnectIfDue();
    }

    public override void _Process(double delta)
    {
        _ = delta;
        if (string.IsNullOrWhiteSpace(ControlUrl))
        {
            return;
        }

        ConnectIfDue();
        if (_socket is null)
        {
            return;
        }

        _socket.Poll();
        WebSocketPeer.State state = _socket.GetReadyState();
        if (state == WebSocketPeer.State.Open)
        {
            if (!_readySent)
            {
                SendReady();
                _readySent = true;
            }

            while (_socket.GetAvailablePacketCount() > 0)
            {
                string message = _socket.GetPacket().GetStringFromUtf8();
                HandleMessage(message);
            }
        }
        else if (state == WebSocketPeer.State.Closed)
        {
            ScheduleReconnect();
        }
    }

    public override void _ExitTree()
    {
        _socket?.Close(1000, "renderer shutdown");
        _socket = null;
    }

    private void ConnectIfDue()
    {
        if (_socket is not null || string.IsNullOrWhiteSpace(ControlUrl) ||
            Time.GetTicksUsec() < _nextConnectAtUs)
        {
            return;
        }

        var candidate = new WebSocketPeer();
        TlsOptions? tlsOptions = null;
        X509Certificate? certificate = null;
        if (ControlUrl.StartsWith("wss://", StringComparison.Ordinal))
        {
            if (string.IsNullOrWhiteSpace(ControlCaPath))
            {
                GD.PushError("A WSS renderer control URL requires --control-ca.");
                candidate.Dispose();
                _nextConnectAtUs = Time.GetTicksUsec() + 1_000_000;
                return;
            }
            certificate = new X509Certificate();
            if (certificate.Load(ControlCaPath) != Error.Ok)
            {
                GD.PushError("The renderer control CA could not be loaded.");
                certificate.Dispose();
                candidate.Dispose();
                _nextConnectAtUs = Time.GetTicksUsec() + 1_000_000;
                return;
            }
            tlsOptions = TlsOptions.Client(certificate, "govor.ai");
        }

        Error result = candidate.ConnectToUrl(ControlUrl, tlsOptions);
        tlsOptions?.Dispose();
        certificate?.Dispose();
        if (result != Error.Ok)
        {
            candidate.Dispose();
            _nextConnectAtUs = Time.GetTicksUsec() + 1_000_000;
            return;
        }

        _socket = candidate;
        _readySent = false;
    }

    private void ScheduleReconnect()
    {
        _socket?.Dispose();
        _socket = null;
        _readySent = false;
        _nextConnectAtUs = Time.GetTicksUsec() + 1_000_000;
    }

    private void SendReady()
    {
        Guid correlationId = Guid.NewGuid();
        string message = ControlContractCodec.EncodeEnvelope(
            "renderer.ready",
            correlationId,
            new RendererReadyPayload(
                _rendererId,
                "godot",
                MessageEnvelope.CurrentProtocolVersion));
        _socket?.SendText(message);
    }

    private void HandleMessage(string text)
    {
        Guid correlationId = Guid.NewGuid();
        Guid commandId = Guid.Empty;
        bool applied = false;
        try
        {
            MessageEnvelope envelope = ControlContractCodec.DecodeEnvelope(text);
            correlationId = envelope.CorrelationId;
            if (envelope.MessageType == "renderer.ack")
            {
                RendererAckPayload readyAcknowledgement =
                    ControlContractCodec.DecodePayload<RendererAckPayload>(envelope);
                if (readyAcknowledgement.CommandId == Guid.Empty || !readyAcknowledgement.Applied)
                {
                    throw new InvalidDataException("Renderer registration was not acknowledged.");
                }
                return;
            }

            if (envelope.MessageType != "renderer.command")
            {
                throw new InvalidDataException("Unsupported renderer message type.");
            }

            RendererCommandPayload command =
                ControlContractCodec.DecodePayload<RendererCommandPayload>(envelope);
            commandId = command.CommandId;
            command.Validate();
            if (command.Scene is not null)
            {
                _sceneDirector?.ApplyScene(command.Scene);
            }
            _teacher?.ApplySessionAction(command.Action, command.AvatarAnimation);
            if (command.Action == "session_started")
            {
                PairingOverlay?.Dismiss();
            }
            applied = true;
            GD.Print(
                $"GOVOR_RENDERER_COMMAND_APPLIED:{command.Action}:" +
                $"{command.CommandId:D}");
        }
        catch (Exception error) when (
            error is JsonException or InvalidDataException or ArgumentException)
        {
            GD.PushWarning($"Rejected renderer control message: {error.GetType().Name}.");
        }

        if (commandId != Guid.Empty)
        {
            _socket?.SendText(
                ControlContractCodec.EncodeEnvelope(
                    "renderer.ack",
                    correlationId,
                    new RendererAckPayload(commandId, applied)));
        }
    }
}
