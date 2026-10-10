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
    private AnimatedTeacherPlaceholder? _teacher;
    private bool _readySent;
    private ulong _nextConnectAtUs;

    public string ControlUrl { get; set; } = string.Empty;

    public override void _Ready()
    {
        _teacher = GetNode<AnimatedTeacherPlaceholder>(
            "../CaptureViewport1280x720/World/AnimatedTeacherPlaceholder");
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
        Error result = candidate.ConnectToUrl(ControlUrl);
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
            _teacher?.ApplySessionAction(command.Action);
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
